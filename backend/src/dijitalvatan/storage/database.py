"""SQLite connections: one per transaction, WAL mode so the crawler writes while the API reads."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

# busy_timeout comes first so every later statement waits for locks instead of failing.
# WAL mode is persistent in the database file and is set by the migration tool.
PRAGMAS = ("PRAGMA busy_timeout = 10000", "PRAGMA foreign_keys = ON", "PRAGMA synchronous = NORMAL")


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


class SchemaNotMigrated(Exception):
    pass


class Database:
    def __init__(self, path: Path):
        self.path = path

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.path, isolation_level=None)
        conn.row_factory = aiosqlite.Row
        try:
            for pragma in PRAGMAS:
                await conn.execute(pragma)
        except BaseException:
            # Each connection owns a non-daemon thread; an unclosed one keeps the process from exiting.
            await conn.close()
            raise
        return conn

    @asynccontextmanager
    async def transaction(self):
        """A write transaction holding the write lock from its first statement, so checks and writes are atomic."""
        conn = await self._connect()
        try:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                await conn.rollback()
                raise
            await conn.commit()
        finally:
            await conn.close()

    @asynccontextmanager
    async def snapshot(self):
        """A read transaction: every query inside sees the same committed state."""
        conn = await self._connect()
        try:
            await conn.execute("BEGIN")
            yield conn
            await conn.rollback()
        finally:
            await conn.close()

    async def ensure_migrated(self, migrations: list[str]):
        """Fail loudly when the database is missing or behind the migration files."""
        if not self.path.exists():
            raise SchemaNotMigrated(f"{self.path} bulunamadı. Önce migration'ları uygulayın: uv run python -m dijitalvatan.migrate")
        async with self.snapshot() as conn:
            rows = await conn.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            )
            applied = {row["name"] for row in await conn.execute_fetchall("SELECT name FROM schema_migrations")} if rows else set()
        pending = [name for name in migrations if name not in applied]
        if pending:
            raise SchemaNotMigrated(f"Uygulanmamış migration'lar: {', '.join(pending)}. Çalıştırın: uv run python -m dijitalvatan.migrate")
