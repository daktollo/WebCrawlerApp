"""End to end: control actions → background crawler → SQLite → read views, against a mocked website."""

import asyncio

import httpx
import pytest
import respx

from dijitalvatan import config
from dijitalvatan.crawler.crawl_control import ControlRejected, CrawlControl
from dijitalvatan.crawler.crawler import Crawler
from dijitalvatan.crawler.page_fetcher import PageFetcher
from dijitalvatan.migrate import apply_migrations
from dijitalvatan.storage.database import Database
from dijitalvatan.views.explorer_view import SeedChanged, read_explorer, read_words
from dijitalvatan.views.search_view import search
from dijitalvatan.views.status_view import read_status

SEED = config.BOGAZICI_SEED
HTML = {"Content-Type": "text/html; charset=utf-8"}
PAGES = {
    "": '<title>Ana sayfa</title><p>Boğaziçi Üniversitesi</p><a href="/a">A</a><a href="/b">B</a>'
        '<a href="/gizli/x">Gizli</a><a href="https://other.example/">Dış</a><a href="/dosya.pdf">PDF</a>',
    "a": '<title>Kampüs</title><p>Kampüs ve araştırma hayatı</p><a href="/">Ana</a><a href="/b">B</a>',
    "b": '<head><meta name="robots" content="noindex"></head><p>Gizlenecek sayfa</p><a href="/c">C</a>',
    "c": '<title>Araştırma</title><p>KAMPÜS araştırmaları</p><a href="/a">A</a>',
}


@pytest.fixture
async def system(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MIN_REQUEST_DELAY_MS", 0)
    monkeypatch.setattr(config, "IDLE_POLL_S", 0.05)

    async def any_address_is_public(self, url, origin):
        return None

    monkeypatch.setattr(PageFetcher, "_ensure_public_address", any_address_is_public)
    db_path = tmp_path / "test.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    db = Database(db_path)
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{SEED}robots.txt").respond(200, text="User-agent: *\nDisallow: /gizli\n",
                                               headers={"Content-Type": "text/plain"})
        for path, body in PAGES.items():
            mock.get(f"{SEED}{path}").respond(200, text=body, headers=HTML)
        mock.get("https://other.example/robots.txt").respond(404)
        mock.get("https://other.example/").respond(403, text="Yasak", headers=HTML)
        async with httpx.AsyncClient() as http:
            crawler = Crawler(db, http)
            task = asyncio.create_task(crawler.run())
            yield db, CrawlControl(db, crawler)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def wait_until_stopped(db: Database) -> dict:
    async with asyncio.timeout(20):
        while (status := await read_status(db))["status"] == "running":
            await asyncio.sleep(0.05)
    return status


async def test_full_crawl_indexes_ranks_and_answers_queries(system):
    db, control = system
    await control.apply("start", SEED, 50)
    status = await wait_until_stopped(db)

    assert status["status"] == "completed"
    assert status["lastError"] is None
    assert status["indexedPages"] == 3  # /, /a, /c — /b carries noindex
    assert status["skippedPages"] == 3  # noindex page, robots-denied page, other site's 403
    assert status["failedPages"] == 0
    assert status["queuedPages"] == 0
    errors = {item["url"]: item["error"] for item in status["recentErrors"]}
    assert errors[f"{SEED}gizli/x"] == "robots.txt bu adresin taranmasına izin vermiyor."
    assert errors[f"{SEED}b"] == "Sayfa noindex işareti taşıyor; arama indeksine alınmadı."
    assert errors["https://other.example/"] == "Site bu isteğe erişim izni vermedi (HTTP 403)."
    assert f"{SEED}dosya.pdf" not in errors  # binary files never enter the queue

    found = await search(db, "kampüs", 30)
    assert sorted(result["url"] for result in found["results"]) == [f"{SEED}a", f"{SEED}c"]
    assert found["total"] == 2
    assert all(result["rank"] > 0 for result in found["results"])
    by_url = {result["url"]: result for result in found["results"]}
    assert by_url[f"{SEED}a"]["matchSources"] == ["title", "content"]
    assert by_url[f"{SEED}c"]["matchSources"] == ["content"]

    both = await search(db, "kampus arastirma", 30)
    assert both["total"] == 2
    assert (await search(db, "kampus yok", 30))["total"] == 0
    assert (await search(db, "bogazici", 30))["total"] == 3  # host name matches through the url field

    words = await read_words(db, SEED, "kamp", 0, 50)
    assert [(entry["word"], entry["pageCount"]) for entry in words["entries"]] == [("kampus", 2)]

    explorer = await read_explorer(db, SEED)
    assert set(explorer["graph"]) == {SEED, f"{SEED}a", f"{SEED}c"}
    assert explorer["graph"][f"{SEED}c"] == [f"{SEED}a"]
    assert explorer["stats"]["pages"] == 3
    with pytest.raises(SeedChanged):
        await read_explorer(db, config.TSK_OFFICIAL_SEED)


async def test_page_limit_and_reset(system):
    db, control = system
    await control.apply("start", SEED, 2)
    status = await wait_until_stopped(db)
    assert status["status"] == "limit_reached"
    assert status["visitedPages"] == 2

    first_start = status["startedAt"]
    await control.apply("reset", SEED, 1)
    status = await wait_until_stopped(db)
    assert status["startedAt"] > first_start
    assert status["indexedPages"] == 1
    assert status["visitedPages"] == 1


async def test_actions_require_an_existing_crawl_with_the_same_seed(system):
    db, control = system
    with pytest.raises(ControlRejected):
        await control.apply("pause", SEED, 10)
    await control.apply("start", SEED, 10)
    await control.apply("pause", SEED, 10)
    assert (await read_status(db))["status"] == "paused"
    with pytest.raises(ControlRejected):
        await control.apply("resume", config.TSK_OFFICIAL_SEED, 10)
