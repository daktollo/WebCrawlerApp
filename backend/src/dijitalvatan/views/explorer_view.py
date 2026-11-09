"""GET /api/crawl/explorer and /api/crawl/words: the link map and the word index of the live crawl."""

from dijitalvatan import config
from dijitalvatan.indexing.text_normalizer import normalize_search_text
from dijitalvatan.storage.crawl_state_repository import CrawlState, CrawlStateRepository
from dijitalvatan.storage.database import Database
from dijitalvatan.storage.index_queries import IndexQueries
from dijitalvatan.storage.queue_repository import QueueRepository


class SeedChanged(Exception):
    """The client asked about a crawl source that is no longer the active one."""


def _check_seed(state: CrawlState, expected_seed: str | None):
    if expected_seed is not None and expected_seed != (state.seed or config.DEFAULT_SEED):
        raise SeedChanged()


async def read_explorer(db: Database, expected_seed: str | None) -> dict:
    """Every indexed page (without bodies) and the links between indexed pages."""
    async with db.snapshot() as conn:
        state = await CrawlStateRepository(conn).get()
        _check_seed(state, expected_seed)
        queries = IndexQueries(conn)
        pages = await queries.all_pages()
        links = await queries.indexed_links()
        discovered_links = await queries.link_count()
        queued = (await QueueRepository(conn).counts()).get("queued", 0)
    graph: dict[str, list[str]] = {page["url"]: [] for page in pages}
    for link in links:
        graph[link["source"]].append(link["target"])
    return {
        "ok": True,
        "seed": state.seed or config.DEFAULT_SEED,
        "startedAt": state.started_at,
        "status": state.status,
        "revision": state.revision,
        "updatedAt": state.updated_at,
        "graph": graph,
        "pages": {page["url"]: {"title": page["title"], "description": page["description"],
                                "indexedAt": page["indexed_at"], "rank": page["rank"]} for page in pages},
        "stats": {"pages": len(pages), "links": len(links), "discoveredLinks": discovered_links,
                  "words": state.indexed_words, "queued": queued},
    }


async def read_words(db: Database, expected_seed: str | None, query: str, offset: int, limit: int) -> dict:
    """Body words containing the (normalized) filter, alphabetically, with a few top-ranked pages each."""
    contains = normalize_search_text(query)
    async with db.snapshot() as conn:
        state = await CrawlStateRepository(conn).get()
        _check_seed(state, expected_seed)
        entries, total = [], 0
        if contains or not query:
            queries = IndexQueries(conn)
            rows, total = await queries.content_words(contains, offset, limit)
            previews = await queries.word_previews([row["word"] for row in rows], config.WORD_PREVIEW_PAGES)
            pages_by_word: dict[str, list[dict]] = {}
            for preview in previews:
                pages_by_word.setdefault(preview["word"], []).append({"url": preview["url"], "title": preview["title"]})
            entries = [{"word": row["word"], "pageCount": row["page_count"], "pages": pages_by_word.get(row["word"], [])}
                       for row in rows]
    return {
        "ok": True,
        "seed": state.seed or config.DEFAULT_SEED,
        "startedAt": state.started_at,
        "revision": state.revision,
        "query": query,
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": entries,
    }
