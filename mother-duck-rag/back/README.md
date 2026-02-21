# Back (mother-duck-rag)

RAG backend: ingest Obsidian vault into DuckDB, CLI queries, FastAPI for the frontend.

## Setup

```bash
cp .env.example .env
# Edit: VAULT_PATH, DB_PATH (default second_brain.duckdb), MODEL
uv sync
```

## Ingest

```bash
make ingest
# Or: uv run python scripts/ingest.py test_vault --db second_brain.duckdb
```

## CLI

```bash
make test-semantic
make test-backlinks
make test-connections
make test-hidden
make test-all
make stats
```

Or: `uv run python scripts/query.py semantic "text" --limit 5`, etc.

## API (for frontend)

```bash
make serve
# API at http://localhost:8000
```

Endpoints: `/api/notes`, `/api/semantic`, `/api/backlinks/{slug}`, `/api/connections/{slug}`, `/api/hidden`, `/api/health`.

## Docs

- [docs/ENTENDENDO_O_RAG.md](docs/ENTENDENDO_O_RAG.md) — how the RAG works
