# Dijital Vatan — Arama Motoru

DSAI 301 için web tarayıcısı (crawler), ters indeks ve PageRank'i öğreten arama motoru:
FastAPI + SQLite arka uç, React ön yüz, Docker Compose ile yayın.

## Adresler ve portlar

| | |
|---|---|
| Site | https://dijitalvatan.searchengineplaces.com.tr |
| Sunucu | Raspberry Pi 5, `192.168.1.118` (Ubuntu 24.04, arm64), uygulama klasörü `~/dijitalvatan` |
| Ters vekil | Nginx Proxy Manager (Pi'de, 80/443): `dijitalvatan.searchengineplaces.com.tr` → `http://192.168.1.118:1319` — Websockets açık, erişim listesi "Publicly Accessible". Ayarlı, ayrıca bir şey yapmaya gerek yok. |
| **Frontend** | **1319** — nginx konteyneri; derlenmiş siteyi sunar, `/api/*` isteklerini backend'e iletir |
| **Backend** | **1320** — FastAPI + arka plan tarayıcısı; Pi'de yalnızca `127.0.0.1:1320`'den erişilir (dışarıya kapalı) |
| Veritabanı | SQLite, Docker volume `dijitalvatan_dijitalvatan-data` → konteynerde `/app/data/dijitalvatan.db` |

```
İnternet → NPM (443) → frontend:1319 (nginx) ─┬─ /        → derlenmiş React sitesi
                                              └─ /api/*   → backend:1320 (FastAPI + tarayıcı) → SQLite
```

## Klasörler

| Klasör | İçerik |
|---|---|
| `backend/` | Python paketi (`src/dijitalvatan`), migration'lar, testler, `requirements.txt` |
| `backend/docker/` | `Dockerfile`, `entrypoint.sh` (migration + sunucu), `Dockerfile.dockerignore` |
| `frontend/` | Vite + React + TypeScript ([frontend/README.md](frontend/README.md)) |
| `frontend/docker/` | `Dockerfile` (Node ile derle → nginx), `nginx.conf`, `Dockerfile.dockerignore` |
| `docker-compose.yml` | İki servis, port eşlemeleri, veri volume'ü |
| `docs/yeniden_insa/` | Mimari, veri modeli, tarayıcı kuralları, API, testler ([README](docs/yeniden_insa/README.md)) |
| `soruce/` | Orijinal ChatGPT Sites kaynak kodu, yalnızca referans (git dışında) |

## Yayın (Raspberry Pi, Docker)

Pi'nin SSH portu dışarıya kapalı; komutlar CasaOS web terminali üzerinden
`.claude/skills/casaos-ssh` skill'iyle çalıştırılır (bağlantı bilgileri o klasördeki `.env`'de).
Docker `sudo` ister; imajlar Pi'nin kendisinde `linux/arm64` için derlenir.

```bash
# 1) Kodu Pi'ye gönder (git deposu Pi'de yok; izlenen dosyaların arşivi aktarılır)
git archive --format=tar.gz HEAD > /tmp/dijitalvatan.tar.gz
#    arşiv base64 ile casaos_ssh.py üzerinden ~/dijitalvatan altına açılır

# 2) Pi'de derle ve başlat
cd ~/dijitalvatan
# Derleme uzun sürer: sudo ön planda şifreyi alır, derleme root kabuğundan arka plana atılır.
# (`sudo -v` + `nohup sudo -n ...` kalıbı bu Pi'de "a password is required" ile başlamadı.)
sudo sh -c "nohup docker compose build > build.log 2>&1 &"
tail -n 20 build.log               # ayrı çağrılarla izleyin
sudo docker compose up -d
sudo docker image prune -f         # SD kartta yer aç

# 3) Kontrol
sudo docker compose ps
curl -s http://127.0.0.1:1320/api/crawl/status   # backend
curl -sI http://127.0.0.1:1319/                  # frontend
sudo docker compose logs --tail 50 backend
```

- Backend konteyneri her açılışta bekleyen migration'ları uygular (`backend/docker/entrypoint.sh`).
- Veritabanı volume'de durur; `docker compose down` silmez, `down -v` siler.
- Güncelleme: yeni arşivi aynı klasöre açıp `sudo docker compose up -d --build`.

## Yerelde geliştirme (Docker'sız)

```bash
cd backend
uv sync                                   # ya da: pip install -r requirements.txt && pip install -e .
uv run python -m dijitalvatan.migrate     # backend/data/dijitalvatan.db
uv run python -m dijitalvatan.main        # backend: http://127.0.0.1:1320

cd ../frontend
npm install
npm run dev                               # site: http://127.0.0.1:5175 (/api → 1320)
```

Testler: `cd backend && uv run pytest -q`.

## Güvenlik notu

Uygulamada giriş yok: siteye erişen herkes taramayı başlatabilir, durdurabilir ve
sıfırlayabilir (`POST /api/crawl/control`). Site herkese açıkken bu yolun NPM'de
("Custom locations" + parolalı Access List) ya da uygulamada korunması gerekir.
