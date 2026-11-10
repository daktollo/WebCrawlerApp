# Dijital Vatan — Arama Motoru

DSAI 301 için web tarayıcısı (crawler), ters indeks ve PageRank'i öğreten arama motoru:
FastAPI + SQLite arka uç, React ön yüz.

## Hızlı başlangıç

```bash
cd backend
uv sync                                   # ya da: pip install -r requirements.txt && pip install -e .
uv run python -m dijitalvatan.migrate     # veritabanını oluşturur
cd ../frontend && npm install && npm run build
cd ../backend && uv run python -m dijitalvatan.main
```

Site: http://127.0.0.1:8000 — taramayı "Canlı arama" ekranındaki "Tarama yönetimi"nden başlatın.

Ayrıntılar (mimari, veri modeli, tarayıcı kuralları, API, testler): [docs/yeniden_insa](docs/yeniden_insa/README.md).
Orijinal ChatGPT Sites kaynak kodu referans olarak `soruce/` altındadır (git dışında).
