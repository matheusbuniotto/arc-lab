# Carrega .env se existir
ifneq (,$(wildcard .env))
    include .env
    export
endif

VAULT_PATH ?= /path/to/obsidian/vault
DB_PATH ?= second_brain.duckdb
MODEL ?= all-MiniLM-L6-v2

.PHONY: help ingest serve test-semantic test-backlinks test-connections test-hidden test-all stats clean

help:
	@echo "Back-RAG - Comandos:"
	@echo ""
	@echo "  make ingest           - Ingerir vault (parse + chunk + embed + DuckDB)"
	@echo "  make test-semantic    - Busca semântica de exemplo"
	@echo "  make test-backlinks   - Backlinks de exemplo"
	@echo "  make test-connections - Conexões N hops de exemplo"
	@echo "  make test-hidden      - Hidden connections de exemplo"
	@echo "  make test-all         - Roda todos os testes de consulta"
	@echo "  make stats            - Estatísticas do banco"
	@echo "  make serve            - Sobe API (FastAPI) em http://localhost:8000"
	@echo "  make clean            - Remove o arquivo DuckDB"
	@echo ""
	@echo "Config (use .env): VAULT_PATH DB_PATH MODEL"

serve:
	uv run uvicorn api.main:app --host 0.0.0.0 --port 8000

ingest:
	uv run python scripts/ingest.py "$(VAULT_PATH)" --model "$(MODEL)" --db "$(DB_PATH)"

test-semantic:
	@echo "=== Busca semântica ==="
	uv run python scripts/query.py semantic "modelagem de dados" --limit 5 --db "$(DB_PATH)"

test-backlinks:
	@echo "=== Backlinks ==="
	uv run python scripts/query.py backlinks "outra-nota" --db "$(DB_PATH)"

test-connections:
	@echo "=== Conexões 2 hops ==="
	uv run python scripts/query.py connections "nota-de-teste" --hops 2 --db "$(DB_PATH)"

test-hidden:
	@echo "=== Hidden connections ==="
	uv run python scripts/query.py hidden "dados" --seed "nota-de-teste" --limit 5 --db "$(DB_PATH)"

test-all: test-semantic test-backlinks test-connections test-hidden
	@echo "=== Testes concluídos ==="

stats:
	@echo "=== Estatísticas do banco ==="
	uv run python -c "import duckdb; from tabulate import tabulate; c=duckdb.connect('$(DB_PATH)'); r=c.execute(\"SELECT 'notes' t, COUNT(*) c FROM notes UNION ALL SELECT 'links', COUNT(*) FROM links UNION ALL SELECT 'chunks', COUNT(*) FROM chunks UNION ALL SELECT 'embeddings', COUNT(*) FROM embeddings\").fetchall(); print(tabulate(r, headers=['tabela','count']))"

clean:
	rm -f "$(DB_PATH)"
	@echo "Banco removido."
