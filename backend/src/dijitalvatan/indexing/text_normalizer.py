"""Turkish-aware folding shared by indexed text and queries."""

import re
import unicodedata
from urllib.parse import unquote, urlsplit

NON_WORD = re.compile(r"[\W_]+")
MAX_TOKEN_CHARS = 80


def normalize_search_text(text: str) -> str:
    """Lowercase, strip accents (ş→s, ğ→g, ı→i) and collapse non-alphanumeric runs to one space."""
    decomposed = unicodedata.normalize("NFKD", text).lower()
    unaccented = "".join(ch for ch in decomposed if not unicodedata.category(ch).startswith("M"))
    return NON_WORD.sub(" ", unaccented.replace("ı", "i")).strip()


def tokenize(text: str) -> list[str]:
    return [word for word in normalize_search_text(text).split(" ") if 0 < len(word) <= MAX_TOKEN_CHARS]


def url_text(url: str) -> str:
    """The searchable words of an address: host name and decoded path."""
    parts = urlsplit(url)
    return normalize_search_text(f"{parts.hostname} {unquote(parts.path)}")
