"""Apply pending SQL migrations from backend/migrations/ in file-name order.

Run: uv run python -m dijitalvatan.migrate
"""

import sqlite3
from pathlib import Path

from dijitalvatan import config


def migration_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def apply_migrations(db_path: Path, directory: Path) -> list[str]:
    """Each file runs in its own transaction and is recorded in schema_migrations; returns the applied names."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        newly_applied = []
        for path in migration_files(directory):
            if path.name in applied:
                continue
            conn.execute("BEGIN")
            try:
                for statement in sqlite3_statements(path.read_text(encoding="utf-8")):
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_migrations VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))", [path.name])
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            newly_applied.append(path.name)
        return newly_applied
    finally:
        conn.close()


def sqlite3_statements(script: str) -> list[str]:
    """Split a script into complete statements (executescript would commit the open transaction)."""
    statements, current = [], ""
    for line in script.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            statements.append(current.strip())
            current = ""
    if any(line.strip() and not line.strip().startswith("--") for line in current.splitlines()):
        raise ValueError(f"Tamamlanmamış SQL ifadesi: {current.strip()[:80]}")
    return statements


def main():
    applied = apply_migrations(config.DB_PATH, config.MIGRATIONS_DIR)
    print(f"Uygulanan migration: {', '.join(applied)}" if applied else "Uygulanacak yeni migration yok.")
    print(f"Veritabanı: {config.DB_PATH}")


if __name__ == "__main__":
    main()
