# 01 — Orijinal Sitenin Analizi

Kaynak: sitenin HTML'i, derlenmiş JS/CSS paketleri (`page-*.js`, `index-*.js`,
`index-*.css`, `page-*.css`) ve canlı API'ye yapılan salt-okunur GET istekleri
(2026-11-09).

## Teknik yapı

- Ön yüz: Next.js uyumlu "vinext" (Vite + React Server Components), Tailwind v4 +
  özel sınıflar (`app-shell`, `sidebar`, `lc-*`, `iz-network` ...), ikonlar `lucide`.
- Arka uç: `/api/crawl/*` uç noktaları; çalışma modu `"runtime": "request-driven"` —
  tarama yalnızca site açıkken ilerliyor ("Tüm ziyaretçiler ayrıldığında kuyruk saklanır;
  sonraki açılışta devam eder").
- Yönetim (taramayı başlatma/durdurma) yalnızca ChatGPT ile giriş yapan sahibe açık
  (`canManage`, `isAuthenticated`).

## Ekranlar (sol menü — "ÇALIŞMA ALANI")

| Menü | İçerik |
|---|---|
| Canlı arama (⌘K) | Kalıcı web indeksinde arama, tarama durumu bandı, sayaçlar, tarama akışı, son eklenen sayfalar, tarama ayarları |
| Örnek / Colab araması | Tarayıcı içinde çalışan arama: örnek veri veya Colab'dan yüklenen JSON |
| Bağlantı haritası | SVG graf; daire boyutu = PageRank, oklar = bağlantı yönü; yakınlaştırma 0.8–1.6 |
| Kelime indeksi | Kelime listesi, filtre, sayfalama; her kelimenin geçtiği sayfalar |
| Veri kümesi | Aktif veri kaynağı, JSON yükle/indir, örnek veriye dön |

Ek bölümler: "PageRank nasıl çalışır?" açıklaması, "Sıralamayı keşfedin" (sönüm
katsayısı ve iterasyon ayarı), "Colab defteri" bağlantısı
(`https://colab.research.google.com/drive/1Pl_Vxa5JpJfEfWWs0gBGWVkeCTI1F6bm`).
Veri kaynağı anahtarı: **Canlı indeks** ↔ **Örnek / Colab**.

## Canlı API — gözlenen cevaplar

`GET /api/crawl/status`
```json
{"ok": true, "seed": "https://bogazici.edu.tr/", "status": "limit_reached",
 "indexedPages": 335, "queuedPages": 1500, "visitedPages": 500, "failedPages": 35,
 "skippedPages": 33, "indexedWords": 13027, "linkCount": 39410,
 "maxPages": 500, "maxDepth": 3, "delayMs": 1500, "currentUrl": null, "lastError": null,
 "updatedAt": "...", "startedAt": "...", "lastIndexedAt": "...", "revision": 597,
 "canManage": false, "isAuthenticated": false, "runtime": "request-driven",
 "recentPages": [{"url": "...", "title": "...", "indexedAt": "..."}],
 "recentErrors": [{"url": "...", "error": "Sayfa alınamadı (HTTP 404)."}]}
```

`GET /api/crawl/search?q=...&limit=30`
```json
{"ok": true, "query": "boğaziçi",
 "results": [{"url": "...", "title": "...", "description": "ilk ~300 karakter…",
              "rank": 0.00937, "indexedAt": "...", "matchSources": ["content", "url"]}],
 "total": 335, "tookMs": 233, "indexedPages": 335, "revision": 597,
 "status": "limit_reached"}
```

`GET /api/crawl/words?q=&offset=0&limit=3&seed=...`
```json
{"ok": true, "seed": "...", "revision": 597, "query": "", "total": 13027,
 "offset": 0, "limit": 3,
 "entries": [{"word": "0", "pageCount": 302, "pages": [{"url": "...", "title": "..."}]}]}
```

`GET /api/crawl/explorer?seed=...` — denemede veritabanı hatası döndü
(`{"ok": false, "error": "Tarama veritabanına şu anda ulaşılamıyor..."}`); cevap biçimi
gözlenemedi, bizim tasarımımız [04_api.md](04_api.md)'de.

`POST /api/crawl/control` — gövde:
`{"action": "start" | "pause" | "set_limit", "maxPages": 1..500, "seed": "..."}`
(`pause` yalnızca `action` taşır; `seed` yalnızca `start` ve `set_limit`'te).

Hata biçimi her uçta aynı: `{"ok": false, "error": "<Türkçe mesaj>"}`.

## Tarama durumları

| status | Başlık | Ton |
|---|---|---|
| idle | Başlamaya hazır | neutral |
| running | Tarama sürüyor | active |
| paused | Tarama duraklatıldı | neutral |
| completed | Tarama tamamlandı | success |
| blocked | Kaynak erişimi engellendi | warning |
| error | Kaynağa ulaşılamadı | warning |
| limit_reached | Sayfa sınırına ulaşıldı | success |

Kapsam kuralları (sayfadaki metinden): başlangıç `https://bogazici.edu.tr/`, bağlantılarla
keşfedilen siteler de taranır (alt alan adları ve başka siteler aynı indekse katılabilir),
her sitenin `robots.txt` kuralına uyulur, en fazla derinlik 3, istekler arası 1500 ms.

## Arama kuralları

- Sorgudaki **tüm** kelimeleri içeren sayfalar döner (AND).
- Eşleşme kaynağı: içerik, başlık, adres (`matchSources`: `content`, `title`, `url`).
- Sıralama PageRank'e göre; sorgu en fazla 200 karakter.

## Örnek / Colab modu (tamamen tarayıcıda)

- Örnek veri: "Search Engine Places" — 10 sayfalık seyahat grafiği (seyahat rehberi,
  Ankara, Konya, İstanbul, Galata Kulesi, Kız Kulesi, Mevlana, Şeyma'nın ve Oktay'ın
  önerileri), 3 kelimelik indeks (`Our`, `learn`, `in`), sabit harita koordinatları.
- Colab çıktısı: `{"index": ..., "graph": ..., "ranks": ...}` (+ isteğe bağlı `pages`
  ve `name`), dosya adı `dijital_vatan_verileri.json`.
- PageRank: kursun `computeRanks` fonksiyonuyla aynı (d = 0.8, 10 iterasyon, sarkan
  düğüm düzeltmesi yok). Ayarlanabilir: d ∈ [0, 1], iterasyon ∈ [0, 1000].
- Doğrulama sınırları: dosya ≤ 8 MB, ≤ 500 sayfa, ≤ 50.000 bağlantı, ≤ 100.000 kelime,
  kelime ≤ 4096 karakter, kelime başına ≤ 50.000 URL, başlık ≤ 300, açıklama ≤ 2000
  karakter; tüm URL'ler http/https; her bağlantı hedefi grafikte bir düğüm olmalı;
  indeksteki her URL grafikte bulunmalı. Her kural için Türkçe hata metni paketten
  aynen alındı.
- Kelime ayırma: NFC normalizasyonu, küçük harf, `i̇` → `i` düzeltmesi, harf/rakam
  dizileri (`[\p{L}\p{N}]+`).
