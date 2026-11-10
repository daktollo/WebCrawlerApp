# Yapay zekâ asistanları için çalışma kuralları

Bu depo DSAI 301 "Soru 1" arama motorudur: web tarayıcısı (crawler), ters indeks, PageRank
ve arama. Canlı site: https://dijitalvatan.searchengineplaces.com.tr

## Okuma sırası

1. `README.md` — adresler, portlar, klasörler, yayın ve yerel çalıştırma.
2. `docs/yeniden_insa/README.md` — belge dizini; ardından ihtiyaca göre:
   - `02_mimari.md` (katmanlar, süreç modeli), `03_veri_modeli.md` (SQLite şeması),
   - `04_tarayici.md` (tarama kuralları), `05_arama_ve_api.md` (arama ve uç noktalar),
   - `06_on_yuz.md`, `07_calistirma_ve_test.md` (komutlar, testler, yayın durumu),
   - `08_kararlar_ve_sonraki_adimlar.md` (kararlar, bilinen sınırlar, açık konular),
   - `01_orijinal_proje.md` (ChatGPT Sites'taki orijinalden farklar).
3. `frontend/README.md` — ön yüz komutları ve portlar.
4. Yalnızca yayın gerektiğinde: `.claude/skills/casaos-ssh/SKILL.md`.

Kod: `backend/src/dijitalvatan/` (Python 3.14, FastAPI, SQLite), `backend/tests/`,
`frontend/src/` (React + TypeScript), `backend/docker/`, `frontend/docker/`, `docker-compose.yml`.

## Kurallar

- **Geliştirme yerelde yapılır.** Değişiklikleri yerelde yazın, `cd backend && uv run pytest -q`
  ve gerekiyorsa `cd frontend && npm run build` ile doğrulayın; sonucu (test çıktısı, ölçüm)
  kullanıcıya gösterin.
- **Yayın (deploy) yalnızca kullanıcının açık onayıyla.** Raspberry Pi'a kod göndermeden,
  `docker compose build/up` çalıştırmadan önce ne değişeceğini özetleyip izin isteyin;
  onay gelmezse yayın yapmayın. Bir önceki onay bir sonraki yayını kapsamaz.
- **Belgeler güncel tutulur.** Kod değişince ilgili `docs/yeniden_insa/` belgesi aynı işte
  güncellenir. Belgeler Türkçe; kod, yorum ve tanımlayıcılar İngilizce.
- **Gizli bilgiler depoya girmez.** Sunucu erişim bilgileri yalnızca
  `.claude/skills/casaos-ssh/.env` dosyasında durur (git dışı). Şifreleri koda, belgelere,
  commit'lere veya komut satırına yazmayın.
- **Veritabanı şeması** yalnızca yeni bir `backend/migrations/NNN_ad.sql` dosyasıyla değişir;
  uygulanmış dosya değiştirilmez. Backend konteyneri açılışta bekleyen migration'ları uygular.
- **Git:** commit'ler yerelde yapılabilir; `git push` için kullanıcıya sorun.
