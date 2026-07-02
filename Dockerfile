FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash mcp
WORKDIR /app

COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER mcp

ENTRYPOINT ["psql-mcp"]
CMD ["--access-mode=restricted", "--transport=stdio"]
