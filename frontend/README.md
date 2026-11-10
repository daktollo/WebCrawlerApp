# Dijital Vatan — Ön Yüz

Vite + React + TypeScript. Orijinal ChatGPT Sites arayüzünden taşınan bileşenler
(`src/app`, `src/components`, `src/lib`).

## Adresler ve portlar

| | |
|---|---|
| Site | https://dijitalvatan.searchengineplaces.com.tr |
| Yayında | **1319** — `docker/` altındaki nginx konteyneri `dist/`'i sunar, `/api/*`'yi backend'e (`backend:1320`) iletir |
| Ters vekil | Nginx Proxy Manager (Pi, 80/443): `dijitalvatan.searchengineplaces.com.tr` → `http://192.168.1.118:1319` (ayarlı) |
| Backend | **1320** |
| Geliştirme | `npm run dev` → http://127.0.0.1:5175; `/api` istekleri `http://127.0.0.1:1320`'ye gider |

## Komutlar

```bash
npm install
npm run dev      # backend 1320'de çalışırken anlık geliştirme
npm run build    # tsc --noEmit + vite build → dist/
```

## Docker

`docker/Dockerfile` iki aşamalı: `node:22-alpine` ile `npm ci && npm run build`, ardından
`nginx:1.28-alpine` 1319'da `dist/`'i sunar (`docker/nginx.conf`). Tek başına değil, proje
kökündeki `docker-compose.yml` ile backend'le birlikte çalıştırılır — bkz. [kök README](../README.md).

Ayrıntılar: [docs/yeniden_insa/06_on_yuz.md](../docs/yeniden_insa/06_on_yuz.md).
