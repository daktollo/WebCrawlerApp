# 05 — Arama ve API

## Kelime ayırma (`indexing/text_normalizer.py`)

`normalize_search_text`: NFKD → küçük harf → birleşik işaretleri (aksanları) sil → `ı→i` →
harf/rakam dışı dizileri tek boşluk yap. `tokenize`: boşluktan böl, 80 karakterden uzunları
at. Örnek: `"İSTANBUL IŞIK Türkçe ŞĞÜÖÇ"` → `istanbul isik turkce sguoc`.

Her sayfa için üç alan indekslenir: `content` (görünür metin), `title`, `url`
(ana makine adı + çözülmüş yol).

## Arama (`views/search_view.py`)

- Sorgu ≤ 200 karakter, kelimelere ayrılır (tekrarlar atılır).
- Sorgudaki **her** kelimeyi herhangi bir alanda içeren sayfalar seçilir, PageRank'e göre
  (eşitlikte URL) sıralanır; `limit` 1–100, varsayılan 30.
- `matchSources`: kelimelerin geçtiği alanlar (`title`, `content`, `url` sırasıyla).
- `description`: gövdede ilk kelimenin geçtiği yerin 75 karakter öncesinden başlayan
  270 karakterlik kesit; gövde yoksa sayfa açıklaması.
- Ölçüm: 17 sayfalık gerçek indekste iki kelimelik sorgu 7 ms.

## Uç noktalar

Bütün cevaplar `Cache-Control: no-store`. Hata biçimi: `{"ok": false, "error": "<Türkçe mesaj>"}`.

| Yöntem | Yol | Cevap |
|---|---|---|
| GET | `/api/crawl/status` | `seed, status, indexedPages, queuedPages, visitedPages, failedPages, skippedPages, indexedWords, linkCount, maxPages, maxDepth, delayMs, currentUrl, lastError, updatedAt, startedAt, lastIndexedAt, revision, recentPages[6], recentErrors[5]` |
| GET | `/api/crawl/search?q=&limit=` | `startedAt, query, results[{url,title,description,rank,indexedAt,matchSources}], total, tookMs, indexedPages, revision, status` |
| GET | `/api/crawl/words?q=&offset=&limit=&seed=` | Gövde kelimeleri, filtre "içerir" (katlanmış), alfabetik, `limit` ≤ 100; her kelime için `pageCount` ve en yüksek PageRank'li 5 sayfa |
| GET | `/api/crawl/explorer?seed=` | `graph` (indekslenmiş sayfalar arası bağlantılar), `pages` (başlık, açıklama, tarih, PageRank), `stats{pages, links, discoveredLinks, words, queued}` |
| POST | `/api/crawl/control` | Gövde `{"action", "seed"?, "maxPages"?, "confirmReset"?}` → güncel durum |

`seed` parametresi etkin taramayla uyuşmazsa 409 "Tarama kaynağı değişti...". Bilinmeyen
yol 404 "Bu tarama işlemi bulunamadı.".

### `/control` doğrulaması

| Koşul | Kod |
|---|---|
| `Content-Type` JSON değil | 415 |
| Gövde > 2048 bayt | 413 |
| Bozuk JSON, bilinmeyen işlem, `reset` onaysız, izinli olmayan seed, `maxPages` 1..2⁵³−1 arası tam sayı değil | 400 |
| Tarama yokken ya da farklı seed'le `pause/resume/retry/set_limit` | 409 |

Orijinaldeki iki alan kaldırıldı: `canManage` / `isAuthenticated` / `loginUrl` (giriş yok)
ve `runtime: "request-driven"` (tarama artık ziyaretçiye bağlı değil).
