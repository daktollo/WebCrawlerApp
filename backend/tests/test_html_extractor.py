import re

import pytest

from dijitalvatan.crawler.html_extractor import HtmlTooLarge, extract_html

SEED = "https://www.tsk.gov.tr/"


def test_removes_non_visible_code_and_joins_inline_word_chunks():
    result = extract_html("""<!doctype html><html><head><title>TSK &amp; Duyurular</title>
    <meta name="description" content="Türk &amp; Dünya"><style>.a{color:red}</style></head><body>
    <h1>Gü<b>n</b>dem &ccedil; &#x130;</h1><p>İkinci satır &NotEqualTilde;</p>
    <script>secretCode()</script><style>cssSecret</style><noscript>hiddenNoScript</noscript>
    <template>hiddenTemplate</template><svg><text>hiddenSvg</text></svg><form>hiddenForm</form>
    <div hidden>hiddenAttribute <a href="/hidden-link">hidden link</a></div>
    <div aria-hidden="true">hiddenAria</div><span style="display: none !important;">hiddenStyle</span>
    <a href="/acik?a=1&amp;b=2">Açık bağlantı</a><a href="/atla" rel="nofollow">Diğer</a>
    <a href="https://other.example/">Dış bağlantı</a><a href="http://127.1/">İç adres</a></body></html>""", SEED)
    assert result.title == "TSK & Duyurular"
    assert result.description == "Türk & Dünya"
    assert re.search("Gündem ç İ İkinci satır ≂̸", result.text)
    assert not re.search(r"secret|hidden|cssSecret|color:red|<[^>]+>", result.text, re.IGNORECASE)
    assert result.links == [f"{SEED}acik?a=1&b=2", "https://other.example/"]
    assert result.noindex is False


def test_meta_noindex_nofollow_and_base_links():
    result = extract_html('<html><head><base href="/duyurular/"><meta name="ROBOTS" content="NOINDEX, nofollow"></head>'
                          '<body>Okunabilir içerik<a href="bir">Bir</a></body></html>', SEED)
    assert result.noindex and result.nofollow
    assert result.links == []
    assert extract_html('<head><base href="/duyurular/"></head><a href="bir">Bir</a>', SEED).links == [f"{SEED}duyurular/bir"]
    assert extract_html('<head><base href="https://other.example/"></head><a href="bir">Bir</a>', SEED).links == [
        "https://other.example/bir"]
    internal = extract_html('<head><base href="http://169.254.169.254/"></head><a href="private">Özel</a>'
                            '<a href="https://example.org/public">Açık</a>', SEED)
    assert internal.links == ["https://example.org/public"]


@pytest.mark.parametrize("fixture", [
    '<title>Türk Silahlı Kuvvetleri Genelkurmay Başkanlığı</title><form><input placeholder="Please type captcha characters">'
    '<button>Send</button></form>',
    '<title>Türk Silahlı Kuvvetleri Genelkurmay Başkanlığı</title><p>Ulaşmaya çalıştığınız örün sitesinin minimum sistem '
    'güvenlik gereksinimlerini karşılayamadığınızdan dolayı sayfaya yönlendirilmediniz.</p>',
    '<p>You were not redirected to the page because you did not complete the minimum system security requirements of the '
    'website that you are trying to reach.</p>',
    '<title>Just a moment...</title><p>Checking your browser</p>',
])
def test_captcha_and_security_pages_are_never_indexed_or_followed(fixture):
    result = extract_html(fixture + '<a href="/next">Devam</a>', SEED)
    assert result.blocked_reason
    assert result.text == ""
    assert result.description == ""
    assert result.noindex
    assert result.links == []


def test_bounded_extraction():
    assert extract_html("<p>" + "A" * 70_000 + "</p><p>Gü<span>n</span>dem</p>", SEED).text.endswith(" Gündem")
    assert len(extract_html("<p>" + "kelime " * 40_000 + "</p>", SEED).text) <= 200_000
    with pytest.raises(HtmlTooLarge):
        extract_html("a" * (2 * 1024 * 1024 + 1), SEED)


def test_description_falls_back_to_visible_text_and_title_to_hostname():
    result = extract_html("<p>" + "metin " * 100 + "</p>", SEED)
    assert result.title == "www.tsk.gov.tr"
    assert result.description == result.text[:300]
