"""GET /api/crawl/search: pages containing every query word, ordered by PageRank."""

import time

from dijitalvatan.indexing.text_normalizer import normalize_search_text, tokenize
from dijitalvatan.storage.crawl_state_repository import CrawlStateRepository
from dijitalvatan.storage.database import Database
from dijitalvatan.storage.index_queries import IndexQueries

SNIPPET_LEAD_CHARS = 75
SNIPPET_CHARS = 270
MATCH_SOURCE_ORDER = ("title", "content", "url")


def snippet(body: str, terms: list[str], fallback: str) -> str:
    """A window of the body around the first query word, or the page description."""
    if not body:
        return fallback
    normalized = normalize_search_text(body)
    positions = [found for term in terms if (found := normalized.find(term)) >= 0]
    start = max(0, min(positions, default=-1) - SNIPPET_LEAD_CHARS)
    text = body[start:start + SNIPPET_CHARS].strip()
    return f"{'…' if start else ''}{text}{'…' if len(body) > start + SNIPPET_CHARS else ''}"


async def search(db: Database, query: str, limit: int) -> dict:
    started = time.perf_counter()
    terms = list(dict.fromkeys(tokenize(query)))
    async with db.snapshot() as conn:
        state = await CrawlStateRepository(conn).get()
        queries = IndexQueries(conn)
        indexed = (await queries.page_summary())["count"]
        if terms:
            rows, total = await queries.pages_with_all_terms(terms, limit)
        elif query:
            rows, total = [], 0  # the query had no searchable word
        else:
            rows, total = await queries.top_pages(limit), indexed
    results = []
    for row in rows:
        fields = set(row["fields"].split(",")) if row["fields"] else set()
        results.append({
            "url": row["url"],
            "title": row["title"],
            "description": snippet(row["body"], terms, row["description"]),
            "rank": row["rank"],
            "indexedAt": row["indexed_at"],
            "matchSources": [source for source in MATCH_SOURCE_ORDER if source in fields],
        })
    return {
        "ok": True,
        "startedAt": state.started_at,
        "query": query,
        "results": results,
        "total": total,
        "tookMs": round((time.perf_counter() - started) * 1000),
        "indexedPages": indexed,
        "revision": state.revision,
        "status": state.status,
    }
