# 04 — Tarayıcı

Kod: `backend/src/dijitalvatan/crawler/`. Bütün sabitler `config.py`'de.

## Döngü (`crawler.py`)

Tarama `running` olduğu sürece her adımda:

1. İşlenen adres sayısı (`done + skipped + failed`) `max_pages`'e ulaştıysa → `limit_reached`.
2. Kuyruktan sıradaki uygun URL alınır. Kuyruk boşsa → `completed`. URL var ama hepsinin
   sitesi bekleme süresindeyse en erken sürenin dolması beklenir (en fazla 5 sn).
3. Sayfa getirilir, işlenir ve sonuç tek bir yazma işleminde kaydedilir: sayfa, kelime
   kayıtları, bağlantılar, kuyruğa eklenen yeni URL'ler, kuyruk durumu.
4. Her 8 indekslenen sayfada bir PageRank yeniden hesaplanır; tarama durunca da bir kez.

Tarama `running` değilse döngü 5 sn'de bir durumu yoklar; kontrol işlemleri döngüyü
anında uyandırır. Sunucu yeniden açılınca tarama `running` durumundaysa kaldığı yerden sürer.

## Bir URL'nin getirilmesi (`page_fetcher.py`)

En fazla 4 yönlendirme; her adımda:

1. URL normalleştirilir (`url_rules.py`): yalnızca http/https; kullanıcı adı/şifre ve
   standart dışı port yok; IP adresi, `localhost`, `.local`, `.internal` gibi adlar yok;
   `#` atılır; takip parametreleri (`utm_*`, `fbclid` ...) silinir, parametreler sıralanır;
   `www.bogazici.edu.tr` → `bogazici.edu.tr` (https). Dosya uzantıları (pdf, jpg, zip, js ...)
   tarama dışı.
2. Sitenin `robots.txt` kuralı (24 saat önbellekli) adrese izin vermiyorsa → atlanır.
3. İstek aralığı: tüm siteler için en az 1,5 sn, aynı site için `max(1,5 sn, Crawl-delay)`.
4. Ana makine adı çözülür; özel, loopback veya link-local IP çıkarsa istek gönderilmez.
5. GET (8 sn toplam süre, `User-Agent: DijitalVatanBot/1.0`); 429/503 + `Retry-After` o
   siteyi bekletir; gövde 2 MB'ı aşarsa sayfa atlanır.

`robots.txt` cevabı: 404/410 → her şeye izin; 401/403 → site `blocked`; 429/5xx → site
`error`; HTML dönerse (doğrulama sayfası) → site `blocked`.

## Sayfanın işlenmesi (`html_extractor.py`)

- Görünür metin: `head`, `script`, `style`, `noscript`, `template`, `svg`, `form`, `iframe`,
  `canvas`, `object`, `hidden`, `aria-hidden="true"` ve `display:none` olan öğeler atılır.
  Blok öğeler arasına boşluk konur, satır içi öğeler birleştirilir ("Gü<b>n</b>dem" → "Gündem").
  En fazla 200.000 karakter.
- Başlık (≤ 300), açıklama (`meta description`, yoksa metnin ilk 300 karakteri),
  bağlantılar (`rel="nofollow"` hariç, en fazla 500; kuyruğa ilk 300'ü).
- `noindex` → sayfa indekse girmez ama bağlantıları izlenir; `nofollow` → bağlantılar
  izlenmez. CAPTCHA/güvenlik sayfası → site `blocked`.

## Hata kuralları

| Durum | URL | Tarama |
|---|---|---|
| HTTP 2xx dışı (401/403/429/5xx hariç), HTML değil, metin yok, robots yasağı, 2 MB üstü | `skipped` | sürer (seed robots yasağıysa `blocked`) |
| 401/403, CAPTCHA, robots erişim engeli | başka sitedeyse `skipped` | sürer; site engellenir |
| 429, 5xx, zaman aşımı, DNS/TLS hatası | başka sitedeyse `failed` | sürer; site engellenir |
| Aynı hatalar seed sitesinde | `failed` | `blocked` / `error` ile durur |
| Beklenmeyen hata | `failed` | `error` ile durur, tam traceback loglanır |

## Kontrol işlemleri (`crawl_control.py`)

| İşlem | Etki |
|---|---|
| `start` (yeni seed ya da ilk tarama) | Eski tarama verisi silinir, yeni nesil başlar, seed kuyruğa girer |
| `start` (aynı seed) | Tüm URL'ler yeniden kuyruğa alınır, site engelleri temizlenir; eski sayfalar yenilenene kadar aranabilir |
| `resume` | `running`, yeni sınırla |
| `retry` | Site engelleri temizlenir, `failed` URL'ler yeniden kuyruğa girer |
| `pause` | `paused`; o an indirilen sayfanın sonucu atılır |
| `set_limit` | Sınır değişir; çalışırken yeni sınır aşılmışsa `limit_reached` |
| `reset` (`confirmReset: true`) | Yeni seed gibi: her şey silinir, seed'den yeniden başlar |

`start` ve `reset` dışındaki işlemler mevcut bir tarama ve aynı seed ister (409).

## PageRank (`ranking/pagerank.py`)

Kurs defterindeki `computeRanks`: başlangıç `1/N`, 10 iterasyon,
`rank(p) = (1-d)/N + Σ d·rank(q)/outdegree(q)`, d = 0.8. Graf yalnızca indekslenmiş
sayfalardan ve aralarındaki bağlantılardan oluşur. Çıktı, orijinal TypeScript fonksiyonunun
örnek veri üzerindeki çıktısıyla 1e-12 hassasiyetle aynı (test).
