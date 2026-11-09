"""/api/crawl/* endpoints. Errors are answered as {"ok": false, "error": "<Turkish message>"}."""

import json

from fastapi import APIRouter, Request

from dijitalvatan import config
from dijitalvatan.crawler.crawl_control import ACTIONS, ControlRejected
from dijitalvatan.storage.crawl_state_repository import CrawlStateRepository
from dijitalvatan.views.explorer_view import SeedChanged, read_explorer, read_words
from dijitalvatan.views.search_view import search
from dijitalvatan.views.status_view import read_status

MAX_SAFE_INTEGER = 2**53 - 1
MAX_CONTROL_BODY = 2048

router = APIRouter(prefix="/api/crawl")


class ApiError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status


def _query(value: str, label: str) -> str:
    query = value.strip()
    if len(query) > config.MAX_QUERY_CHARS:
        raise ApiError(f"{label} en fazla {config.MAX_QUERY_CHARS} karakter olabilir.", 400)
    return query


@router.get("/status")
async def status(request: Request):
    return await read_status(request.app.state.db)


@router.get("/search")
async def search_index(request: Request, q: str = "", limit: str = ""):
    query = _query(q, "Arama")
    requested = int(limit) if limit.isdigit() and int(limit) > 0 else config.SEARCH_DEFAULT_LIMIT
    bounded = min(config.SEARCH_MAX_LIMIT, requested)
    return await search(request.app.state.db, query, bounded)


@router.get("/explorer")
async def explorer(request: Request, seed: str | None = None):
    try:
        return await read_explorer(request.app.state.db, seed)
    except SeedChanged:
        raise ApiError("Tarama kaynağı değişti. Güncel veriyi yeniden yükleyin.", 409)


@router.get("/words")
async def words(request: Request, q: str = "", offset: str = "0", limit: str = str(config.WORDS_DEFAULT_LIMIT),
                seed: str | None = None):
    query = _query(q, "Kelime filtresi")
    if not (offset.isdigit() and limit.isdigit()) or int(limit) < 1:
        raise ApiError("Geçerli bir sayfalama aralığı gönderin.", 400)
    try:
        return await read_words(request.app.state.db, seed, query, int(offset), min(config.WORDS_MAX_LIMIT, int(limit)))
    except SeedChanged:
        raise ApiError("Tarama kaynağı değişti. Güncel veriyi yeniden yükleyin.", 409)


@router.post("/control")
async def control(request: Request):
    action, seed, max_pages = await _control_input(request)
    try:
        await request.app.state.control.apply(action, seed, max_pages)
    except ControlRejected as rejected:
        raise ApiError(rejected.message, rejected.status)
    return await read_status(request.app.state.db)


async def _control_input(request: Request) -> tuple[str, str, int]:
    """Validate the JSON body: {"action", "seed"?, "maxPages"?, "confirmReset"?}."""
    if "application/json" not in request.headers.get("Content-Type", ""):
        raise ApiError("JSON biçiminde bir istek gönderin.", 415)
    raw = await request.body()
    if len(raw) > MAX_CONTROL_BODY:
        raise ApiError("İstek çok büyük.", 413)
    try:
        body = json.loads(raw)
    except ValueError:
        raise ApiError("Geçerli bir JSON isteği gönderin.", 400)
    if not isinstance(body, dict):
        raise ApiError("Geçersiz tarama isteği.", 400)
    action = body.get("action")
    if action not in ACTIONS:
        raise ApiError("Geçersiz tarama işlemi.", 400)
    if action == "reset" and body.get("confirmReset") is not True:
        raise ApiError("Tüm tarama verilerini silip yeniden başlatmak için açık onay gereklidir.", 400)

    async with request.app.state.db.snapshot() as conn:
        current = await CrawlStateRepository(conn).get()
    seed = config.SEED_ALIASES.get(body["seed"]) if "seed" in body else (current.seed or config.DEFAULT_SEED)
    if seed is None:
        raise ApiError("Başlangıç adresi yalnızca bogazici.edu.tr, www.bogazici.edu.tr, www.tsk.gov.tr veya www.tsk.tr olabilir.", 400)
    max_pages = body.get("maxPages", None if action == "set_limit" else current.max_pages)
    if type(max_pages) is not int or not 1 <= max_pages <= MAX_SAFE_INTEGER:
        raise ApiError("Sayfa sınırı pozitif bir tam sayı olmalıdır. Sayısal olarak tam temsil edilemeyen değerler "
                       "kullanılamaz.", 400)
    return action, seed, max_pages
