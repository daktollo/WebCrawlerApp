# 02 — Mimari

## Süreç modeli

Tek bir Python süreci (`uv run python -m dijitalvatan.main`, port 8000):

- **FastAPI** `/api/crawl/*` uç noktalarını sunar.
- **Arka plan tarayıcısı** aynı süreçte bir `asyncio` görevi olarak çalışır.
  `backend/data/crawler.lock` üzerinde özel bir dosya kilidi (`flock`) alır; ikinci bir
  sunucu açılırsa API'yi sunar ama taramaz (logda hata satırı yazılır).
- **Ön yüz** derlendiyse (`frontend/dist`) aynı adresten statik olarak sunulur.
  Geliştirmede Vite (port 5175) `/api` isteklerini 8000'e yönlendirir.
- **SQLite** WAL modunda (migration aracı açar, dosyada kalıcıdır): tarayıcı yazarken API
  okumaya devam eder. Her işlem kendi bağlantısını açar; bağlantının ilk ayarı
  `busy_timeout = 10 sn` (kilit varsa hata yerine bekler). Yazma işlemleri
  `BEGIN IMMEDIATE` ile yazma kilidini baştan alır. Bir bağlantı açılırken iptal gelirse
  bağlantı kapatılır; `aiosqlite` her bağlantı için daemon olmayan bir thread açtığından,
  kapanmayan bağlantı sürecin çıkmasını engeller.

## Katmanlar

Bağımlılık tek yönlü: `api → views / crawler → indexing / ranking → storage`.
SQL yalnızca `storage/` altındaki sınıflarda.

```
backend/
├── migrations/001_initial.sql        # SQLite şeması
├── requirements.txt                  # uv export (çalışma bağımlılıkları)
├── requirements-dev.txt              # test bağımlılıkları
├── data/                             # dijitalvatan.db, crawler.lock, server.log (git dışı)
├── src/dijitalvatan/
│   ├── config.py                     # tüm ayarlar (yollar, seed'ler, sınırlar, gecikmeler)
│   ├── main.py                       # sunucuyu başlatır
│   ├── migrate.py                    # migration'ları uygular
│   ├── api/
│   │   ├── app.py                    # FastAPI, yaşam döngüsü, hata biçimi, statik ön yüz
│   │   └── crawl_routes.py           # uç noktalar ve istek doğrulama
│   ├── crawler/
│   │   ├── url_rules.py              # URL normalleştirme, genel adres kuralları
│   │   ├── robots.py                 # robots.txt ayrıştırma ve eşleştirme
│   │   ├── html_extractor.py         # görünür metin, başlık, açıklama, bağlantılar
│   │   ├── page_fetcher.py           # robots, istek aralığı, yönlendirme, boyut, IP kontrolü
│   │   ├── crawler.py                # tarama döngüsü
│   │   ├── crawl_control.py          # start/pause/resume/retry/set_limit/reset
│   │   └── errors.py                 # SkipPage, CrawlFailure ve Türkçe mesajlar
│   ├── indexing/text_normalizer.py   # Türkçe katlama, kelimelere ayırma
│   ├── ranking/pagerank.py           # PageRank
│   ├── storage/                      # database.py + tablo başına repository sınıfları
│   └── views/                        # durum, arama, harita, kelime indeksi JSON'ları
└── tests/                            # birim, entegrasyon ve API testleri
frontend/                             # bkz. 06_on_yuz.md
```

## Neden bu tasarım

- **SQLite:** ~500 sayfa ölçeğinde bellek sorunu yok; asıl ihtiyaç kalıcılık (tarama
  dakikalar sürüyor) ve tarama sırasında arama. Tek dosya, kurulum yok; öğrenci
  `backend/data/dijitalvatan.db`'yi DB Browser ile açıp `words` / `postings` tablolarında
  ters indeksi görebilir.
- **Arka plan görevi:** Orijinaldeki lease/fence düzeneği, çok sayıda isteğin aynı anda
  tarayıcıyı tetikleyebilmesinden doğuyordu. Tek yazarlı bir döngü bu karmaşıklığı ortadan
  kaldırıyor; tarama ziyaretçiye bağlı kalmıyor.
- **Nesil (generation) kontrolü:** Bir sayfa indirilirken tarama duraklatılır ya da
  sıfırlanırsa, sayfanın sonucu yazılmadan atılır (`crawl_state.started_at` ve `status`
  kontrol edilir).
