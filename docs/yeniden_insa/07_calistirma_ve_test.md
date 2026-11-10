# 07 — Çalıştırma ve Test

## Gereksinimler

- Python 3.14 ve [uv](https://docs.astral.sh/uv/) (önerilen) — ya da pip ile
  `backend/requirements.txt`.
- Node.js ≥ 22.13 ve npm.

## Yerelde çalıştırma (Docker'sız)

```bash
cd backend
uv sync                                  # ya da: pip install -r requirements.txt -r requirements-dev.txt && pip install -e .
uv run python -m dijitalvatan.migrate    # backend/data/dijitalvatan.db oluşturur / günceller
uv run python -m dijitalvatan.main       # backend: http://127.0.0.1:1320

cd ../frontend
npm install
npm run dev                              # site: http://127.0.0.1:5175 (/api → 1320)
```

Taramayı başlatmak: sitede "Canlı arama" → "Tarama yönetimi" → başlangıç adresi ve sayfa
sınırı → "Taramayı başlat". Aynı şey komut satırından:

```bash
curl -X POST http://127.0.0.1:1320/api/crawl/control -H 'Content-Type: application/json' \
  -d '{"action":"start","seed":"https://www.bogazici.edu.tr/","maxPages":200}'
```

## Yayın

| | |
|---|---|
| Adres | https://dijitalvatan.searchengineplaces.com.tr |
| Sunucu | Raspberry Pi 5 `192.168.1.118` (Ubuntu 24.04, arm64), klasör `~/dijitalvatan` |
| Ters vekil | Nginx Proxy Manager (Pi'de 80/443), proxy host `http` → `192.168.1.118:1319`, Websockets açık, "Publicly Accessible" — ayarlı |
| Konteynerler | `frontend` 1319 (nginx) · `backend` 1320 (yalnızca `127.0.0.1`) · volume `dijitalvatan_dijitalvatan-data` |
| Erişim | SSH dışarıya kapalı; komutlar `.claude/skills/casaos-ssh` ile CasaOS web terminalinden |

Adımlar kök [README](../../README.md#yayın-raspberry-pi-docker)'de: kod arşivi aktarılır,
`sudo docker compose build` ve `up -d`. Backend konteyneri açılışta migration'ları uygular.

**Yayın durumu (2026-11-10):**

| Kontrol (Pi üzerinden) | Sonuç |
|---|---|
| `docker compose ps` | `backend` ve `frontend` çalışıyor |
| `127.0.0.1:1320/api/crawl/status` | 200 (migration açılışta uygulandı, boş veritabanı) |
| `127.0.0.1:1319/` ve `/api/crawl/status` | 200 / 200 |
| `192.168.1.118:1319` (LAN) | 200 |
| `192.168.1.118:1320` (LAN) | bağlantı yok — beklendiği gibi kapalı |
| NPM, `Host: dijitalvatan.searchengineplaces.com.tr` ile http | 200 |
| NPM https | sertifika yok — NPM'de SSL sekmesinden Let's Encrypt alınmalı |
| Herkese açık DNS | `dijitalvatan` kaydı yok; A kaydı Pi'nin dış IP'sine (`95.173.229.167`) yazılmalı |
Site herkese açık olduğu için tarama yönetimi (`POST /api/crawl/control`) korunmalı
([08](08_kararlar_ve_sonraki_adimlar.md)).

## Testler

```bash
cd backend && uv run pytest -q
# pip ile kurulumda: python -m pytest -q   (requirements ile temiz ortamda doğrulandı)
```

64 test (2026-11-10). Kararlılık ölçümü: 40 ardışık çalıştırmanın 40'ı geçti
(her biri < 1 sn; thread uyarıları hata sayılarak). Düzeltmeden önce 25 çalıştırmanın 7'si
"database is locked" ile düşüyor, bazıları da kapanmayan `aiosqlite` thread'i yüzünden
askıda kalıyordu ([02](02_mimari.md)).

| Dosya | Kapsam |
|---|---|
| `test_url_rules.py` | URL normalleştirme, özel/yerel adreslerin reddi, Boğaziçi takma adı (orijinal testlerden taşındı) |
| `test_robots.py` | robots grupları, en uzun kural, joker, `$`, kodlanmış Unicode (orijinal testlerden) |
| `test_html_extractor.py` | Gizli içerik, entity'ler, `noindex`/`nofollow`, `<base>`, CAPTCHA sayfaları, boyut sınırları (orijinal testlerden) |
| `test_text_and_rank.py` | Türkçe katlama; PageRank'in orijinal TypeScript çıktısıyla eşitliği |
| `test_crawl_integration.py` | Taklit bir sitede uçtan uca tarama: robots yasağı, `noindex`, 403 veren dış site, PDF, arama, kelime indeksi, harita, sayfa sınırı, sıfırlama, kontrol kuralları |
| `test_api.py` | HTTP hata biçimi, doğrulama mesajları ve kodları |

## Ölçümler (gerçek tarama, 2026-11-10)

Seed `https://www.bogazici.edu.tr/`, sınır 20:

| Ölçüm | Değer |
|---|---|
| Süre | 20 adres ≈ 53 sn (adres başına ~2,6 sn: 1,5 sn bekleme + yeni siteler için robots.txt + ağ) |
| İndekslenen / atlanan / hatalı | 17 / 2 / 1 |
| Kuyrukta kalan | 60 |
| Kelime / keşfedilen bağlantı | 2.051 / 2.368 (harita: 157 bağlantı, iki ucu da indekslenmiş) |
| Arama ("Boğaziçi araştırma") | 13 sonuç, 7 ms |

Sunucu yeniden başlatıldıktan sonra indeks ve tarama durumu korunmuş olarak geldi
(ölçümler yerel, Docker'sız çalıştırmada alındı).
Hatalar beklenen türdendi: `arsivmerkezi.bogazici.edu.tr` DNS/bağlantı hatası,
`vimeo.com` `noindex`, `harita.bogazici.edu.tr` robots.txt yerine HTML döndürdü.
