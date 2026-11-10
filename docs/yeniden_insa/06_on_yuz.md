# 06 — Ön Yüz

Kod: `frontend/` — Vite 8 + React 19 + TypeScript 5.9, Tailwind 4 (yalnızca temel
sıfırlama için, PostCSS eklentisiyle). Sürümler orijinalin lockfile'ıyla aynı.

## Taşıma

Orijinal dosyalar klasör adları korunarak `frontend/src/` altına kopyalandı:

| Dosya | Görevi |
|---|---|
| `app/page.tsx` | Ana görünüm, gezinme, Örnek / Colab laboratuvarı |
| `components/live-crawler.tsx` | Canlı arama, tarama durumu, tarama yönetimi |
| `components/live-explorer.tsx` | Canlı bağlantı haritası, kelime indeksi, veri kümesi |
| `components/network-graph.tsx` | SVG bağlantı grafiği |
| `lib/search-engine.ts` | Örnek veri, tarayıcıda PageRank, arama ve JSON doğrulama |
| `lib/crawler-types.ts` | API sözleşmesi ve seed sabitleri |
| `app/globals.css`, `crawler.css`, `explorer.css` | Orijinal stiller |

Yeni dosyalar: `index.html` (başlık ve açıklama orijinal `layout.tsx`'ten), `src/main.tsx`,
`vite.config.ts` (`@/` → `src/`, geliştirmede `/api` → `127.0.0.1:1320`), `tsconfig.json`.

## Orijinalden farklar

- `"use client"` satırları ve Next.js `Metadata` kaldırıldı.
- Yönetici girişi olmadığı için "yalnızca site yöneticisi değiştirebilir" dalı,
  "Yönetici" etiketi ve ilgili CSS kuralları (`lc-owner-*`) silindi; tarama yönetimi
  paneli durum yüklenince her zaman görünür.
- **Mobil sonuç kartı düzeltmesi (orijinalde de vardı):** 540 pikselin altında canlı arama
  sonuç kartı `flex-wrap` ile iki satıra bölünüyor ve PageRank kutusu `width:100%` alıyordu;
  içerik sütunu `flex:1` (başlangıç genişliği 0) olduğundan ikisi aynı satıra yerleşiyor,
  içerik sıfır genişliğe sıkışıp başlık harf harf alt alta diziliyordu. `crawler.css`'te bu
  kırılımda `.lc-result-main{flex-basis:100%}` eklendi. 390 pikselde ölçüm: içerik sütunu
  0 → 326 piksel, başlık yüksekliği tek satır (26 piksel). Diğer ekranlarda (Örnek / Colab,
  harita, kelime indeksi, veri kümesi) sıkışan metin yok; tablolar kendi kutularında kayıyor.
- Tarama akışı notu: "Tarama sunucu çalıştığı sürece arka planda ilerler. Sunucu kapanınca
  kuyruk saklanır; yeniden açıldığında devam eder."

Ekranlar: Canlı arama (⌘K / Ctrl+K), Örnek / Colab araması, Bağlantı haritası,
Kelime indeksi, Veri kümesi, "PageRank nasıl çalışır?". Tarayıcıda (Chromium) beş ekran
da açıldı; konsolda hata ve uyarı yok (2026-11-10).

## Derleme

- `npm run build` → `tsc --noEmit` + `vite build` → `frontend/dist` (JS 297 kB, gzip 89 kB).
- Yayında `frontend/docker/Dockerfile` imajı derler: `node:22-alpine` ile `npm ci` +
  `npm run build`, ardından `nginx:1.28-alpine` `dist/`'i **1319**'da sunar ve `/api/*`'yi
  `backend:1320`'ye iletir (`frontend/docker/nginx.conf`). `assets/` uzun süre önbelleğe
  alınır (adlarında içerik özeti var), `index.html` her seferinde doğrulanır.
- Backend statik dosya sunmaz.
