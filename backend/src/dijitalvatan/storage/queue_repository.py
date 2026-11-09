"""The crawl frontier: every discovered URL and what happened to it."""

import json
from dataclasses import dataclass

import aiosqlite

from dijitalvatan.storage.database import now_iso, now_ms

VISITED_STATES = ("done", "skipped", "failed")


@dataclass
class QueueItem:
    id: int
    url: str
    origin: str
    depth: int


class QueueRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def next_ready(self) -> QueueItem | None:
        """Breadth-first next URL whose site may be requested now. Blocked sites are picked too, to record the skip."""
        rows = await self.conn.execute_fetchall(
            """SELECT q.id, q.url, q.origin, q.depth FROM queue q LEFT JOIN origins o ON o.origin = q.origin
            WHERE q.state = 'queued'
              AND (o.origin IS NULL OR o.blocked_reason IS NOT NULL OR o.next_request_at_ms <= ?)
            ORDER BY q.depth, q.id LIMIT 1""",
            [now_ms()],
        )
        return QueueItem(**dict(rows[0])) if rows else None

    async def seconds_until_ready(self) -> float | None:
        """Wait until the earliest queued site may be requested again; None when nothing is queued."""
        rows = await self.conn.execute_fetchall(
            """SELECT count(*) AS queued, min(coalesce(o.next_request_at_ms, 0)) AS next_ms
            FROM queue q LEFT JOIN origins o ON o.origin = q.origin WHERE q.state = 'queued'"""
        )
        if rows[0]["queued"] == 0:
            return None
        return max(0.0, (rows[0]["next_ms"] - now_ms()) / 1000)

    async def counts(self) -> dict[str, int]:
        rows = await self.conn.execute_fetchall("SELECT state, count(*) AS count FROM queue GROUP BY state")
        return {row["state"]: row["count"] for row in rows}

    async def count_visited(self) -> int:
        counts = await self.counts()
        return sum(counts.get(state, 0) for state in VISITED_STATES)

    async def mark(self, item_id: int, state: str, error: str | None):
        await self.conn.execute("UPDATE queue SET state = ?, error = ?, updated_at = ? WHERE id = ?",
                                [state, error, now_iso(), item_id])

    async def enqueue(self, urls: list[str], origins: list[str], depth: int, capacity: int):
        """Add new URLs in page order while the queue holds fewer than `capacity` rows."""
        await self.conn.execute(
            """INSERT INTO queue (url, origin, depth, updated_at)
            SELECT json_extract(value, '$[0]'), json_extract(value, '$[1]'), :depth, :now FROM json_each(:pairs)
            WHERE json_extract(value, '$[0]') NOT IN (SELECT url FROM queue)
            ORDER BY key
            LIMIT max(0, :capacity - (SELECT count(*) FROM queue))
            ON CONFLICT (url) DO NOTHING""",
            {"pairs": json.dumps(list(zip(urls, origins))), "depth": depth, "now": now_iso(), "capacity": capacity},
        )

    async def enqueue_seed(self, seed: str, origin: str):
        await self.conn.execute(
            """INSERT INTO queue (url, origin, depth, updated_at) VALUES (?, ?, 0, ?)
            ON CONFLICT (url) DO UPDATE SET state = 'queued', error = NULL, updated_at = excluded.updated_at""",
            [seed, origin, now_iso()],
        )

    async def requeue(self, states: tuple[str, ...]):
        await self.conn.execute(
            f"UPDATE queue SET state = 'queued', error = NULL, updated_at = ? WHERE state IN ({','.join('?' * len(states))})",
            [now_iso(), *states],
        )

    async def recent_errors(self, limit: int) -> list[dict]:
        rows = await self.conn.execute_fetchall(
            "SELECT url, error FROM queue WHERE error IS NOT NULL ORDER BY updated_at DESC LIMIT ?", [limit]
        )
        return [dict(row) for row in rows]
