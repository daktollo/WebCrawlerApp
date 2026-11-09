"""Writes of indexed pages: page row, inverted-index postings, outlinks and PageRank."""

import json

import aiosqlite

from dijitalvatan.storage.database import now_iso


class PageRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def save(self, url: str, title: str, description: str, body: str,
                   terms: dict[str, list[str]], links: list[str]):
        """Replace the page and everything derived from it; terms maps a field (content/title/url) to its words."""
        rows = await self.conn.execute_fetchall(
            """INSERT INTO pages (url, title, description, body, indexed_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (url) DO UPDATE SET title = excluded.title, description = excluded.description,
                body = excluded.body, indexed_at = excluded.indexed_at
            RETURNING id""",
            [url, title, description, body, now_iso()],
        )
        page_id = rows[0]["id"]
        await self.conn.execute("DELETE FROM postings WHERE page_id = ?", [page_id])
        for field, words in terms.items():
            encoded = json.dumps(words)
            await self.conn.execute(
                "INSERT INTO words (word) SELECT value FROM json_each(?) WHERE true ON CONFLICT (word) DO NOTHING", [encoded]
            )
            await self.conn.execute(
                """INSERT INTO postings (word_id, page_id, field)
                SELECT id, ?, ? FROM words WHERE word IN (SELECT value FROM json_each(?))
                ON CONFLICT DO NOTHING""",
                [page_id, field, encoded],
            )
        await self.conn.execute("DELETE FROM links WHERE source_id = ?", [page_id])
        await self.conn.execute(
            "INSERT INTO links (source_id, target_url) SELECT ?, value FROM json_each(?) WHERE true ON CONFLICT DO NOTHING",
            [page_id, json.dumps(links)],
        )

    async def delete(self, url: str):
        await self.conn.execute("DELETE FROM pages WHERE url = ?", [url])

    async def link_graph(self) -> dict[int, list[int]]:
        """Indexed pages and the links between them; links to pages outside the index are left out."""
        graph = {row["id"]: [] for row in await self.conn.execute_fetchall("SELECT id FROM pages")}
        edges = await self.conn.execute_fetchall(
            "SELECT l.source_id, t.id AS target_id FROM links l JOIN pages t ON t.url = l.target_url"
        )
        for edge in edges:
            graph[edge["source_id"]].append(edge["target_id"])
        return graph

    async def set_ranks(self, ranks: dict[int, float]):
        await self.conn.execute(
            """UPDATE pages SET rank = json_extract(r.value, '$[1]') FROM json_each(?) AS r
            WHERE pages.id = json_extract(r.value, '$[0]')""",
            [json.dumps(list(ranks.items()))],
        )

    async def count_content_words(self) -> int:
        rows = await self.conn.execute_fetchall("SELECT count(DISTINCT word_id) AS count FROM postings WHERE field = 'content'")
        return rows[0]["count"]

    async def clear_all(self):
        """Empty every table of the crawl generation (queue, pages, links, index)."""
        for table in ("postings", "links", "words", "pages", "queue"):
            await self.conn.execute(f"DELETE FROM {table}")
