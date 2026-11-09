"""HTTP layer: response shape, validation messages and status codes."""

import pytest
from fastapi.testclient import TestClient

from dijitalvatan import config
from dijitalvatan.api.app import app
from dijitalvatan.migrate import apply_migrations


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "api.db")
    monkeypatch.setattr(config, "CRAWLER_LOCK_PATH", tmp_path / "crawler.lock")
    apply_migrations(config.DB_PATH, config.MIGRATIONS_DIR)
    with TestClient(app) as test_client:
        yield test_client


def error(response) -> tuple[int, str]:
    body = response.json()
    assert body["ok"] is False
    assert response.headers["Cache-Control"] == "no-store"
    return response.status_code, body["error"]


def test_status_of_a_fresh_database(client):
    body = client.get("/api/crawl/status").json()
    assert body["ok"] is True
    assert body["status"] == "idle"
    assert body["seed"] == config.DEFAULT_SEED
    assert body["maxPages"] == 200
    assert body["indexedPages"] == 0


def test_control_validation(client):
    post = lambda body: client.post("/api/crawl/control", json=body)  # noqa: E731
    assert error(post({"action": "jump"})) == (400, "Geçersiz tarama işlemi.")
    assert error(post({"action": "reset", "seed": config.BOGAZICI_SEED}))[0] == 400
    assert error(post({"action": "start", "seed": "https://example.org/"}))[0] == 400
    assert error(post({"action": "start", "maxPages": 0}))[0] == 400
    assert error(post({"action": "start", "maxPages": "5"}))[0] == 400
    assert error(post({"action": "pause"})) == (409, "Önce bir tarama başlatın.")
    assert error(client.post("/api/crawl/control", content="x", headers={"Content-Type": "text/plain"}))[0] == 415


def test_start_accepts_the_www_alias_and_pause_stops(client):
    started = client.post("/api/crawl/control", json={"action": "start", "seed": config.BOGAZICI_REQUESTED_SEED, "maxPages": 5})
    assert started.status_code == 200
    assert started.json()["seed"] == config.BOGAZICI_SEED
    paused = client.post("/api/crawl/control", json={"action": "pause"}).json()
    assert paused["status"] == "paused"
    assert paused["maxPages"] == 5


def test_read_endpoint_validation(client):
    assert error(client.get("/api/crawl/search", params={"q": "x" * 201}))[0] == 400
    assert error(client.get("/api/crawl/words", params={"offset": "-1"})) == (400, "Geçerli bir sayfalama aralığı gönderin.")
    assert error(client.get("/api/crawl/explorer", params={"seed": "https://www.tsk.tr/"}))[0] == 409
    assert error(client.get("/api/crawl/nothing")) == (404, "Bu tarama işlemi bulunamadı.")
    assert client.get("/api/crawl/search", params={"q": "kampüs"}).json()["total"] == 0
