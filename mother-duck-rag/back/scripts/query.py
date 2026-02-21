#!/usr/bin/env python3
"""CLI de consultas ao RAG: semantic, backlinks, connections, hidden."""
import argparse
import os
from pathlib import Path

import duckdb
from tabulate import tabulate

SCRIPT_DIR = Path(__file__).resolve().parent
QUERIES_DIR = SCRIPT_DIR.parent / "queries"


def load_sql(name: str) -> str:
    p = QUERIES_DIR / f"{name}.sql"
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8").strip()


def get_db_meta(conn: duckdb.DuckDBPyConnection) -> tuple[str, int]:
    r = conn.execute("SELECT key, value FROM metadata WHERE key IN ('model_name', 'embedding_dim')").fetchall()
    meta = dict(r)
    return meta.get("model_name", "all-MiniLM-L6-v2"), int(meta.get("embedding_dim", "384"))


def run_semantic(conn: duckdb.DuckDBPyConnection, query_text: str, limit: int, model_name: str, dim: int):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    query_vec = model.encode([query_text], convert_to_numpy=True)[0].tolist()
    sql = load_sql("semantic_search")
    sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
    sql = sql.replace("$limit", str(int(limit)))
    res = conn.execute(sql, [query_vec]).fetchall()
    cols = ["title", "slug", "file_path", "content", "heading_context", "similarity"]
    if not res:
        print("(Nenhum resultado)")
    else:
        print(tabulate([list(r) for r in res], headers=cols, maxcolwidths=[20, 25, 35, 40, 20, 10]))


def run_backlinks(conn: duckdb.DuckDBPyConnection, slug: str):
    sql = load_sql("find_backlinks").replace("$slug", "?")
    res = conn.execute(sql, [slug]).fetchall()
    if not res:
        print("(Nenhum backlink)")
    else:
        print(tabulate(res, headers=["source_slug", "link_text", "target_slug"]))


def run_connections(conn: duckdb.DuckDBPyConnection, seed_slug: str, hops: int):
    sql = load_sql("find_connections")
    sql = sql.replace("$seed_slug", "?")
    sql = sql.replace("$hops", str(int(hops)))
    res = conn.execute(sql, [seed_slug]).fetchall()
    if not res:
        print("(Nenhuma conexão)")
    else:
        print(tabulate(res, headers=["slug", "hop"]))


def run_hidden(conn: duckdb.DuckDBPyConnection, query_text: str, seed_slug: str, limit: int, model_name: str, dim: int):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    query_vec = model.encode([query_text], convert_to_numpy=True)[0].tolist()
    sql = load_sql("hidden_connections")
    sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
    sql = sql.replace("$seed_slug", "?")
    sql = sql.replace("$limit", str(int(limit)))
    # SQL tem 3 ocorrências de $seed_slug → 3 placeholders; 1 para query_embedding
    res = conn.execute(sql, [query_vec, seed_slug, seed_slug, seed_slug]).fetchall()
    if not res:
        print("(Nenhum resultado)")
    else:
        print(tabulate([list(r) for r in res], headers=["title", "slug", "content", "similarity"], maxcolwidths=[25, 30, 50, 10]))


def main():
    p = argparse.ArgumentParser(description="Consultas ao RAG (DuckDB)")
    p.add_argument("command", choices=["semantic", "backlinks", "connections", "hidden"])
    p.add_argument("query_or_slug", nargs="?", help="Texto da busca ou slug")
    p.add_argument("--seed", default=None, help="Slug da nota semente (hidden)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--hops", type=int, default=2)
    p.add_argument("--db", default=os.environ.get("DB_PATH", "second_brain.duckdb"))
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"Banco não encontrado: {args.db}. Rode 'make ingest' antes.")
        return

    conn = duckdb.connect(args.db, read_only=True)
    model_name, dim = get_db_meta(conn)

    if args.command == "semantic":
        run_semantic(conn, args.query_or_slug or "modelagem de dados", args.limit, model_name, dim)
    elif args.command == "backlinks":
        run_backlinks(conn, args.query_or_slug or "uma-nota")
    elif args.command == "connections":
        run_connections(conn, args.query_or_slug or "uma-nota", args.hops)
    elif args.command == "hidden":
        run_hidden(conn, args.query_or_slug or "dados", args.seed or "uma-nota", args.limit, model_name, dim)

    conn.close()


if __name__ == "__main__":
    main()
