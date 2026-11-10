# Dijital Vatan — Ön Yüz

Vite + React + TypeScript. Orijinal ChatGPT Sites arayüzünden taşınan bileşenler
(`src/app`, `src/components`, `src/lib`).

## Adresler

| | |
|---|---|
| Site | https://dijitalvatan.searchengineplaces.com.tr |
| Yayında sunan | Arka uç, **1319** portunda (`0.0.0.0:1319`), bu klasördeki `dist/`'i `/` adresinden verir |
| Ters vekil | Nginx Proxy Manager: `dijitalvatan.searchengineplaces.com.tr` → `http://192.168.1.118:1319` |
| Geliştirme | `npm run dev` → http://127.0.0.1:5175; `/api` istekleri `http://127.0.0.1:1319`'a gider |

## Komutlar

```bash
npm install
npm run build    # tsc --noEmit + vite build → dist/
npm run dev      # arka uç 1319'da çalışırken anlık geliştirme
```

Ön yüz ayrı bir sunucu gerektirmez: yayında site ve API aynı adresten (1319) gelir.
Ayrıntılar: [docs/yeniden_insa/06_on_yuz.md](../docs/yeniden_insa/06_on_yuz.md).
