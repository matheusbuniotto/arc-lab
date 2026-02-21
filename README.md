# arc-lab

Obsidian RAG app: **mother-duck-rag** (DuckDB, embeddings, ingest + API) + React frontend.

## Structure

- **mother-duck-rag/back/** — Python backend: DuckDB, embeddings, ingest CLI, FastAPI server.
- **mother-duck-rag/front/** — Vite + React + TypeScript frontend.

## Quick start

1. **Backend (ingest + API)**

   ```bash
   cd mother-duck-rag/back
   cp .env.example .env
   # Edit .env: VAULT_PATH, DB_PATH (default second_brain.duckdb)
   uv sync
   make ingest          # ingest vault (or use test_vault for demo)
   make serve           # API at http://localhost:8000
   ```

2. **Vault** — Configure vault path in `mother-duck-rag/back/.env` (`VAULT_PATH`). Vaults are listed in the app sidebar; registry is in `mother-duck-rag/back/vaults.json`.

3. **Frontend**

   ```bash
   cd mother-duck-rag/front
   npm install
   npm run dev          # UI at http://localhost:5173
   ```

4. Open http://localhost:5173 — Graph, **Ask (Q&A)**, **Agent**, **Research**, Semantic, Backlinks, Connections, Hidden.

**Chat (Q&A)** and **Agent** require an LLM API: set `OPENAI_API_KEY` in `mother-duck-rag/back/.env` (and optionally `OPENAI_BASE_URL`, `OPENAI_MODEL`).  
**Research** (web + notes) and the agent’s `web_research` tool use Perplexity: set `PERPLEXITY_API_KEY`. Without it, the Research tab shows only your notes.

## API

With `make serve` in `mother-duck-rag/back`:

- `GET /api/health` — backend + DB check (optional `?vault=id`)
- `GET /api/vaults` — list registered vaults
- `GET /api/notes`, `GET /api/graph` — notes and graph (optional `?vault=id`)
- `GET /api/semantic?q=...&limit=10`, `GET /api/backlinks/{slug}`, `GET /api/connections/{slug}?hops=2`, `GET /api/hidden?q=...&seed=...&limit=10`
- `POST /api/chat` — RAG answer with citations
- `POST /api/agent` — AI agent (search, backlinks, RAG, web research)
- `GET /api/research?q=...` — web (Perplexity) + vault notes

Frontend uses `VITE_API_URL` (default `http://localhost:8000`). Set in `mother-duck-rag/front/.env` if the API runs elsewhere.

## Vault structure (Obsidian)

- **[mother-duck-rag/docs/OBSIDIAN_VAULT_STRUCTURE.md](mother-duck-rag/docs/OBSIDIAN_VAULT_STRUCTURE.md)** — folders, naming, `source_type` / `tags`, templates.
- **mother-duck-rag/vault_template/** — copy as your vault root: MOCs, Learning (Books/Courses/Talks), Slipbox, `_templates/`.

Set `VAULT_PATH` in `mother-duck-rag/back/.env` to your vault root.

## Docs

- [mother-duck-rag/back/README.md](mother-duck-rag/back/README.md) — ingest, CLI, API
- [mother-duck-rag/back/docs/ENTENDENDO_O_RAG.md](mother-duck-rag/back/docs/ENTENDENDO_O_RAG.md) — how the RAG works
