---
name: casaos-ssh
description: Run shell commands on the project's Raspberry Pi 5 deployment server through the CasaOS web terminal (its SSH port is not reachable from outside). Use for anything on the server — checking status, Docker builds and containers, deployment, logs.
---

# CasaOS üzerinden Raspberry Pi'da komut çalıştırma

Sunucu bir **Raspberry Pi 5** (Ubuntu 24.04, `aarch64`, yerel IP `192.168.1.118`). Modem
CasaOS panelinin portunu ve Nginx Proxy Manager için 80/443'ü dışarı yönlendiriyor; SSH portu
dışarıdan erişilemez. Bu script CasaOS'a
giriş yapar, CasaOS'un `/v1/sys/wsssh` WebSocket'i üzerinden Pi'ın kendi içinden
SSH oturumu açar, tek komutu çalıştırır ve çıktıyı uzak çıkış koduyla döndürür.

## Kurulum

Bilgiler bu klasördeki `.env` dosyasından okunur (gitignored).

- `.env` yoksa `.env.example`'ı `.env` olarak kopyala ve kullanıcının verdiği
  bilgileri **yalnızca oraya** yaz; ardından `chmod 600 .env`.
- Şifreleri README'ye, dokümanlara, commit'lere veya komut satırına yazma.

## Yayın onayı

Geliştirme yerelde yapılır. Pi'a kod göndermeden, `docker compose build/up/down`
çalıştırmadan veya konteynerleri değiştirmeden önce kullanıcıya ne yapılacağını özetleyip
**açık onay** iste; onay yoksa yapma. Her yayın ayrı onay ister. Salt okuma komutları
(`docker compose ps`, `logs`, `curl` ile durum kontrolü) onay gerektirmez.

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
  uv run --quiet .claude/skills/casaos-ssh/casaos_ssh.py 'cd ~/dijitalvatan && sudo sh -c "nohup docker compose build > build.log 2>&1 &"'
  uv run --quiet .claude/skills/casaos-ssh/casaos_ssh.py 'tail -n 30 ~/dijitalvatan/build.log; pgrep -f "docker compose build" >/dev/null && echo SÜRÜYOR || echo BİTTİ'
  ```

  `sudo` ön planda çalışır, şifre sorusunu script yanıtlar; derlemeyi root yetkili kabuk
  arka plana atar ve `sudo` hemen döner. `build.log` root'a ait olur.
  `sudo -v && { nohup sudo -n ... & }` kalıbını kullanma: bu Pi'da arka plandaki `sudo -n`
  önbelleğe alınmış yetkiyi bulamıyor ("sudo: a password is required") ve derleme hiç
  başlamıyor (2026-11-10'da denendi).

## sudo ve Docker

- **Docker sudo ister:** her zaman `sudo docker ...`, `sudo docker compose ...`.
- Script `[sudo] password for ...` sorusunu `.env`'deki `SSH_PASSWORD` ile
  kendisi yanıtlar.
- Her `sudo` çağrısı ~20 sn bekler (Pi'da `hostname` çözümlemesi ~10 sn sürüyor);
  takılma sanma.

## Docker build: hedef mimari arm64

- İmajlar **`linux/arm64`** için olmalı. En basit yol build'i Pi'ın kendisinde
  almak (`sudo docker compose build`).
- Başka makinede build alınacaksa: `docker buildx build --platform linux/arm64 ...`.
- Taban imajlar arm64 sürümü olan resmi imajlar olmalı (`python:3.14-slim`,
  `node:22-alpine` gibi); yalnızca amd64 yayınlanan imajları kullanma.
- Pi'da SD kart ~21 GB boş: build sonrası `sudo docker image prune` ile yer aç.

## Dosya aktarma

Script dosya yükleyemez, ama komut satırı uzun olabilir: 100 KB'lık tek satır bozulmadan
geçti (sha256 ile doğrulandı). Proje kodu bu yüzden arşiv olarak, ~90 KB'lık base64
parçalarıyla gönderilir:

```bash
git archive --format=tar.gz -o /tmp/app.tar.gz HEAD -- . ':!.claude'
base64 -w0 /tmp/app.tar.gz | split -b 90000 -d - /tmp/part.
# her parça için:  casaos_ssh.py "printf %s '$(cat /tmp/part.00)' >> /tmp/dv.b64"
# sonra Pi'da:      base64 -d /tmp/dv.b64 > /tmp/dv.tar.gz && sha256sum /tmp/dv.tar.gz
#                   tar xzf /tmp/dv.tar.gz -C ~/dijitalvatan
```

İlk parçadan önce `/tmp/dv.b64`'ü silin; sha256'yı yerel arşivle karşılaştırın.
