# 05 — Ön Yüz

Vite + React + TypeScript. Yönlendirme kütüphanesi yok; orijinaldeki gibi sol menüden
seçilen görünüm durum olarak tutulur. Geliştirmede Vite `/api` isteklerini
`localhost:8000`'e yönlendirir (proxy).

## Klasör yapısı

```
frontend/src/
├── main.tsx
├── App.tsx                     # app-shell: sidebar + active view
├── api/crawlClient.ts          # fetch wrapper: {ok:false,error} → Error(error)
├── lab/                        # browser-only Örnek/Colab mode
│   ├── sampleDataset.ts        # "Search Engine Places" data and fixed map layout
│   ├── datasetValidator.ts     # all upload rules and Turkish messages
│   ├── tokenizer.ts            # same rule as backend tokenizer.py
│   ├── pagerank.ts             # computeRanks(graph, d, iterations)
│   └── labSearch.ts
├── views/
│   ├── LiveSearchView.tsx      # Canlı arama + tarama paneli + ayarlar
│   ├── LabSearchView.tsx       # Örnek / Colab araması + PageRank ayarları
│   ├── LinkMapView.tsx         # Bağlantı haritası
│   ├── WordIndexView.tsx       # Kelime indeksi
│   ├── DatasetView.tsx         # Veri kümesi: yükle / indir / örneğe dön
│   └── HowItWorksView.tsx      # PageRank nasıl çalışır?
├── components/                 # Sidebar, ResultCard, NetworkGraph, StatusBanner, Pager ...
└── styles/
```

## Davranışlar (orijinalden)

- **Canlı arama:** durum her 5 sn'de bir sorgulanır (12 sn zaman aşımı); `revision`
  değiştiğinde açık arama yenilenir. Arama 15 sn zaman aşımı; yeni cevap gelmezse eski
  sonuç, "“x” için yeni yanıt alınamadı" notuyla gösterilir. ⌘K / Ctrl+K arama
  kutusuna odaklar.
- **Tarama paneli:** başlangıç adresi alanı, sayfa sınırı (1–500), "Taramayı başlat /
  Taramaya devam et / Yeni sınırla devam et / Yeniden tara / Duraklat" butonları,
  sayaçlar, işlenen/sınır ilerlemesi, son eklenen sayfalar, son hatalar.
- **Örnek / Colab:** tamamen tarayıcıda; JSON ≤ 8 MB okunur, doğrulanır, PageRank
  seçilen d ve iterasyonla yeniden hesaplanır; "JSON indir" mevcut veriyi indirir.
  Sonuç sıralaması: "Önce en yüksek puan" / "Alfabetik"; isteğe bağlı "Başlık ve
  adresleri de ara".
- **Harita:** SVG, daire yarıçapı PageRank'e orantılı, yönlü oklar, karşılıklı
  bağlantılar ayrı çizilir, düğüme tıklayınca seçim + gelen/giden bağlantı bilgisi,
  yakınlaştırma 0.8–1.6 (0.2 adım). Örnek veride orijinalin sabit koordinatları,
  canlı veride `d3-force` ile bir kez hesaplanan yerleşim.
- **Kelime indeksi:** önek filtresi, sayfalama ("1–50 / 13.027"), her kelimenin geçtiği
  sayfalar.
- Sayılar `tr-TR` biçiminde, tarihler `gün ay saat:dakika`.
- `prefers-reduced-motion` desteklenir.

## Görünüm

Orijinalin derlenmiş CSS'i elimizde (Tailwind v4 + özel sınıflar). İki seçenek var;
karar [06](06_asamalar_ve_acik_sorular.md)'de.
