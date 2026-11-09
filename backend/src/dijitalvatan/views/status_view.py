"""GET /api/crawl/status: phase, counters and recent activity of the crawl."""

from dijitalvatan import config
from dijitalvatan.crawler.url_rules import origin_of
from dijitalvatan.storage.crawl_state_repository import CrawlStateRepository
from dijitalvatan.storage.database import Database
from dijitalvatan.storage.index_queries import IndexQueries
from dijitalvatan.storage.origin_repository import OriginRepository
from dijitalvatan.storage.queue_repository import QueueRepository

RECENT_PAGES = 6
RECENT_ERRORS = 5


async def read_status(db: Database) -> dict:
    async with db.snapshot() as conn:
        state = await CrawlStateRepository(conn).get()
        queries = IndexQueries(conn)
        pages = await queries.page_summary()
        counts = await QueueRepository(conn).counts()
        links = await queries.link_count()
        recent_pages = await queries.recent_pages(RECENT_PAGES)
        recent_errors = await QueueRepository(conn).recent_errors(RECENT_ERRORS)
        seed = state.seed or config.DEFAULT_SEED
        delay_ms = await OriginRepository(conn).delay_ms(origin_of(seed))
    return {
        "ok": True,
        "seed": seed,
        "status": state.status,
        "indexedPages": pages["count"],
        "queuedPages": counts.get("queued", 0),
        "visitedPages": counts.get("done", 0) + counts.get("failed", 0) + counts.get("skipped", 0),
        "failedPages": counts.get("failed", 0),
        "skippedPages": counts.get("skipped", 0),
        "indexedWords": state.indexed_words,
        "linkCount": links,
        "maxPages": state.max_pages,
        "maxDepth": state.max_depth,
        "delayMs": delay_ms or config.MIN_REQUEST_DELAY_MS,
        "currentUrl": state.current_url,
        "lastError": state.last_error,
        "updatedAt": state.updated_at,
        "startedAt": state.started_at,
        "lastIndexedAt": pages["latest"],
        "revision": state.revision,
        "canManage": True,
        "recentPages": [{"url": row["url"], "title": row["title"], "indexedAt": row["indexed_at"]} for row in recent_pages],
        "recentErrors": recent_errors,
    }
