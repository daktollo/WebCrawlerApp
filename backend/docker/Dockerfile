# Backend: crawl API + background crawler (FastAPI, SQLite). Build context: backend/
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    DIJITALVATAN_HOST=0.0.0.0
WORKDIR /app

# Dependencies first so code changes do not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev

# SQLite database and crawler lock live here; mount a volume to keep them.
VOLUME /app/data
EXPOSE 1320
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
CMD ["sh", "/usr/local/bin/entrypoint.sh"]
