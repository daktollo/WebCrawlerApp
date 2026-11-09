# 03 — Tarayıcı, İndeks, PageRank, Arama

## Tarayıcı (`crawler/`)

FastAPI sürecinin içinde tek bir `asyncio` görevi olarak çalışır. Sunucu açıldığında
etkin tarama `running` durumundaysa kaldığı yerden devam eder.

Döngü (her adım tek sayfa):

1. Kuyruktan `depth, id` sırasıyla ilk `queued` sayfayı al. Kuyruk boşsa →
   `completed`.
2. İşlenen sayfa sayısı `max_pages`'e ulaştıysa → `limit_reached`.
3. `robots.txt` (host başına bir kez indirilir, bellekte tutulur) izin vermiyorsa →
   sayfa `skipped`.
4. İndir (`httpx`, zaman aşımı 15 sn, yönlendirmeleri izle, gövde ≤ 5 MB). HTTP hatası
   veya HTML olmayan içerik → `failed` / `skipped`, hata metni `pages.error`'a
   ("Sayfa alınamadı (HTTP 404).").
5. Ayrıştır: `<title>`, görünür metin (`script`, `style`, `noscript` atılır),
   `<a href>` bağlantıları.
6. İndeksle (aşağıda), bağlantıları kuyruğa ekle (`depth + 1 ≤ max_depth` ise), `links`
   satırlarını yaz, `revision`'ı artır, `last_indexed_at`'i güncelle.
7. `delay_ms` kadar bekle (varsayılan 1500 ms).

URL normalizasyonu (`frontier.py`): yalnızca http/https; parça (`#...`) atılır; host
küçük harfe çevrilir; varsayılan port atılır; kullanıcı adı/şifre içeren adresler
reddedilir. Yönlendirme sonrası son URL kaydedilir (ör. `www.bogazici.edu.tr` →
`bogazici.edu.tr`).

Kapsam: orijinaldeki gibi başka sitelere giden bağlantılar da kuyruğa girer; sınırı
`max_pages` ve `max_depth` koyar.

Durum geçişleri:

| Olay | Yeni durum |
|---|---|
| `start` (yeni seed) | eski tarama pasif, yeni tarama `running` |
| `start` (aynı seed, `paused`/`limit_reached`) | `running` (sınır yükseltildiyse devam) |
| `pause` | `paused` — mevcut sayfa bitince durur |
| `set_limit` | yalnızca `max_pages` güncellenir |
| kuyruk boş | `completed` |
| sınır doldu | `limit_reached` |
| ilk sayfa robots/403 ile engellendi | `blocked` |
| ilk sayfaya ağ hatasıyla ulaşılamadı | `error` |

İlk sayfa dışındaki hatalar taramayı durdurmaz; sayfa `failed` olur ve
`recentErrors`'da görünür.

## Kelime ayırma (`indexing/tokenizer.py`)

Orijinalle birebir aynı kural, hem arka uçta hem ön yüzde:

```python
def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower().replace("i̇", "i")
    return WORD_PATTERN.findall(unicodedata.normalize("NFC", text))  # [^\W_]+
```

`str.lower()` "İ" harfini `"i̇"` yapar; düzeltme bunu `i`'ye çevirir — böylece
"İstanbul" ve "istanbul" aynı kelime olur.

## İndeks (`indexing/indexer.py`)

Her indekslenen sayfa için içerik, başlık ve URL ayrı ayrı kelimelere ayrılır;
`postings` tablosuna `(word, page, field)` olarak yazılır. Tek sayfanın tüm yazımları
tek transaction'da yapılır.

## PageRank (`ranking/pagerank.py`)

Kurs ve Colab defterindeki `computeRanks` ile aynı algoritma (d = 0.8, 10 iterasyon),
böylece Örnek/Colab modu ile canlı indeks aynı puanları üretir:

```
rank_0(p) = 1 / N
rank_{k+1}(p) = (1 - d) / N + Σ_{q → p} d · rank_k(q) / outdegree(q)
```

Sarkan düğüm (çıkış bağlantısı olmayan sayfa) düzeltmesi yapılmaz; bu kursun tanımı.
Sonuç `crawl.revision` anahtarıyla bellekte tutulur: arama, revizyon değişmediyse
yeniden hesaplamaz. 500 düğüm / 40.000 bağlantıda bir hesaplamanın süresi Faz 1'de
ölçülecek; tahmin değil, ölçüm raporlanacak.

## Arama (`search/search_service.py`)

1. Sorgu ≤ 200 karakter, kelimelere ayrılır.
2. Her kelime için eşleşen sayfa kümesi (`postings`, herhangi bir alan). Sayfa, tüm
   kelimeleri içermeli (kesişim).
3. Her sonuç için `matchSources`: kelimelerin hangi alanlarda bulunduğu.
4. PageRank'e göre azalan sıralama; ilk `limit` (≤ 30) kayıt + `total`.
5. `tookMs` ölçülüp cevaba eklenir.
