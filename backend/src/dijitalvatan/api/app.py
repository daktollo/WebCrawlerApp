"""FastAPI application: crawl API, the background crawler and the built frontend."""

import asyncio
import fcntl
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from dijitalvatan import config
from dijitalvatan.api.crawl_routes import ApiError, router
from dijitalvatan.crawler.crawl_control import CrawlControl
from dijitalvatan.crawler.crawler import Crawler
from dijitalvatan.migrate import migration_files
from dijitalvatan.storage.database import Database

logger = logging.getLogger(__name__)
NO_STORE = {"Cache-Control": "no-store"}


def _try_crawler_lock():
    """An exclusive file lock: only one server process may run the crawler. None if another holds it."""
    config.CRAWLER_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = open(config.CRAWLER_LOCK_PATH, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(config.DB_PATH)
    await db.ensure_migrated([path.name for path in migration_files(config.MIGRATIONS_DIR)])
    http = httpx.AsyncClient(follow_redirects=False, headers={"User-Agent": config.USER_AGENT})
    crawler = Crawler(db, http)
    lock = _try_crawler_lock()
    task = asyncio.create_task(crawler.run()) if lock else None
    if lock is None:
        logger.error("Another server process holds %s; this process serves the API without crawling.",
                     config.CRAWLER_LOCK_PATH)
    app.state.db = db
    app.state.control = CrawlControl(db, crawler)
    yield
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        lock.close()
    await http.aclose()


app = FastAPI(title="Dijital Vatan", lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def no_store_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers.update(NO_STORE)
    return response


@app.exception_handler(ApiError)
async def api_error(request: Request, error: ApiError):
    return JSONResponse({"ok": False, "error": error.message}, status_code=error.status, headers=NO_STORE)


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    if request.url.path.startswith("/api/") and error.status_code == 404:
        return JSONResponse({"ok": False, "error": "Bu tarama işlemi bulunamadı."}, status_code=404, headers=NO_STORE)
    return JSONResponse({"ok": False, "error": str(error.detail)}, status_code=error.status_code, headers=NO_STORE)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    # Starlette logs the traceback of exceptions reaching this handler.
    return JSONResponse({"ok": False, "error": "Sunucuda beklenmeyen bir hata oluştu. Ayrıntı sunucu kaydında."},
                        status_code=500, headers=NO_STORE)


if config.FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")
else:
    logger.warning("%s not found: serving the API only. Build the frontend with `npm run build` in frontend/.",
                   config.FRONTEND_DIST)
