# Dijital Vatan — Yeniden İnşa Planı

ChatGPT üzerinde yayınlanan "Dijital Vatan — Arama Motoru" sitesinin
(`https://iz-arama-motoru.radiantthistle2.chatgpt.site/`) bu klasörde, düzenlenebilir
kaynak koduyla yeniden yazılması.

Orijinal sitenin kaynak kodu indirilemiyor: ön yüz yalnızca derlenmiş (minified) paket
olarak sunuluyor, source map yok; arka uç (tarayıcı, indeks, veritabanı) hiç dışarı
açık değil. Bu nedenle proje sıfırdan, orijinalin davranışı referans alınarak yazılacak.

**Seçilen yön:** Python (FastAPI) arka uç + Vite/React ön yüz + Supabase (Postgres), tam kapsam
(canlı tarama dahil).

**Durum:** Uygulama başladı (Faz 0–4 yazılıyor). Veritabanı: Supabase.

## Belgeler

| Dosya | İçerik |
|---|---|
| [01_kaynak_analizi.md](01_kaynak_analizi.md) | Orijinal siteden çıkarılanlar: ekranlar, API cevap biçimleri, durumlar, sınırlar, örnek veri |
| [02_mimari_ve_veri_modeli.md](02_mimari_ve_veri_modeli.md) | Klasör yapısı, katmanlar, Supabase (Postgres) şeması ve bağlantısı |
| [03_tarayici_ve_indeks.md](03_tarayici_ve_indeks.md) | Tarayıcı (crawler), kelime ayırma, indeks, PageRank, arama |
| [04_api.md](04_api.md) | FastAPI uç noktaları ve cevap biçimleri |
| [05_on_yuz.md](05_on_yuz.md) | Ön yüz ekranları, istemci tarafı Örnek/Colab modu, harita |
| [06_asamalar_ve_acik_sorular.md](06_asamalar_ve_acik_sorular.md) | Uygulama aşamaları, ölçüm/test planı, verilen kararlar |
