"""Per-site politeness: cached robots.txt policy, request spacing and access blocks."""

import json
from dataclasses import dataclass

import aiosqlite

from dijitalvatan import config
from dijitalvatan.storage.database import now_ms

ORIGIN_COLUMNS = "origin, robots_policy, robots_checked_at_ms, delay_ms, next_request_at_ms, blocked_reason, blocked_phase"


@dataclass
class OriginState:
    origin: str
    robots_policy: dict | None
    robots_checked_at_ms: int | None
    delay_ms: int
    next_request_at_ms: int
    blocked_reason: str | None
    blocked_phase: str | None


class OriginRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def _ensure(self, origin: str):
        await self.conn.execute("INSERT INTO origins (origin, delay_ms) VALUES (?, ?) ON CONFLICT DO NOTHING",
                                [origin, config.MIN_REQUEST_DELAY_MS])

    async def get(self, origin: str) -> OriginState:
        await self._ensure(origin)
        rows = await self.conn.execute_fetchall(f"SELECT {ORIGIN_COLUMNS} FROM origins WHERE origin = ?", [origin])
        state = dict(rows[0])
        state["robots_policy"] = json.loads(state["robots_policy"]) if state["robots_policy"] else None
        return OriginState(**state)

    async def delay_ms(self, origin: str) -> int | None:
        rows = await self.conn.execute_fetchall("SELECT delay_ms FROM origins WHERE origin = ?", [origin])
        return rows[0]["delay_ms"] if rows else None

    async def block(self, origin: str, reason: str, phase: str):
        await self._ensure(origin)
        await self.conn.execute("UPDATE origins SET blocked_reason = ?, blocked_phase = ? WHERE origin = ?",
                                [reason, phase, origin])

    async def save_robots(self, origin: str, policy: dict, delay_ms: int):
        now = now_ms()
        await self.conn.execute(
            """UPDATE origins SET robots_policy = ?, robots_checked_at_ms = ?, delay_ms = ?,
                next_request_at_ms = max(next_request_at_ms, ?) WHERE origin = ?""",
            [json.dumps(policy), now, delay_ms, now + delay_ms, origin],
        )

    async def schedule_next(self, origin: str, delay_ms: int):
        await self.conn.execute("UPDATE origins SET next_request_at_ms = ? WHERE origin = ?", [now_ms() + delay_ms, origin])

    async def defer_until(self, origin: str, until_ms: int):
        """A server's Retry-After can only push the next request later."""
        await self.conn.execute("UPDATE origins SET next_request_at_ms = max(next_request_at_ms, ?) WHERE origin = ?",
                                [until_ms, origin])

    async def clear_blocks_and_robots(self):
        """Explicit retries re-check every site, but never shorten a pending Retry-After."""
        await self.conn.execute(
            "UPDATE origins SET blocked_reason = NULL, blocked_phase = NULL, robots_policy = NULL, robots_checked_at_ms = NULL"
        )

    async def reset(self):
        """A fresh crawl forgets all sites except their future Retry-After times."""
        await self.conn.execute("DELETE FROM origins WHERE next_request_at_ms <= ?", [now_ms()])
        await self.clear_blocks_and_robots()
