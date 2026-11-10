# 08 — Kararlar ve Sonraki Adımlar

## Verilen kararlar

| Tarih | Karar |
|---|---|
| 2026-11-09 | Yığın: Python FastAPI arka uç + Vite/React ön yüz; tam kapsam (canlı tarama dahil) |
| 2026-11-09 | Görünüm: orijinal tasarım korunur |
| 2026-11-09 | Giriş yok; herkes taramayı yönetebilir |
| 2026-11-09 | Tarama sunucu açık olduğu sürece arka planda ilerler |
| 2026-11-09 | Yeni seed eski tarama verisini siler |
| 2026-11-09 | Zip'teki kod referanstır; aynı işlev daha iyi bir tasarımla yeniden yazılır |
| 2026-11-10 | Veritabanı Supabase değil, yerel SQLite |
| 2026-11-10 | Seed listesi şimdilik sabit (`bogazici.edu.tr`, `www.tsk.gov.tr`, `www.tsk.tr`) |
| 2026-11-10 | Migration'ları geliştirici (Claude) uygular |
| 2026-11-10 | Yayın adresi `dijitalvatan.searchengineplaces.com.tr`, Raspberry Pi `192.168.1.118` |
| 2026-11-10 | Docker Compose: `backend/docker` ve `frontend/docker`; frontend (nginx) **1319**, backend **1320** |

## Bilinen sınırlar

- **Yapışık kelimeler:** Satır içi öğeler boşluksuz birleştirildiği için, menülerde arka
  arkaya duran bağlantılar tek kelime gibi indekslenebiliyor (gerçek taramada
  `arabirimlerkampus` gibi). Kural orijinalle aynı; "Gü<b>n</b>dem" gibi gerçek kelimeleri
  korumak için bu şekilde. İyileştirme seçeneği: `<a>` ve `<button>`'u da blok sayıp
  boşluk eklemek.
- **Snippet konumu:** Kesit konumu katlanmış metinde bulunup orijinal metne uygulanıyor;
  katlama metin uzunluğunu değiştirdiğinde kesit birkaç karakter kayabilir (orijinalde de
  aynı).
- **Tek sunucu:** Tarayıcı ve SQLite aynı makinede. Birden çok sunucuya ölçeklemek
  gerekirse veritabanı Postgres'e taşınmalı (storage katmanı buna göre ayrık).

## Açık konular

- **Yerel örnek site:** "Search Engine Places" örnek grafını gerçek HTML sayfaları olarak
  sunup seed listesine eklemek (derste deterministik, birkaç saniyelik tarama).
  `searchengineplaces.com.tr` yayında; doğrudan seed olarak eklemek de bir seçenek.
- **Yayın:** Site `https://dijitalvatan.searchengineplaces.com.tr` adresinden herkese açık
  olacak (Nginx Proxy Manager → `192.168.1.118:1319` → frontend konteyneri). Giriş olmadığı için şu an internetteki
  herkes taramayı başlatıp sıfırlayabilir; `POST /api/crawl/control` için yetki (ör. NPM
  erişim listesiyle bu yolu kilitlemek ya da uygulamada yönetici anahtarı) karara bağlanmalı.
