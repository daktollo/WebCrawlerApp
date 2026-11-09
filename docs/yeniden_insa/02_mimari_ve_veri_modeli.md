# 02 — Mimari ve Veri Modeli

## Klasör yapısı

```
dijitalvatan/
├── supabase/
│   └── migrations/
│       └── 20261109000000_initial.sql
├── backend/
│   ├── pyproject.toml
│   ├── .env.example             # DATABASE_URL=...
│   ├── dijitalvatan/
│   │   ├── config.py            # module-level settings (DEFAULT_SEED, DELAY_MS ...)
│   │   ├── main.py              # driver: small crawl + search from the command line
│   │   ├── storage/
│   │   │   ├── database.py      # psycopg connection pool
│   │   │   ├── crawl_repository.py
│   │   │   ├── page_repository.py
│   │   │   └── word_repository.py
│   │   ├── crawler/
│   │   │   ├── fetcher.py       # HTTP fetch (httpx), content-type and size checks
│   │   │   ├── html_parser.py   # title, text, links
│   │   │   ├── robots.py        # per-host robots.txt cache
│   │   │   ├── frontier.py      # URL normalization and enqueue rules
│   │   │   └── crawler.py       # Crawler class: background loop, state transitions
│   │   ├── indexing/
│   │   │   └── tokenizer.py
│   │   ├── ranking/
│   │   │   └── pagerank.py      # PageRank + revision-keyed cache
│   │   ├── search/
│   │   │   └── search_service.py
│   │   └── api/
│   │       ├── app.py           # FastAPI app, lifespan opens the pool and starts the crawler
│   │       ├── crawl_routes.py
│   │       └── schemas.py
│   └── tests/
├── frontend/                    # Vite + React + TypeScript, see 05_on_yuz.md
└── docs/
```

Katmanlar arasında tek yönlü bağımlılık: `api → search/crawler → indexing/ranking →
storage`. SQL yalnızca repository sınıflarında bulunur.

## Bağımlılıklar

- Arka uç (Python 3.14, `uv`): `fastapi`, `uvicorn`, `httpx`, `selectolax`,
  `psycopg[binary]`, `psycopg-pool`, `python-dotenv`; test: `pytest`,
  `pytest-asyncio`, `respx`.
- Ön yüz: `react`, `react-dom`, `lucide-react`, `d3-force`.

## Veritabanı: Supabase (Postgres)

### Bağlantı

Arka uç Supabase'e **doğrudan Postgres bağlantısıyla** (`psycopg`) bağlanır;
`supabase-py` / REST API kullanılmaz. Sebep: tarayıcı sayfa başına toplu yazım yapar
ve arama tek bir birleşik SQL sorgusudur; bunlar PostgREST üzerinden ya mümkün değil
ya da her biri ayrı HTTP isteği olur.

- Bağlantı adresi `backend/.env` içindeki `DATABASE_URL`'den okunur; yoksa uygulama
  açılışta açık bir hatayla durur.
- Supabase panelinde **Connect → Session pooler** adresi kullanılır
  (`postgresql://postgres.<proje>:<parola>@aws-0-<bölge>.pooler.supabase.com:5432/postgres`).
  Doğrudan bağlantı (`db.<proje>.supabase.co`) yalnızca IPv6 verdiği için çoğu ev
  ağında çalışmaz. Transaction pooler (6543) da çalışır; bunun için hazırlanmış
  ifadeler (prepared statements) kapalı tutulur (`prepare_threshold=None`).
- Tarayıcı süreç içinde çalıştığı için arka uç **tek worker** ile çalıştırılır.

### Şema ve güvenlik

Tablolar `public` yerine ayrı bir **`dijitalvatan` şemasında** durur. Supabase'in REST
API'si yalnızca `public` şemasını dışarı açar; böylece `anon` anahtarıyla tarayıcıdan
bu tablolara erişilemez. Arka uç `postgres` kullanıcısıyla bağlanır.

Tek bir etkin tarama tutulur: yeni bir başlangıç adresiyle başlatıldığında
`pages` ve `words` tabloları `TRUNCATE ... CASCADE` ile boşaltılır (bağlı `links` ve
`postings` de gider). Bu yüzden tablolarda `crawl_id` sütunu yok.

```sql
CREATE SCHEMA dijitalvatan;

CREATE TABLE dijitalvatan.crawl_state (
    id              smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- single row
    seed            text,
    status          text NOT NULL DEFAULT 'idle' CHECK (status IN
                    ('idle','running','paused','completed','blocked','error','limit_reached')),
    max_pages       integer NOT NULL DEFAULT 500 CHECK (max_pages BETWEEN 1 AND 500),
    max_depth       integer NOT NULL DEFAULT 3,
    delay_ms        integer NOT NULL DEFAULT 1500,
    current_url     text,
    last_error      text,
    revision        bigint NOT NULL DEFAULT 0,   -- bumped on every processed page
    started_at      timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    last_indexed_at timestamptz
);
INSERT INTO dijitalvatan.crawl_state DEFAULT VALUES;

CREATE TABLE dijitalvatan.pages (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url           text NOT NULL UNIQUE,
    depth         integer NOT NULL,
    state         text NOT NULL CHECK (state IN ('queued','indexed','failed','skipped')),
    title         text,
    description   text,
    error         text,
    discovered_at timestamptz NOT NULL DEFAULT now(),
    processed_at  timestamptz
);
CREATE INDEX pages_queue_idx ON dijitalvatan.pages (state, depth, id);

CREATE TABLE dijitalvatan.links (
    from_page_id bigint NOT NULL REFERENCES dijitalvatan.pages(id) ON DELETE CASCADE,
    to_page_id   bigint NOT NULL REFERENCES dijitalvatan.pages(id) ON DELETE CASCADE,
    PRIMARY KEY (from_page_id, to_page_id)
);

CREATE TABLE dijitalvatan.words (
    id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    word text NOT NULL UNIQUE
);
CREATE INDEX words_prefix_idx ON dijitalvatan.words (word text_pattern_ops);

CREATE TABLE dijitalvatan.postings (
    word_id bigint NOT NULL REFERENCES dijitalvatan.words(id) ON DELETE CASCADE,
    page_id bigint NOT NULL REFERENCES dijitalvatan.pages(id) ON DELETE CASCADE,
    field   text   NOT NULL CHECK (field IN ('content','title','url')),
    PRIMARY KEY (word_id, page_id, field)
);
CREATE INDEX postings_page_idx ON dijitalvatan.postings (page_id);
```

Notlar:
- Kuyruk ayrı bir tablo değil: `state = 'queued'` satırları `depth, id` sırasıyla
  (genişlik öncelikli). Duraklatma ve sunucu yeniden başlatmada kuyruk veritabanında
  kalır.
- Sayaçlar `COUNT` sorgusuyla hesaplanır (500 sayfa / ~40.000 bağlantı ölçeğinde).
- `links` yalnızca `pages` tablosundaki satırlar arasındadır. Kuyruğa alınmayan
  hedefler (kuyruk sınırı, derinlik, ikili dosya uzantısı) için satır açılmaz.
- Boyut tahmini: 500 sayfada yaklaşık 300–500 bin `postings` satırı, birkaç on MB;
  Supabase ücretsiz katmanın 500 MB sınırının altında. Faz 2'de gerçek sayı ölçülecek.

### Migration

Dosya Supabase CLI biçiminde: `supabase/migrations/20261109000000_initial.sql`.
Uygulamayı **sen** yaparsın; iki yol:
- Supabase panelinde **SQL Editor**'e dosyanın içeriğini yapıştırıp çalıştırmak, veya
- Supabase CLI ile: `supabase link --project-ref <proje>` ardından `supabase db push`.
