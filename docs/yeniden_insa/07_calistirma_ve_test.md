# 07 — Çalıştırma ve Test

## Gereksinimler

- Python 3.14 ve [uv](https://docs.astral.sh/uv/) (önerilen) — ya da pip ile
  `backend/requirements.txt`.
- Node.js ≥ 22.13 ve npm.

## Kurulum

```bash
# Arka uç
cd backend
uv sync                                  # ya da: pip install -r requirements.txt -r requirements-dev.txt && pip install -e .
uv run python -m dijitalvatan.migrate    # backend/data/dijitalvatan.db oluşturur / günceller

# Ön yüz
cd ../frontend
npm install
npm run build                            # frontend/dist
```

## Çalıştırma

```bash
cd backend
uv run python -m dijitalvatan.main      # 0.0.0.0:1319 → http://127.0.0.1:1319  (site + API + tarayıcı)
```

Ön yüz üzerinde çalışırken: arka uç açıkken `cd frontend && npm run dev` →
http://127.0.0.1:5175 (değişiklikler anında yansır).

Taramayı başlatmak: sitede "Canlı arama" → "Tarama yönetimi" → başlangıç adresi ve sayfa
sınırı → "Taramayı başlat". Aynı şey komut satırından:

```bash
curl -X POST http://127.0.0.1:1319/api/crawl/control -H 'Content-Type: application/json' \
  -d '{"action":"start","seed":"https://www.bogazici.edu.tr/","maxPages":200}'
```

## Yayın

| | |
|---|---|
| Adres | https://dijitalvatan.searchengineplaces.com.tr |
| Ters vekil | Nginx Proxy Manager, proxy host: `http` → `192.168.1.118:1319`, Websockets açık, erişim listesi "Publicly Accessible" |
| Sunucu | `192.168.1.118` üzerinde `uv run python -m dijitalvatan.main` (`0.0.0.0:1319`); ön yüz önceden `npm run build` ile derlenmiş olmalı |

Durum (2026-11-10): proxy kaydı hazırlandı; alan adı için DNS kaydı henüz çözülmüyor ve
uygulama `192.168.1.118`'e kurulmadı. Site herkese açık olacağı için tarama yönetimi
(`POST /api/crawl/control`) korunmalı ([08](08_kararlar_ve_sonraki_adimlar.md)).

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

Sunucu yeniden başlatıldıktan sonra indeks ve tarama durumu korunmuş olarak geldi.
Hatalar beklenen türdendi: `arsivmerkezi.bogazici.edu.tr` DNS/bağlantı hatası,
`vimeo.com` `noindex`, `harita.bogazici.edu.tr` robots.txt yerine HTML döndürdü.
