# 03 — Veri Modeli (SQLite)

Şema: `backend/migrations/001_initial.sql` (uygulandı, 2026-11-10).
Zaman damgaları ISO-8601 UTC metni (`2026-11-10T09:30:00.000Z`); `*_ms` sütunları epoch
milisaniye.

## Tablolar

| Tablo | Satır | Anlamı |
|---|---|---|
| `crawl_state` | tek satır (`id = 1`) | Etkin tarama: `seed`, `status`, `max_pages` (vars. 200), `max_depth` (3), `current_url`, `last_error`, `revision`, `indexed_words`, `started_at`, `updated_at` |
| `origins` | site başına | `robots_policy` (JSON), `robots_checked_at_ms`, `delay_ms`, `next_request_at_ms`, `blocked_reason`, `blocked_phase` |
| `queue` | keşfedilen her URL | `url`, `origin`, `depth`, `state` (`queued` / `done` / `skipped` / `failed`), `error`, `updated_at` |
| `pages` | indekslenen her sayfa (yönlendirme sonrası son URL) | `url`, `title`, `description`, `body` (≤ 200.000 karakter), `rank`, `indexed_at` |
| `links` | sayfanın giden bağlantıları | `source_id → pages`, `target_url` (hedef indekslenmemiş olabilir) |
| `words` | sözlük | katlanmış kelime |
| `postings` | ters indeks | `(word_id, page_id, field)`; `field` ∈ `content`, `title`, `url` |

İlişkiler `ON DELETE CASCADE`: bir sayfa silinince bağlantıları ve kelime kayıtları da
gider.

## Kurallar

- **`revision`** her değişiklikte artar, hiç azalmaz; ön yüz yeni veri olup olmadığını buna
  bakarak anlar.
- **`started_at`** bir tarama neslini tanımlar. Sıfırlama ve yeni seed ona kesin olarak daha
  geç bir değer verir; ön yüz eski nesle ait gecikmiş cevapları bununla ayıklar.
- **Kuyruk sırası:** `state = 'queued'`, `ORDER BY depth, id` (genişlik öncelikli). İstek
  zamanı gelmemiş sitelerin URL'leri atlanır; engellenmiş sitelerinkiler "atlandı" diye
  kaydedilmek üzere seçilir.
- **Yeni seed / sıfırlama:** `queue`, `pages`, `links`, `words` ve `postings` boşaltılır.
  `origins`'ten yalnızca ileri tarihli `Retry-After` beklemeleri kalır.
- **Sayaçlar** (`indexedPages`, `queuedPages` ...) `COUNT` ile hesaplanır; `indexed_words`
  PageRank yenilenirken güncellenir.

## Migration düzeni

- Dosyalar `backend/migrations/NNN_ad.sql`, ada göre sırayla uygulanır.
- `uv run python -m dijitalvatan.migrate` veritabanını WAL moduna alır, uygulanmamış
  dosyaları her biri kendi transaction'ında çalıştırır ve `schema_migrations` tablosuna
  yazar; tekrar çalıştırmak güvenli.
- Sunucu açılışta uygulanmamış migration görürse açık bir hatayla durur.
- Şemayı değiştirmek için yeni bir dosya eklenir (`002_...sql`); uygulanmış dosya
  değiştirilmez.
