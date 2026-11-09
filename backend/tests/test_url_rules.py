import pytest

from dijitalvatan.crawler.url_rules import normalize_crawl_url, normalize_public_web_url

SEED = "https://www.tsk.gov.tr/"


def test_normalization_follows_public_domains_and_keeps_scheme():
    assert normalize_crawl_url("../haber?b=2&utm_source=x&a=1#kisim", f"{SEED}dosya/sayfa") == f"{SEED}haber?a=1&b=2"
    assert normalize_crawl_url("http://www.tsk.gov.tr/duyuru", SEED) == "http://www.tsk.gov.tr/duyuru"
    for candidate in ["https://www.tsk.tr/", "https://sub.www.tsk.gov.tr/", "https://other.example/", "http://example.org/article"]:
        assert normalize_crawl_url(candidate, SEED) == candidate
    assert normalize_crawl_url("//other.example/path#fragment", SEED) == "https://other.example/path"
    assert normalize_crawl_url("../article", "http://example.org/news/today") == "http://example.org/article"
    assert normalize_crawl_url("https://EXAMPLE.org.:443/a?utm_campaign=x&z=1", SEED) == "https://example.org/a?z=1"
    assert normalize_crawl_url("https://example.org/", "https://user:secret@bogazici.edu.tr/") is None
    assert normalize_public_web_url("/robots.txt", "https://other.example/") == "https://other.example/robots.txt"
    assert normalize_crawl_url("/robots.txt", "https://other.example/") is None


@pytest.mark.parametrize("candidate", [
    "https://user:password@www.tsk.gov.tr/", "https://www.tsk.gov.tr:8443/", "javascript:alert(1)", "mailto:a@b.test",
    "file:///etc/passwd", "ftp://example.org/", "https://www.tsk.gov.tr/%ZZ", "/test.pdf?download=1", "/image.PNG",
    "/bundle.js", "/bad\\path", "/bad%0Apath", "/bad\x7fpath",
])
def test_rejects_non_page_or_unsafe_urls(candidate):
    assert normalize_crawl_url(candidate, SEED) is None


@pytest.mark.parametrize("candidate", [
    "https://127.0.0.1/", "http://169.254.169.254/", "https://10.1.2.3/", "https://192.168.1.1/", "https://172.16.0.1/",
    "https://8.8.8.8/", "https://127.1/", "https://2130706433/", "https://0x7f000001/", "https://0177.0.0.1/",
    "https://[::1]/", "https://[::ffff:127.0.0.1]/", "https://[2001:4860:4860::8888]/",
    "https://localhost/", "https://localhost./", "https://admin.localhost/", "https://intranet/", "https://router.local/",
    "https://app.internal/", "https://metadata.google.internal/", "https://device.lan/", "https://home.arpa/",
    "https://service.home.arpa/", "https://private.localdomain/", "https://portal.intranet/", "https://hidden.onion/",
    "https://example.invalid/",
])
def test_rejects_ip_literals_and_local_hostnames(candidate):
    assert normalize_public_web_url(candidate, SEED) is None
    assert normalize_crawl_url(candidate, SEED) is None
    assert normalize_public_web_url("/relative", candidate) is None


def test_bogazici_www_alias_is_canonical_while_subdomains_stay_eligible():
    canonical = "https://bogazici.edu.tr/"
    assert normalize_crawl_url("https://www.bogazici.edu.tr/tr/arastirma?utm_source=x", canonical) == f"{canonical}tr/arastirma"
    assert normalize_crawl_url("/tr/kampus", "https://www.bogazici.edu.tr/") == f"{canonical}tr/kampus"
    assert normalize_crawl_url("http://www.bogazici.edu.tr/tr", canonical) == f"{canonical}tr"
    assert normalize_crawl_url("http://bogazici.edu.tr/tr", canonical) == f"{canonical}tr"
    for candidate in ["https://arastirma.bogazici.edu.tr/", "https://cogs.bogazici.edu.tr/", "https://boun.edu.tr/",
                      "https://www.tsk.gov.tr/", "https://other.example/"]:
        assert normalize_crawl_url(candidate, canonical) == candidate
    for candidate in ["https://user:pass@www.bogazici.edu.tr/", "https://www.bogazici.edu.tr:8443/", "/dosya.pdf"]:
        assert normalize_crawl_url(candidate, canonical) is None


def test_non_ascii_paths_are_percent_encoded_once():
    assert normalize_crawl_url("/Türkçe sayfa", SEED) == f"{SEED}T%C3%BCrk%C3%A7e%20sayfa"
    assert normalize_crawl_url("/T%C3%BCrk%C3%A7e", SEED) == f"{SEED}T%C3%BCrk%C3%A7e"
