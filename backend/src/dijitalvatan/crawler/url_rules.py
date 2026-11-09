"""Which URLs the crawler may request, and their single canonical spelling.

Syntax rules only: hostnames must be public DNS names (no IP literals, no local or
internal suffixes). Resolution to private addresses is checked at fetch time.
"""

import re
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlencode, urljoin, urlsplit

MAX_INPUT_CHARS = 4096
MAX_URL_CHARS = 2048
FORBIDDEN_INPUT = re.compile(r"[\x00-\x1f\x7f\\]")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
LOCAL_SUFFIX = re.compile(r"(?:^|\.)(?:localhost|local|localdomain|internal|intranet|lan|home|onion|invalid)$")
PERCENT_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
TRACKING_PARAM = re.compile(r"^(?:utm_.+|fbclid|gclid|dclid|msclkid|_ga|mc_cid|mc_eid)$", re.IGNORECASE)
BINARY_EXTENSION = re.compile(
    r"\.(?:pdf|docx?|xlsx?|pptx?|odt|ods|zip|rar|7z|gz|tar|exe|dmg|apk|iso|mp[34]|m4[av]|avi|mov|wmv|webm|wav|ogg"
    r"|jpe?g|png|gif|webp|avif|svg|ico|bmp|tiff?|css|m?js|map|woff2?|ttf|eot|json|xml|csv|txt)$",
    re.IGNORECASE,
)
DEFAULT_PORTS = {"http": 80, "https": 443}
# Characters kept literally in a path; everything else (space, quotes, non-ASCII ...) is percent-encoded.
PATH_SAFE = "/%:@!$&'()*+,;=-._~[]^|"
# The university's www alias serves the same site as the bare domain.
CANONICAL_HOSTS = {"www.bogazici.edu.tr": "bogazici.edu.tr"}
HTTPS_ONLY_HOSTS = {"bogazici.edu.tr"}


def _public_hostname(hostname: str) -> str | None:
    host = hostname.lower().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = host.split(".")
    if len(host) > 253 or len(labels) < 2 or not re.search(r"[a-z]", labels[-1]):
        return None
    if not all(DNS_LABEL.match(label) for label in labels):
        return None
    if LOCAL_SUFFIX.search(host) or host == "home.arpa" or host.endswith(".home.arpa"):
        return None
    return CANONICAL_HOSTS.get(host, host)


def _split_public(url: str):
    """Split an absolute URL and return (scheme, host, path, query) if it is a public web address."""
    parts = urlsplit(url)
    if parts.scheme not in DEFAULT_PORTS or parts.username is not None or parts.password is not None:
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    if port is not None and port != DEFAULT_PORTS[parts.scheme]:
        return None
    host = _public_hostname(parts.hostname or "")
    if host is None:
        return None
    return parts.scheme, host, parts.path, parts.query


def _decoded_path(path: str) -> str | None:
    """Strict percent-decoding: malformed escapes or invalid UTF-8 make the URL unusable."""
    if PERCENT_ESCAPE.search(path):
        return None
    try:
        return unquote(path, errors="strict")
    except UnicodeDecodeError:
        return None


def normalize_public_web_url(raw: str, base: str) -> str | None:
    if len(raw) > MAX_INPUT_CHARS or len(base) > MAX_INPUT_CHARS or FORBIDDEN_INPUT.search(raw + base):
        return None
    if _split_public(base) is None:
        return None
    split = _split_public(urljoin(base, raw.strip()))
    if split is None:
        return None
    scheme, host, path, query = split
    if host in HTTPS_ONLY_HOSTS:
        scheme = "https"
    # Resolving against a bare origin removes dot segments from absolute input as well.
    path = quote(urlsplit(urljoin("http://x/", path or "/")).path, safe=PATH_SAFE)
    decoded = _decoded_path(path)
    if decoded is None or CONTROL_CHARS.search(decoded):
        return None
    params = [(name, value) for name, value in parse_qsl(query, keep_blank_values=True) if not TRACKING_PARAM.match(name)]
    params.sort(key=lambda pair: pair[0])
    search = f"?{urlencode(params, quote_via=quote_plus)}" if params else ""
    normalized = f"{scheme}://{host}{path}{search}"
    return normalized if len(normalized) <= MAX_URL_CHARS else None


def normalize_crawl_url(raw: str, base: str) -> str | None:
    """A public page URL; files such as PDFs, images and scripts are never crawled."""
    normalized = normalize_public_web_url(raw, base)
    if normalized is None or BINARY_EXTENSION.search(unquote(urlsplit(normalized).path)):
        return None
    return normalized


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"
