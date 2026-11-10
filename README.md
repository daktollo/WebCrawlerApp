# Dijital Vatan — Arama Motoru

DSAI 301 için web tarayıcısı (crawler), ters indeks ve PageRank'i öğreten arama motoru:
FastAPI + SQLite arka uç, React ön yüz.

## Adresler

| | |
|---|---|
| Site | https://dijitalvatan.searchengineplaces.com.tr |
| Sunucu portu | **1319** (`0.0.0.0`) — site, API ve tarayıcı tek süreçte |
| Ters vekil | Nginx Proxy Manager: `dijitalvatan.searchengineplaces.com.tr` → `http://192.168.1.118:1319` (Websockets açık, herkese açık) |
| Yerelde | http://127.0.0.1:1319 · ön yüz geliştirme sunucusu http://127.0.0.1:5175 |

## Hızlı başlangıç

```bash
cd backend
uv sync                                   # ya da: pip install -r requirements.txt && pip install -e .
uv run python -m dijitalvatan.migrate     # veritabanını oluşturur
cd ../frontend && npm install && npm run build
cd ../backend && uv run python -m dijitalvatan.main   # 0.0.0.0:1319
```

Taramayı "Canlı arama" ekranındaki "Tarama yönetimi"nden başlatın.

Ayrıntılar (mimari, veri modeli, tarayıcı kuralları, API, testler, yayın):
[docs/yeniden_insa](docs/yeniden_insa/README.md). Ön yüz: [frontend/README.md](frontend/README.md).
Orijinal ChatGPT Sites kaynak kodu referans olarak `soruce/` altındadır (git dışında).
