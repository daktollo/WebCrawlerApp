"""The single crawl_state row: which crawl runs, its phase and limits."""

from dataclasses import dataclass

import aiosqlite

from dijitalvatan.storage.database import now_iso

STATE_COLUMNS = """seed, status, max_pages, max_depth, current_url, last_error, revision, indexed_words,
    started_at, updated_at"""
# Every write makes clients refresh: revision only grows.
TOUCH = "updated_at = :now, revision = revision + 1"


@dataclass
class CrawlState:
    seed: str | None
    status: str
    max_pages: int
    max_depth: int
    current_url: str | None
    last_error: str | None
    revision: int
    indexed_words: int
    started_at: str | None
    updated_at: str | None

    def same_generation(self, other: "CrawlState") -> bool:
        return self.seed == other.seed and self.started_at == other.started_at


class CrawlStateRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def _update(self, assignments: str, **params):
        await self.conn.execute(f"UPDATE crawl_state SET {assignments}, {TOUCH} WHERE id = 1", {"now": now_iso(), **params})

    async def get(self) -> CrawlState:
        rows = await self.conn.execute_fetchall(f"SELECT {STATE_COLUMNS} FROM crawl_state WHERE id = 1")
        return CrawlState(**dict(rows[0]))

    async def touch(self):
        await self.conn.execute(f"UPDATE crawl_state SET {TOUCH} WHERE id = 1", {"now": now_iso()})

    async def finish(self, status: str, last_error: str | None):
        await self._update("status = :status, last_error = :error, current_url = NULL", status=status, error=last_error)

    async def set_current_url(self, url: str | None):
        await self.conn.execute("UPDATE crawl_state SET current_url = ?, updated_at = ? WHERE id = 1", [url, now_iso()])

    async def set_indexed_words(self, count: int):
        await self._update("indexed_words = :count", count=count)

    async def begin_generation(self, seed: str, max_pages: int, started_at: str):
        """A new crawl: the strictly later started_at lets clients drop answers about the previous one."""
        await self._update(
            """seed = :seed, status = 'running', max_pages = :max_pages, current_url = NULL, last_error = NULL,
            indexed_words = 0, started_at = :started_at""",
            seed=seed, max_pages=max_pages, started_at=started_at,
        )

    async def run(self, max_pages: int):
        await self._update("status = 'running', max_pages = :max_pages, current_url = NULL, last_error = NULL",
                           max_pages=max_pages)

    async def pause(self):
        await self._update("status = 'paused', current_url = NULL")

    async def set_max_pages(self, max_pages: int, visited: int):
        """A running crawl that has already processed the new limit stops at once."""
        await self._update(
            """max_pages = :max_pages,
            status = CASE WHEN status = 'running' AND :visited >= :max_pages THEN 'limit_reached' ELSE status END,
            current_url = CASE WHEN status = 'running' AND :visited >= :max_pages THEN NULL ELSE current_url END""",
            max_pages=max_pages, visited=visited,
        )
