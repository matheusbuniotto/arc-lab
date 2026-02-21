#!/usr/bin/env python3
"""Ingestão: lê o vault Obsidian e popula o DuckDB."""
import argparse
import os

from src.database.ingestion import run_ingestion


def main():
    p = argparse.ArgumentParser(description="Ingerir vault Obsidian no DuckDB")
    p.add_argument("vault_path", nargs="?", default=os.environ.get("VAULT_PATH"), help="Pasta do vault")
    p.add_argument("--model", default=os.environ.get("MODEL", "all-MiniLM-L6-v2"), help="Modelo de embeddings")
    p.add_argument("--db", default=os.environ.get("DB_PATH", "second_brain.duckdb"), help="Arquivo DuckDB")
    p.add_argument("--no-recreate", action="store_true", help="Não dropar tabelas antes")
    args = p.parse_args()
    if not args.vault_path:
        p.error("Informe vault_path ou defina VAULT_PATH no .env")
    run_ingestion(
        vault_path=args.vault_path,
        db_path=args.db,
        model_name=args.model,
        recreate=not args.no_recreate,
    )


if __name__ == "__main__":
    main()
