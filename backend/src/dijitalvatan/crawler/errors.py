"""Outcomes of crawling one URL that are not a successfully indexed page."""

NOT_PUBLIC = "Adres genel web üzerinde taranabilir bir hedef değil; istek gönderilmeden atlandı."
REDIRECT_NOT_PUBLIC = "Yönlendirme hedefi genel web üzerinde taranabilir bir adres değil; hedefe istek gönderilmeden atlandı."
ROBOTS_DENIED = "robots.txt bu adresin taranmasına izin vermiyor."
NOT_HTML = "Bu kaynak bir HTML sayfası değil."
TOO_LARGE = "Kaynak sayfa 2 MB sınırını aşıyor."
NO_TEXT = "İndekslenecek görünür metin bulunamadı."
NOINDEX = "Sayfa noindex işareti taşıyor; arama indeksine alınmadı."
TIMEOUT = "Kaynak adrese bağlantı 8 saniyede tamamlanamadı. Önceki indeks korunuyor."
CONNECT_FAILED = "Kaynak adrese bağlanılamadı. Alan adı/DNS, bağlantı veya TLS hatası olabilir. Önceki indeks korunuyor."
NO_LOCATION = "Site geçerli bir yönlendirme adresi vermedi."
TOO_MANY_REDIRECTS = "Kaynak sitede çok fazla yönlendirme var."
UNEXPECTED = "Tarama sırasında beklenmeyen bir hata oluştu. Önceki indeks korunuyor; yeniden deneyebilirsiniz."


class SkipPage(Exception):
    """This URL is not indexed; the crawl continues."""

    def __init__(self, message: str, robots_denied: bool = False):
        super().__init__(message)
        self.message = message
        self.robots_denied = robots_denied


class CrawlFailure(Exception):
    """A site refused or failed. Other sites keep being crawled; a failing seed site stops the crawl."""

    def __init__(self, message: str, phase: str = "error", origin: str | None = None):
        super().__init__(message)
        self.message = message
        self.phase = phase
        self.origin = origin


class OriginBlocked(CrawlFailure):
    """The site was already blocked earlier in this crawl; no request is sent."""


class CrawlChanged(Exception):
    """The crawl was paused, reset or switched while a page was in flight; its result is dropped."""
