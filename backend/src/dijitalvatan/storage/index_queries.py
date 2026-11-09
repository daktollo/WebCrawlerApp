"""Read queries behind the status, search, word-index and map endpoints."""

import json

import aiosqlite


class IndexQueries:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def _all(self, sql: str, params=()) -> list[dict]:
        return [dict(row) for row in await self.conn.execute_fetchall(sql, params)]

    async def page_summary(self) -> dict:
        return (await self._all("SELECT count(*) AS count, max(indexed_at) AS latest FROM pages"))[0]

    async def link_count(self) -> int:
        return (await self._all("SELECT count(*) AS count FROM links"))[0]["count"]

    async def recent_pages(self, limit: int) -> list[dict]:
        return await self._all("SELECT url, title, indexed_at FROM pages ORDER BY indexed_at DESC LIMIT ?", [limit])

    async def top_pages(self, limit: int) -> list[dict]:
        return await self._all(
            "SELECT url, title, body, description, indexed_at, rank, '' AS fields FROM pages "
            "ORDER BY rank DESC, indexed_at DESC LIMIT ?",
            [limit],
        )

    async def pages_with_all_terms(self, terms: list[str], limit: int) -> tuple[list[dict], int]:
        """Pages containing every term in any field, by PageRank; also the total number of matches.

        `fields` is a comma-separated list of the fields (content/title/url) where a term occurs.
        """
        rows = await self._all(
            """WITH matched AS (
                SELECT po.page_id, group_concat(DISTINCT po.field) AS fields
                FROM postings po JOIN words w ON w.id = po.word_id
                WHERE w.word IN (SELECT value FROM json_each(:terms))
                GROUP BY po.page_id
                HAVING count(DISTINCT w.word) = :count
            )
            SELECT p.url, p.title, p.body, p.description, p.indexed_at, p.rank, m.fields, count(*) OVER () AS total
            FROM matched m JOIN pages p ON p.id = m.page_id
            ORDER BY p.rank DESC, p.url LIMIT :limit""",
            {"terms": json.dumps(terms), "count": len(terms), "limit": limit},
        )
        return rows, rows[0]["total"] if rows else 0

    async def content_words(self, contains: str, offset: int, limit: int) -> tuple[list[dict], int]:
        """Words of page bodies containing a substring, in byte order, with how many pages use each."""
        match = """FROM words w JOIN postings po ON po.word_id = w.id AND po.field = 'content'
            WHERE instr(w.word, :contains) > 0"""
        params = {"contains": contains, "offset": offset, "limit": limit}
        rows = await self._all(
            f"SELECT w.word, count(*) AS page_count {match} GROUP BY w.word ORDER BY w.word LIMIT :limit OFFSET :offset",
            params,
        )
        total = (await self._all(f"SELECT count(DISTINCT w.id) AS count {match}", params))[0]["count"]
        return rows, total

    async def word_previews(self, words: list[str], per_word: int) -> list[dict]:
        """The highest-ranked pages whose body contains each word."""
        return await self._all(
            """SELECT word, url, title FROM (
                SELECT w.word, p.url, p.title,
                    row_number() OVER (PARTITION BY w.word ORDER BY p.rank DESC, p.url) AS position
                FROM words w
                JOIN postings po ON po.word_id = w.id AND po.field = 'content'
                JOIN pages p ON p.id = po.page_id
                WHERE w.word IN (SELECT value FROM json_each(:words))
            ) WHERE position <= :per_word ORDER BY word, position""",
            {"words": json.dumps(words), "per_word": per_word},
        )

    async def all_pages(self) -> list[dict]:
        return await self._all("SELECT url, title, description, indexed_at, rank FROM pages ORDER BY rank DESC, url")

    async def indexed_links(self) -> list[dict]:
        """Links whose two ends are both indexed pages."""
        return await self._all(
            """SELECT s.url AS source, t.url AS target FROM links l
            JOIN pages s ON s.id = l.source_id JOIN pages t ON t.url = l.target_url
            ORDER BY s.url, t.url"""
        )
