# Dijital Vatan — Arama Motoru (yeniden inşa)

Öğrencilere bir web tarayıcısının (crawler) nasıl çalıştığını göstermek için kurulan
DSAI 301 "Soru 1" arama motoru. Orijinali ChatGPT Sites üzerinde (Cloudflare Workers + D1)
yayınlanmıştı; kaynak kodu `soruce/` altında yalnızca referans olarak duruyor.
Bu proje aynı işlevi kendi sunucumuzda, daha sade bir mimariyle çalıştırır.

**Durum (2026-11-10):** Çalışıyor. Arka uç, tarayıcı, SQLite veritabanı ve ön yüz tamam;
64 test geçiyor; `bogazici.edu.tr` üzerinde 20 sayfalık gerçek tarama yapıldı
(ölçümler [07](07_calistirma_ve_test.md)'de).

**Yığın:** Python 3.14 + FastAPI (API ve arka plan tarayıcısı, port 1320) · SQLite (tek dosya) ·
Vite + React + TypeScript (orijinal bileşenler taşındı; nginx ile port 1319) · Docker Compose,
Raspberry Pi üzerinde yayın.

## Belgeler

| Dosya | İçerik |
|---|---|
| [01_orijinal_proje.md](01_orijinal_proje.md) | Orijinal sitenin mimarisi ve davranışı, neyi koruduk, neyi değiştirdik |
| [02_mimari.md](02_mimari.md) | Katmanlar, klasör yapısı, süreç modeli |
| [03_veri_modeli.md](03_veri_modeli.md) | SQLite şeması ve migration düzeni |
| [04_tarayici.md](04_tarayici.md) | Tarama döngüsü, kuyruk, robots, istek aralığı, hata kuralları, kontrol işlemleri, PageRank |
| [05_arama_ve_api.md](05_arama_ve_api.md) | Kelime ayırma, arama, kelime indeksi, harita ve HTTP uç noktaları |
| [06_on_yuz.md](06_on_yuz.md) | Ön yüzün taşınması, ekranlar, orijinalden farklar |
| [07_calistirma_ve_test.md](07_calistirma_ve_test.md) | Yerelde çalıştırma, yayın (Docker, Pi), testler ve ölçümler |
| [08_kararlar_ve_sonraki_adimlar.md](08_kararlar_ve_sonraki_adimlar.md) | Verilen kararlar, bilinen sınırlar, açık konular |
