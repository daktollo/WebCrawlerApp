---
name: casaos-ssh
description: Run shell commands on the project's Raspberry Pi 5 deployment server through the CasaOS web terminal (its SSH port is not reachable from outside). Use for anything on the server — checking status, Docker builds and containers, deployment, logs.
---

# CasaOS üzerinden Raspberry Pi'da komut çalıştırma

Sunucu bir **Raspberry Pi 5** (Ubuntu 24.04, `aarch64`). Modem yalnızca CasaOS panelinin
portunu dışarı yönlendiriyor; SSH portu dışarıdan erişilemez. Bu script CasaOS'a
giriş yapar, CasaOS'un `/v1/sys/wsssh` WebSocket'i üzerinden Pi'ın kendi içinden
SSH oturumu açar, tek komutu çalıştırır ve çıktıyı uzak çıkış koduyla döndürür.

## Kurulum

Bilgiler bu klasördeki `.env` dosyasından okunur (gitignored).

- `.env` yoksa `.env.example`'ı `.env` olarak kopyala ve kullanıcının verdiği
  bilgileri **yalnızca oraya** yaz; ardından `chmod 600 .env`.
- Şifreleri README'ye, dokümanlara, commit'lere veya komut satırına yazma.

## Kullanım

Proje kökünden:

```bash
uv run --quiet .claude/skills/casaos-ssh/casaos_ssh.py 'uname -a; df -h /'
```

- Her çağrı yeni bir oturumdur (~5 sn açılış). `cd` ve ortam değişkenleri çağrılar
  arasında taşınmaz; aynı komut içinde `cd ~/app && ...` şeklinde yaz.
- Etkileşimli programlar (vim, top, `docker exec -it`, onay soran `apt`) kullanma;
  `-y`, `--no-pager` gibi etkileşimsiz seçenekler kullan.
- Script'in kendi zaman aşımı 30 dk, Bash aracınınki en fazla 10 dk. Uzun işleri
  (Docker build) Pi'da arka planda başlat ve logu ayrı çağrılarla izle:

  ```bash
  uv run --quiet .claude/skills/casaos-ssh/casaos_ssh.py 'cd ~/dijitalvatan && sudo -v && { nohup sudo -n docker compose build > build.log 2>&1 & }'
  uv run --quiet .claude/skills/casaos-ssh/casaos_ssh.py 'tail -n 30 ~/dijitalvatan/build.log'
  ```

  `sudo -v` şifreyi önde (ön planda) sorar; arka plandaki `sudo -n` önbelleğe alınmış
  yetkiyi kullanır. `{ ... & }` parantezi şart: yoksa `&` tüm `sudo -v && ...`
  zincirini arka plana atar, sudo şifre sorusunda durur (Stopped) ve iş hiç başlamaz.

## sudo ve Docker

- **Docker sudo ister:** her zaman `sudo docker ...`, `sudo docker compose ...`.
- Script `[sudo] password for ...` sorusunu `.env`'deki `SSH_PASSWORD` ile
  kendisi yanıtlar.
- Her `sudo` çağrısı ~20 sn bekler (Pi'da `hostname` çözümlemesi ~10 sn sürüyor),
  önbellekli `sudo -n` dahil; takılma sanma.

## Docker build: hedef mimari arm64

- İmajlar **`linux/arm64`** için olmalı. En basit yol build'i Pi'ın kendisinde
  almak (`sudo docker compose build`).
- Başka makinede build alınacaksa: `docker buildx build --platform linux/arm64 ...`.
- Taban imajlar arm64 sürümü olan resmi imajlar olmalı (`python:3.14-slim`,
  `node:22-alpine` gibi); yalnızca amd64 yayınlanan imajları kullanma.
- Pi'da SD kart ~21 GB boş: build sonrası `sudo docker image prune` ile yer aç.
