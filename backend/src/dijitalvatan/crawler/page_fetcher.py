"""Polite HTTP fetching: robots.txt per site, request spacing, manual redirects, size and address limits."""

import asyncio
import ipaddress
import re
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from dijitalvatan import config
from dijitalvatan.crawler import errors
from dijitalvatan.crawler.errors import CrawlFailure, OriginBlocked, SkipPage
from dijitalvatan.crawler.html_extractor import extract_html
from dijitalvatan.crawler.robots import RobotsPolicy, parse_robots
from dijitalvatan.crawler.url_rules import normalize_crawl_url, normalize_public_web_url, origin_of
from dijitalvatan.storage.database import Database, now_ms
from dijitalvatan.storage.origin_repository import OriginRepository

CHARSET = re.compile(r"charset\s*=\s*[\"']?([^\s;\"']+)", re.IGNORECASE)
HTML_TYPE = re.compile(r"text/html|application/xhtml\+xml", re.IGNORECASE)
HTML_START = re.compile(r"^\s*<!doctype html|^\s*<html", re.IGNORECASE)
ACCEPT = {"page": "text/html,application/xhtml+xml", "robots": "text/plain,*/*;q=0.5"}


@dataclass
class SourceResponse:
    url: str
    status: int
    body: str
    content_type: str
    robots_header: str


def _decode(data: bytes, content_type: str) -> str:
    match = CHARSET.search(content_type)
    try:
        return data.decode(match.group(1) if match else "utf-8", errors="replace")
    except LookupError:  # unknown charset label: decode as UTF-8, like browsers do
        return data.decode("utf-8", errors="replace")


def _retry_at_ms(header: str) -> int | None:
    """Retry-After as seconds or an HTTP date; None when unparseable."""
    if header.strip().isdigit():
        return now_ms() + int(header) * 1000
    try:
        moment = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    return int((moment if moment.tzinfo else moment.replace(tzinfo=UTC)).timestamp() * 1000)


class PageFetcher:
    def __init__(self, db: Database, http: httpx.AsyncClient, wait: Callable[[float], Awaitable[None]]):
        """`wait(seconds)` sleeps and then raises CrawlChanged if the crawl stopped meanwhile."""
        self.db = db
        self.http = http
        self.wait = wait
        self._next_request = 0.0  # monotonic time of the next allowed request to any site

    async def fetch(self, initial_url: str, kind: str) -> SourceResponse:
        """GET a page ("page") or robots.txt ("robots"), following up to MAX_REDIRECTS redirects."""
        normalize = normalize_crawl_url if kind == "page" else normalize_public_web_url
        url = initial_url
        for _ in range(config.MAX_REDIRECTS):
            normalized = normalize(url, initial_url)
            if normalized is None:
                raise SkipPage(errors.NOT_PUBLIC)
            url = normalized
            origin = origin_of(url)
            if kind == "page" and not (await self.robots_policy(origin)).allows(url):
                raise SkipPage(errors.ROBOTS_DENIED, robots_denied=True)
            await self._pace(origin)
            await self._ensure_public_address(url, origin)
            response = await self._get(url, origin, kind)
            if isinstance(response, SourceResponse):
                return response
            target = normalize(response, url)
            if target is None:
                raise SkipPage(errors.REDIRECT_NOT_PUBLIC)
            url = target
        raise CrawlFailure(errors.TOO_MANY_REDIRECTS, "error", origin_of(url))

    async def robots_policy(self, origin: str) -> RobotsPolicy:
        async with self.db.transaction() as conn:
            state = await OriginRepository(conn).get(origin)
        if state.blocked_reason:
            raise OriginBlocked(state.blocked_reason, state.blocked_phase or "blocked", origin)
        if state.robots_policy and now_ms() - state.robots_checked_at_ms < config.ROBOTS_CACHE_S * 1000:
            return RobotsPolicy.from_json(state.robots_policy)
        try:
            response = await self.fetch(f"{origin}/robots.txt", "robots")
            policy = self._robots_from_response(response, origin)
        except SkipPage as skip:
            raise CrawlFailure(skip.message, "blocked", origin) from skip
        except CrawlFailure as failure:
            raise CrawlFailure(failure.message, failure.phase, origin) from failure
        async with self.db.transaction() as conn:
            await OriginRepository(conn).save_robots(origin, policy.to_json(), max(config.MIN_REQUEST_DELAY_MS, policy.delay_ms))
        return policy

    def _robots_from_response(self, response: SourceResponse, origin: str) -> RobotsPolicy:
        status = response.status
        if status in (404, 410):
            return parse_robots("")
        if status in (401, 403):
            raise CrawlFailure(f"robots.txt erişimi engellendi (HTTP {status}). Bu sitenin tarama izni doğrulanamadı.", "blocked", origin)
        if status >= 500 or status == 429:
            raise CrawlFailure(f"robots.txt alınamadı (HTTP {status}). İzin doğrulanana kadar bu sitenin sayfaları taranmayacak.", "error", origin)
        if not 200 <= status < 300:
            raise CrawlFailure(f"robots.txt beklenmeyen HTTP {status} yanıtı verdi.", "error", origin)
        if HTML_TYPE.search(response.content_type) or HTML_START.search(response.body):
            reason = extract_html(response.body[: 2 * 1024 * 1024], response.url).blocked_reason
            raise CrawlFailure(reason or "robots.txt yerine bir HTML doğrulama veya hata sayfası döndü. Tarama izni doğrulanamadı.",
                               "blocked", origin)
        return parse_robots(response.body)

    async def _pace(self, origin: str):
        """At most one request per MIN_REQUEST_DELAY_MS overall, and per site at its crawl-delay."""
        async with self.db.transaction() as conn:
            state = await OriginRepository(conn).get(origin)
        if state.blocked_reason:
            raise OriginBlocked(state.blocked_reason, state.blocked_phase or "blocked", origin)
        site_wait = (state.next_request_at_ms - now_ms()) / 1000
        await self.wait(max(0.0, self._next_request - time.monotonic(), site_wait))
        self._next_request = time.monotonic() + config.MIN_REQUEST_DELAY_MS / 1000
        async with self.db.transaction() as conn:
            await OriginRepository(conn).schedule_next(origin, max(config.MIN_REQUEST_DELAY_MS, state.delay_ms))

    async def _ensure_public_address(self, url: str, origin: str):
        """Refuse hostnames that resolve to private, loopback or link-local addresses."""
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(urlsplit(url).hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            raise CrawlFailure(errors.CONNECT_FAILED, "error", origin) from error
        if any(not ipaddress.ip_address(info[4][0].split("%")[0]).is_global for info in infos):
            raise SkipPage(errors.NOT_PUBLIC)

    async def _get(self, url: str, origin: str, kind: str) -> SourceResponse | str:
        """The response, or the Location of a redirect."""
        try:
            async with asyncio.timeout(config.FETCH_TIMEOUT_S):
                async with self.http.stream("GET", url, headers={"Accept": ACCEPT[kind]}) as response:
                    if response.status_code in (429, 503) and "Retry-After" in response.headers:
                        retry_at = _retry_at_ms(response.headers["Retry-After"])
                        if retry_at:
                            async with self.db.transaction() as conn:
                                await OriginRepository(conn).defer_until(origin, retry_at)
                    if 300 <= response.status_code < 400:
                        if "Location" not in response.headers:
                            raise CrawlFailure(errors.NO_LOCATION, "error", origin)
                        return response.headers["Location"]
                    content_type = response.headers.get("Content-Type", "")
                    if int(response.headers.get("Content-Length") or 0) > config.MAX_HTML_BYTES:
                        raise SkipPage(errors.TOO_LARGE)
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data += chunk
                        if len(data) > config.MAX_HTML_BYTES:
                            raise SkipPage(errors.TOO_LARGE)
                    return SourceResponse(url, response.status_code, _decode(bytes(data), content_type), content_type,
                                          response.headers.get("X-Robots-Tag", ""))
        except TimeoutError as error:
            raise CrawlFailure(errors.TIMEOUT, "error", origin) from error
        except httpx.HTTPError as error:
            raise CrawlFailure(errors.CONNECT_FAILED, "error", origin) from error
