"""Crawl management actions: start, pause, resume, retry, set_limit and reset."""

from datetime import datetime, timedelta

from dijitalvatan.crawler.crawler import Crawler
from dijitalvatan.crawler.url_rules import origin_of
from dijitalvatan.storage.crawl_state_repository import CrawlStateRepository
from dijitalvatan.storage.database import Database, now_iso
from dijitalvatan.storage.origin_repository import OriginRepository
from dijitalvatan.storage.page_repository import PageRepository
from dijitalvatan.storage.queue_repository import VISITED_STATES, QueueRepository

ACTIONS = ("start", "pause", "resume", "retry", "set_limit", "reset")


class ControlRejected(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status


class CrawlControl:
    def __init__(self, db: Database, crawler: Crawler):
        self.db = db
        self.crawler = crawler

    async def apply(self, action: str, seed: str, max_pages: int):
        async with self.db.transaction() as conn:
            states = CrawlStateRepository(conn)
            queue = QueueRepository(conn)
            origins = OriginRepository(conn)
            current = await states.get()
            if action not in ("start", "reset"):
                if current.seed is None:
                    raise ControlRejected("Önce bir tarama başlatın.", 409)
                if seed != current.seed:
                    raise ControlRejected("Başlangıç adresini değiştirmek için yeni tarama başlatın.", 409)

            if action == "reset" or (action == "start" and seed != current.seed):
                # A new generation: every page, link and word of the previous crawl is removed.
                await PageRepository(conn).clear_all()
                await origins.reset()
                await states.begin_generation(seed, max_pages, _later_than(current.started_at))
                await queue.enqueue_seed(seed, origin_of(seed))
            elif action == "start":
                # Same seed again: revisit every URL; the old pages stay searchable until refreshed.
                await origins.clear_blocks_and_robots()
                await queue.requeue(VISITED_STATES)
                await queue.enqueue_seed(seed, origin_of(seed))
                await states.run(max_pages)
            elif action == "retry":
                await origins.clear_blocks_and_robots()
                await queue.requeue(("failed",))
                await states.run(max_pages)
            elif action == "resume":
                await states.run(max_pages)
            elif action == "pause":
                await states.pause()
            elif action == "set_limit":
                await states.set_max_pages(max_pages, await queue.count_visited())
        self.crawler.wake()


def _later_than(previous: str | None) -> str:
    """Now, or a millisecond after the previous start when the clock has not moved past it."""
    now = now_iso()
    if previous is None or now > previous:
        return now
    moment = datetime.fromisoformat(previous) + timedelta(milliseconds=1)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")
