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
`vite.config.ts` (`@/` → `src/`, geliştirmede `/api` → `127.0.0.1:8000`), `tsconfig.json`.

## Orijinalden farklar

- `"use client"` satırları ve Next.js `Metadata` kaldırıldı.
- Yönetici girişi olmadığı için "yalnızca site yöneticisi değiştirebilir" dalı,
  "Yönetici" etiketi ve ilgili CSS kuralları (`lc-owner-*`) silindi; tarama yönetimi
  paneli durum yüklenince her zaman görünür.
- Tarama akışı notu: "Tarama sunucu çalıştığı sürece arka planda ilerler. Sunucu kapanınca
  kuyruk saklanır; yeniden açıldığında devam eder."

Ekranlar: Canlı arama (⌘K / Ctrl+K), Örnek / Colab araması, Bağlantı haritası,
Kelime indeksi, Veri kümesi, "PageRank nasıl çalışır?". Tarayıcıda (Chromium) beş ekran
da açıldı; konsolda hata ve uyarı yok (2026-11-10).

## Derleme

- `npm run build` → `tsc --noEmit` + `vite build` → `frontend/dist` (JS 297 kB, gzip 89 kB).
- Arka uç `frontend/dist`'i `/` adresinden sunar; `dist` yoksa sadece API çalışır ve logda
  uyarı yazar.
