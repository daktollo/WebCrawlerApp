"""The background crawl loop: one URL at a time, breadth-first, while the crawl is running."""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable

import aiosqlite
import httpx

from dijitalvatan import config
from dijitalvatan.crawler import errors
from dijitalvatan.crawler.errors import CrawlChanged, CrawlFailure, OriginBlocked, SkipPage
from dijitalvatan.crawler.html_extractor import ExtractedHtml, HtmlTooLarge, extract_html
from dijitalvatan.crawler.page_fetcher import HTML_TYPE, PageFetcher
from dijitalvatan.crawler.url_rules import origin_of
from dijitalvatan.indexing.text_normalizer import tokenize, url_text
from dijitalvatan.ranking.pagerank import compute_ranks
from dijitalvatan.storage.crawl_state_repository import CrawlState, CrawlStateRepository
from dijitalvatan.storage.database import Database
from dijitalvatan.storage.origin_repository import OriginRepository
from dijitalvatan.storage.page_repository import PageRepository
from dijitalvatan.storage.queue_repository import QueueItem, QueueRepository

logger = logging.getLogger(__name__)
NOINDEX_HEADER = re.compile(r"\bnoindex\b|\bnone\b", re.IGNORECASE)
NOFOLLOW_HEADER = re.compile(r"\bnofollow\b|\bnone\b", re.IGNORECASE)

Write = Callable[[aiosqlite.Connection], Awaitable[None]]


class Crawler:
    def __init__(self, db: Database, http: httpx.AsyncClient):
        self.db = db
        self.fetcher = PageFetcher(db, http, self._wait)
        self._wake = asyncio.Event()
        self._generation: CrawlState | None = None  # state when the current page was picked
        self._unranked_pages = 0

    def wake(self):
        """Called after a control action so the loop reacts without waiting for its idle poll."""
        self._wake.set()

    async def run(self):
        async with self.db.snapshot() as conn:
            self._generation = await CrawlStateRepository(conn).get()
        await self._refresh_ranks()
        while True:
            try:
                await self._step()
            except Exception:
                logger.exception("Crawler step failed")
                await self._sleep(config.IDLE_POLL_S)

    async def _step(self):
        async with self.db.snapshot() as conn:
            state = await CrawlStateRepository(conn).get()
        if state.status != "running":
            if self._unranked_pages:
                await self._refresh_ranks()
            await self._sleep(config.IDLE_POLL_S)
            return
        self._generation = state

        item, wait = None, None
        async with self.db.snapshot() as conn:
            queue = QueueRepository(conn)
            visited = await queue.count_visited()
            if visited < state.max_pages:
                item = await queue.next_ready()
                if item is None:
                    wait = await queue.seconds_until_ready()
        if visited >= state.max_pages:
            await self._commit(lambda conn: CrawlStateRepository(conn).finish("limit_reached", None))
        elif item is None and wait is None:
            await self._commit(lambda conn: CrawlStateRepository(conn).finish("completed", None))
        elif item is None:
            await self._sleep(min(wait, config.IDLE_POLL_S))
        else:
            await self._commit(lambda conn: CrawlStateRepository(conn).set_current_url(item.url))
            await self._crawl(item, state)
            if self._unranked_pages >= config.RANK_REFRESH_EVERY:
                await self._refresh_ranks()

    async def _crawl(self, item: QueueItem, state: CrawlState):
        seed_origin = origin_of(state.seed)
        try:
            response = await self.fetcher.fetch(item.url, "page")
            origin = origin_of(response.url)
            if response.status in (401, 403):
                raise CrawlFailure(f"Site bu isteğe erişim izni vermedi (HTTP {response.status}).", "blocked", origin)
            if response.status == 429:
                raise CrawlFailure("Site istek sınırına ulaşıldığını bildirdi (HTTP 429). Bekleme süresi dolduktan sonra "
                                   "yeniden deneyin.", "error", origin)
            if response.status >= 500:
                raise CrawlFailure(f"Kaynak sunucu HTTP {response.status} hatası verdi. Daha önce indekslenen içerik "
                                   "korunuyor.", "error", origin)
            if not 200 <= response.status < 300:
                raise SkipPage(f"Sayfa alınamadı (HTTP {response.status}).")
            if not HTML_TYPE.search(response.content_type):
                raise SkipPage(errors.NOT_HTML)
            try:
                page = extract_html(response.body, response.url)
            except HtmlTooLarge as error:
                raise SkipPage(str(error)) from error
            if page.blocked_reason:
                raise CrawlFailure(page.blocked_reason, "blocked", origin)
            noindex = page.noindex or bool(NOINDEX_HEADER.search(response.robots_header))
            if not page.text.strip() and not noindex:
                raise SkipPage(errors.NO_TEXT)
            nofollow = page.nofollow or bool(NOFOLLOW_HEADER.search(response.robots_header))
            links = [] if nofollow else page.links[: config.MAX_OUTLINKS_PER_PAGE]
            saved = await self._commit(lambda conn: self._save(conn, item, response.url, page, links, noindex, state))
            if saved and not noindex:
                self._unranked_pages += 1
        except CrawlChanged:
            logger.info("Crawl changed while fetching %s; result dropped", item.url)
        except SkipPage as skip:
            async def record_skip(conn):
                await QueueRepository(conn).mark(item.id, "skipped", skip.message)
                await CrawlStateRepository(conn).touch()
                if item.depth == 0 and skip.robots_denied:
                    await CrawlStateRepository(conn).finish("blocked", skip.message)
            await self._commit(record_skip)
        except CrawlFailure as failure:
            async def record_failure(conn):
                if failure.origin and not isinstance(failure, OriginBlocked):
                    await OriginRepository(conn).block(failure.origin, failure.message, failure.phase)
                if failure.origin and failure.origin != seed_origin:
                    # Another site refused: skip its URLs and keep crawling the rest.
                    await QueueRepository(conn).mark(item.id, "skipped" if failure.phase == "blocked" else "failed",
                                                     failure.message)
                    await CrawlStateRepository(conn).touch()
                else:
                    await QueueRepository(conn).mark(item.id, "failed", failure.message)
                    await CrawlStateRepository(conn).finish(failure.phase, failure.message)
            await self._commit(record_failure)
        except Exception:
            logger.exception("Crawling %s failed", item.url)

            async def record_crash(conn):
                await QueueRepository(conn).mark(item.id, "failed", errors.UNEXPECTED)
                await CrawlStateRepository(conn).finish("error", errors.UNEXPECTED)
            await self._commit(record_crash)

    async def _save(self, conn: aiosqlite.Connection, item: QueueItem, final_url: str, page: ExtractedHtml,
                    links: list[str], noindex: bool, state: CrawlState):
        pages = PageRepository(conn)
        queue = QueueRepository(conn)
        if noindex:
            await pages.delete(final_url)
        else:
            terms = {
                "content": list(dict.fromkeys(tokenize(page.text))),
                "title": list(dict.fromkeys(tokenize(page.title))),
                "url": list(dict.fromkeys(tokenize(url_text(final_url)))),
            }
            await pages.save(final_url, page.title, page.description, page.text, terms, links)
        if item.depth < state.max_depth and links:
            await queue.enqueue(links, [origin_of(link) for link in links], item.depth + 1,
                                state.max_pages * config.QUEUE_CAPACITY_PER_PAGE)
        await queue.mark(item.id, "skipped" if noindex else "done", errors.NOINDEX if noindex else None)
        await CrawlStateRepository(conn).touch()

    async def _refresh_ranks(self):
        """Recompute PageRank over the indexed pages and the vocabulary size shown in the status."""
        async def refresh(conn):
            pages = PageRepository(conn)
            await pages.set_ranks(compute_ranks(await pages.link_graph(), config.PAGERANK_DAMPING, config.PAGERANK_ITERATIONS))
            await CrawlStateRepository(conn).set_indexed_words(await pages.count_content_words())
        # Pages of a paused or finished crawl still get ranked; a reset or new seed discards the refresh.
        await self._commit(refresh, require_running=False)
        self._unranked_pages = 0

    async def _commit(self, write: Write, require_running: bool = True) -> bool:
        """Run `write` only if the crawl is still the generation this loop is working on."""
        async with self.db.transaction() as conn:
            current = await CrawlStateRepository(conn).get()
            if not current.same_generation(self._generation) or (require_running and current.status != "running"):
                return False
            await write(conn)
            return True

    async def _wait(self, seconds: float):
        if seconds > 0:
            await self._sleep(seconds)
        async with self.db.snapshot() as conn:
            current = await CrawlStateRepository(conn).get()
        if current.status != "running" or not current.same_generation(self._generation):
            raise CrawlChanged()

    async def _sleep(self, seconds: float):
        try:
            await asyncio.wait_for(self._wake.wait(), seconds)
        except TimeoutError:
            pass
        self._wake.clear()
