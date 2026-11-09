# 06 — Aşamalar ve Açık Sorular

## Aşamalar

Aşamalar sırayla yazılır; her aşamanın test çıktısı ve ölçümleri raporlanır.

| Faz | İş | Bitti sayılması için |
|---|---|---|
| 0 | İskelet: `backend/` (uv, pyproject), `frontend/` (Vite), `supabase/migrations/..._initial.sql` | Migration dosyası hazır → **sen uygularsın** |
| 1 | Çekirdek: tokenizer, PageRank, repository'ler, indexer, arama servisi, `main.py` (örnek veriyi indeksleyip arar) | `pytest` geçer; örnek veride PageRank değerleri Colab `computeRanks` ile aynı (test); 500 düğüm / 40.000 bağlantılık rastgele grafikte PageRank süresi ölçülmüş |
| 2 | Tarayıcı + API: fetcher, parser, robots, frontier, crawler döngüsü, `/status`, `/control`, `/search`, `/words`, `/explorer` | Taklit (respx) sitede uçtan uca test; gerçek bir sitede (ör. bogazici.edu.tr, 20 sayfa) deneme taraması ve ölçülen süre/sayaçlar |
| 3 | Ön yüz — canlı: app-shell, sidebar, Canlı arama, tarama paneli | Tarayıcıda canlı tarama başlatılıp aranabiliyor (ekran görüntüsü) |
| 4 | Ön yüz — laboratuvar: Örnek/Colab araması, doğrulayıcı, Veri kümesi, Bağlantı haritası, Kelime indeksi, PageRank açıklaması | Örnek veri ve gerçek Colab JSON'u ile çalışıyor; doğrulama kuralları için birim testleri (vitest) |
| 5 | Son: çalıştırma talimatı (README), dokümanları koda göre güncelleme | — |

## Kararlar

Önerilen seçenekler onaylandı; ek olarak veritabanı Supabase oldu.

| Konu | Karar |
|---|---|
| Veritabanı | Supabase (Postgres), doğrudan `psycopg` bağlantısı, ayrı `dijitalvatan` şeması — ayrıntı [02](02_mimari_ve_veri_modeli.md) |
| Görünüm | Orijinalin derlenmiş CSS'i olduğu gibi kullanılır, bileşenler aynı sınıf adlarını taşır |
| Migration | Ben `supabase/migrations/` altına yazarım, sen uygularsın (SQL Editor veya `supabase db push`) |
| Yönetim | Giriş yok, `canManage` her zaman `true` |
| Tarama zamanı | Sunucu çalıştığı sürece arka planda; kuyruk veritabanında kalır, açılışta devam eder |
| Seed değişince | Eski tarama verisi silinir (`TRUNCATE`) |
| Profil kartı, varsayılan adres, Colab bağlantısı | Orijinaldeki gibi korunur (`config` sabitleri) |
| Git | `git init` yapılmadı |

## Benim verdiğim tasarım kararları (ayrıca onaylamadığın)

- `explorer` ucu PageRank'i en yüksek 60 sayfayı döner (orijinalin cevabı
  gözlenemedi).
- HTML ayrıştırma `selectolax`, HTTP `httpx`; gövde en fazla 5 MB, zaman aşımı 15 sn.
- Kuyruktaki adres sayısı en fazla 1.500 (orijinalde gözlenen değer); dolunca yeni
  bağlantılar kuyruğa alınmaz.
- Bilinen ikili dosya uzantıları (`.pdf`, `.jpg`, `.zip` ...) kuyruğa alınmaz.
- Sayfa açıklaması: `<meta name="description">` varsa o, yoksa görünür metnin ilk
  300 karakteri.
- `robots.txt` 4xx dönerse her şeye izin, 5xx/ağ hatasında o host'a izin yok
  (RFC 9309).
- Sayaçlar ayrı sütunda değil, `COUNT` sorgusuyla.
