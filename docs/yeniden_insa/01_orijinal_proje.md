# 01 — Orijinal Proje

Kaynak: `soruce/iz-arama-motoru-kaynak-kodlari.zip` içindeki iki sürüm —
`yayindaki-surum-9` (yayındaki) ve `son-gelistirme-surumu` (en son). Referans olarak
son geliştirme sürümü alındı.

## Mimari

- **Çalışma ortamı:** Cloudflare Workers üzerinde Vinext (Next.js uyumlu, Vite tabanlı).
- **Veritabanı:** Cloudflare D1 (SQLite). Arama, FTS5 tam metin tablosuyla
  (`crawl_search`, `unicode61 remove_diacritics`) yapılıyor; kelime listesi `fts5vocab`'den.
- **Tarama tetikleme ("request-driven"):** Ayrı bir tarayıcı süreci yok. Tarama `running`
  durumundayken gelen her API isteği (ön yüz durumu 5 sn'de bir soruyor) `waitUntil` ile
  kısa bir iş başlatıyor: en fazla 20 sn'de en fazla 8 sayfa. Aynı anda tek iş çalışsın diye
  veritabanında 45 sn'lik bir kiralama (lease) ve her yazımda bir "fence" koşulu var.
  Siteyi kimse açmazsa tarama duruyor; Cloudflare sürümüne dakikalık Cron eklenmiş.
- **Yetki:** Taramayı yalnızca site sahibi yönetebiliyor (ChatGPT Sites oturumu ya da
  Cloudflare Access). Ziyaretçiler sadece arıyor.

## Davranış (korunan)

- Varsayılan seed `https://bogazici.edu.tr/` (`www.bogazici.edu.tr` buna yönleniyor).
  İzinli seed'ler sabit: `bogazici.edu.tr`, `www.tsk.gov.tr`, `www.tsk.tr`.
- Genişlik öncelikli tarama, en fazla derinlik 3; kuyruk sayfa sınırının 4 katına kadar.
  Varsayılan sınır 200, üst sınır yok (JavaScript'in güvenli tam sayı aralığı).
- Alan adı dışına çıkılabiliyor (alt alan adları, başka siteler); her site (origin) için
  ayrı `robots.txt` ve ayrı istek aralığı (en az 1,5 sn, `Crawl-delay`'e uyuluyor);
  `Retry-After` korunuyor.
- `noindex` / `nofollow` (meta ve `X-Robots-Tag`), CAPTCHA/güvenlik doğrulama sayfaları
  indekslenmiyor ve takip edilmiyor. PDF, resim, arşiv gibi dosyalar kuyruğa alınmıyor.
- Başka bir site erişimi engellerse sadece o site atlanıyor; seed sitesi engellerse tarama
  `blocked` / `error` ile duruyor.
- Kelimeler Türkçe katlanıyor: `NFKD` + küçük harf + aksan silme + `ı→i`
  ("Boğaziçi" → "bogazici").
- Arama: sorgudaki **tüm** kelimeleri içeren sayfalar (içerik, başlık veya adreste),
  PageRank'e göre sıralı. PageRank kurs defteriyle aynı: d = 0.8, 10 iterasyon, sarkan
  düğüm düzeltmesi yok, sadece indekslenmiş sayfalar arasındaki bağlantılar.
- Kontrol işlemleri: `start`, `pause`, `resume`, `retry`, `set_limit`, `reset` (açık onaylı).
- "Örnek / Colab" laboratuvarı tamamen tarayıcıda çalışıyor: "Search Engine Places"
  örnek verisi (10 sayfa, 18 bağlantı, `searchengineplaces.com.tr`; kaynak Colab defterinin
  kayıtlı çıktısı) ve Colab'den yüklenen JSON.

## Bizde değişenler

| Konu | Orijinal | Biz |
|---|---|---|
| Tarayıcıyı ilerleten | Ziyaretçi istekleri + Cron | Sunucu sürecindeki tek arka plan görevi ([04](04_tarayici.md)) |
| Eşzamanlılık güvenliği | Lease + her SQL'de fence | Tek yazar + dosya kilidi; sonuçlar "nesil" kontrolüyle yazılıyor |
| Veritabanı | D1, her tabloda `seed` sütunu | Yerel SQLite, tek etkin tarama; yeni seed eski veriyi siliyor ([03](03_veri_modeli.md)) |
| Tam metin arama | FTS5 | Kendi ters indeksimiz (`words` + `postings`); öğrenci tabloları görebiliyor |
| Yetki | Site sahibi girişi | Giriş yok; yerel/derste kullanım için herkes yönetebilir |
| Okuma tutarlılığı | Okuma sonrası "tarama değişti mi" kontrolü (409) | Her okuma tek bir SQLite okuma işleminde (anlık görüntü) |
| Çok büyük sayfa (>2 MB) | Siteyi `error` ile engelliyordu | Sadece o sayfa atlanıyor |
| İç ağ adresleri | Workers'ın genel ağ sınırı | Adres çözümlenip özel/loopback IP'ler reddediliyor |
