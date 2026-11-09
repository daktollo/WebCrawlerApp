"""Visible text, metadata and outlinks of an HTML page."""

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

from dijitalvatan.crawler.url_rules import normalize_crawl_url
from dijitalvatan.indexing.text_normalizer import normalize_search_text

MAX_HTML_CHARS = 2 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_TITLE_CHARS = 300
MAX_DESCRIPTION_CHARS = 500
DESCRIPTION_FROM_TEXT_CHARS = 300
MAX_LINKS = 500
REMOVED_TAGS = {"head", "script", "style", "noscript", "template", "svg", "form", "iframe", "canvas", "object"}
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "details", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
    "section", "summary", "table", "td", "th", "tr", "ul",
}
HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\s*(?:!important\s*)?(?:;|$)", re.IGNORECASE
)
INVISIBLE_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏﻿]")
WHITESPACE = re.compile(r"\s+")
CHALLENGE_TITLE = re.compile(
    r"^(?:just a moment|access denied|attention required|security verification|verify you are human|robot check)(?:\b|$)",
    re.IGNORECASE,
)
CAPTCHA_FORM = re.compile(r"(?:captcha\s+characters|(?:placeholder|name|id)\s*=\s*[\"'][^\"']*(?:captcha|cf-chl))", re.IGNORECASE)
CHALLENGE_TEXT = re.compile(
    r"(?:verify (?:that )?you are human|checking your browser|please complete the security check"
    r"|insan oldugunuzu dogrulayin|robot olmadiginizi dogrulayin)",
    re.IGNORECASE,
)
BLOCKED_MESSAGE = "Kaynak site insan doğrulaması veya güvenlik kontrolü istiyor. Koruma sayfası indekse alınmadı."


class HtmlTooLarge(Exception):
    pass


@dataclass
class ExtractedHtml:
    title: str
    text: str
    description: str
    links: list[str]
    noindex: bool
    nofollow: bool
    blocked_reason: str | None


def _clean(text: str, limit: int) -> str:
    return WHITESPACE.sub(" ", INVISIBLE_CHARS.sub("", text)).strip()[:limit]


def _is_hidden(node: LexborNode) -> bool:
    attributes = node.attributes
    return (
        node.tag in REMOVED_TAGS
        or "hidden" in attributes
        or (attributes.get("aria-hidden") or "").lower() == "true"
        or bool(HIDDEN_STYLE.search(attributes.get("style") or ""))
    )


def _blocked_reason(title: str, text: str, html: str) -> str | None:
    """Access challenges are a stop signal, never content to index or work around."""
    normalized = normalize_search_text(f"{title} {text}")
    security_notice = (
        "minimum system security requirements" in normalized
        or "minimum sistem guvenlik gereksinimlerini karsilayamadiginizdan" in normalized
    )
    if security_notice or CHALLENGE_TITLE.search(title.strip()):
        return BLOCKED_MESSAGE
    if len(text) < 5000 and (CAPTCHA_FORM.search(html) or CHALLENGE_TEXT.search(normalized)):
        return BLOCKED_MESSAGE
    return None


class _VisibleContent:
    """Walks the document once, skipping hidden subtrees, collecting text and links."""

    def __init__(self, base: str, url: str):
        self.base = base
        self.url = url
        self.parts: list[str] = []
        self.size = 0
        self.links: dict[str, None] = {}

    def _add_text(self, value: str):
        if self.size >= MAX_TEXT_CHARS:
            return
        part = value[: MAX_TEXT_CHARS - self.size]
        self.parts.append(part)
        self.size += len(part)

    def _add_link(self, node: LexborNode):
        if len(self.links) >= MAX_LINKS or "nofollow" in (node.attributes.get("rel") or "").lower().split():
            return
        link = normalize_crawl_url(urljoin(self.base, node.attributes["href"] or ""), self.url)
        if link:
            self.links[link] = None

    def walk(self, root: LexborNode):
        # Explicit stack: deeply nested pages must not hit Python's recursion limit.
        stack: list[LexborNode | str] = [root]
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                self._add_text(node)
                continue
            if node.tag == "-text":
                self._add_text(node.text(deep=False))
                continue
            if node.tag.startswith("-") or _is_hidden(node):
                continue
            if node.tag == "a" and "href" in node.attributes:
                self._add_link(node)
            if node.tag in BLOCK_TAGS:
                self._add_text(" ")
                if node.tag not in ("br", "hr"):
                    stack.append(" ")
            stack.extend(reversed(list(node.iter(include_text=True))))

    @property
    def text(self) -> str:
        return "".join(self.parts)


def extract_html(html: str, url: str) -> ExtractedHtml:
    if len(html) > MAX_HTML_CHARS:
        raise HtmlTooLarge("HTML sayfası 2 MB sınırını aşıyor.")
    tree = LexborHTMLParser(html)
    title_node = tree.css_first("title")
    title = title_node.text() if title_node else ""

    description = ""
    noindex = nofollow = False
    for meta in tree.css("meta"):
        name = (meta.attributes.get("name") or "").lower()
        content = meta.attributes.get("content") or ""
        if name == "description" and not description:
            description = _clean(content, MAX_DESCRIPTION_CHARS)
        if name in ("robots", "dijitalvatanbot"):
            values = re.split(r"[\s,]+", content.lower())
            noindex = noindex or "noindex" in values or "none" in values
            nofollow = nofollow or "nofollow" in values or "none" in values

    base = url
    base_node = tree.css_first("base[href]")
    if base_node:
        base = urljoin(url, base_node.attributes["href"] or "")

    content = _VisibleContent(base, url)
    content.walk(tree.root)
    title = _clean(title, MAX_TITLE_CHARS) or (urlsplit(url).hostname or "")
    text = _clean(content.text, MAX_TEXT_CHARS)
    blocked = _blocked_reason(title, text, html)
    return ExtractedHtml(
        title=title,
        text="" if blocked else text,
        description="" if blocked else description or text[:DESCRIPTION_FROM_TEXT_CHARS],
        links=[] if blocked or nofollow else list(content.links),
        noindex=noindex or blocked is not None,
        nofollow=nofollow or blocked is not None,
        blocked_reason=blocked,
    )
