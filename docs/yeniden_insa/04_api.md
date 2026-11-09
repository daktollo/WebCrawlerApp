# 04 — API

Tüm uçlar `/api/crawl` altında. Cevap biçimleri orijinal siteyle aynı tutulur
(alan adları camelCase), böylece ön yüz orijinaldeki gibi davranır.

## Başarı ve hata biçimi

- Başarı: `{"ok": true, ...}`, HTTP 200.
- Beklenen hatalar (geçersiz URL, sınır dışı `maxPages`, bilinmeyen `action`, etkin
  tarama yokken `set_limit`): HTTP 400 / 409 / 422,
  `{"ok": false, "error": "<Türkçe mesaj>"}`. Ön yüz bu `error` metnini aynen gösterir.
- Beklenmeyen hatalar: `logger.exception(...)` ile tam traceback loglanır, HTTP 500,
  `{"ok": false, "error": "Sunucuda beklenmeyen bir hata oluştu."}`.

## Uç noktalar

| Yöntem | Yol | Açıklama |
|---|---|---|
| GET | `/api/crawl/status` | Durum, sayaçlar, son 6 indekslenen sayfa, son 6 hata ([01](01_kaynak_analizi.md)'deki biçim) |
| POST | `/api/crawl/control` | `{"action": "start" \| "pause" \| "set_limit", "maxPages"?: 1..500, "seed"?: url}` → güncel durum |
| GET | `/api/crawl/search?q=&limit=30` | Arama sonuçları |
| GET | `/api/crawl/words?q=&offset=0&limit=50&seed=` | Kelime indeksi, öneke göre filtre, sayfalama; her kelime için ilk 5 sayfa |
| GET | `/api/crawl/explorer?seed=` | Harita verisi (aşağıda) |

`seed` parametresi olan uçlarda istenen seed etkin taramayla eşleşmiyorsa HTTP 409,
`"Tarama kaynağı değişti."` — ön yüz bunu görünce güncel kaynağa yeniden bağlanır
(orijinaldeki davranış).

## `/api/crawl/explorer` (bizim tasarımımız)

Orijinalin cevabı gözlenemedi. 500 sayfanın hepsini SVG'de çizmek okunaksız olur; bu
yüzden PageRank'i en yüksek `EXPLORER_NODES = 60` sayfa ve bunlar arasındaki
bağlantılar döner:

```json
{"ok": true, "seed": "...", "revision": 597,
 "nodes": [{"url": "...", "title": "...", "rank": 0.0093,
            "incoming": 41, "outgoing": 120}],
 "edges": [{"from": "...", "to": "...", "reciprocal": true}],
 "totalPages": 335, "totalLinks": 39410}
```

`incoming` / `outgoing` tüm grafikteki sayılardır (yalnızca gösterilen 60 düğüm
arasındakiler değil).

## Yönetim yetkisi

`canManage` alanı korunur. Varsayılan öneri: yerel uygulama olduğu için her zaman
`true`, `isAuthenticated` alanı kaldırılır (açık soru — [06](06_asamalar_ve_acik_sorular.md)).
