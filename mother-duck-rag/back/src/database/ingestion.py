"""
Pipeline de ingestão: vault -> notes, links, chunks, embeddings -> DuckDB.
"""
import json
from pathlib import Path

from tqdm import tqdm

from src.database.schema import (
    create_hnsw_index,
    drop_all_tables,
    get_embedding_dim,
    get_schema_sql,
    init_database,
)
from src.embeddings.embedder import Embedder
from src.parsers import chunk_note, chunk_text_for_embedding, extract_links_from_note, parse_note_file
from src.parsers.chunker import Chunk


def collect_note_files(vault_path: Path) -> list[Path]:
    vault_path = Path(vault_path)
    if not vault_path.is_dir():
        raise FileNotFoundError(f"Vault não encontrado: {vault_path}")
    return list(vault_path.rglob("*.md"))


def run_ingestion(
    vault_path: str | Path,
    db_path: str,
    model_name: str,
    recreate: bool = True,
) -> None:
    vault_path = Path(vault_path)
    files = collect_note_files(vault_path)
    if not files:
        print("Nenhum arquivo .md encontrado no vault.")
        return

    dim = get_embedding_dim(model_name)
    if dim is None:
        raise ValueError(f"Modelo '{model_name}' não suportado.")

    conn = init_database(db_path, model_name=model_name, embedding_dim=dim)
    if recreate:
        drop_all_tables(conn)
        schema_sql = get_schema_sql(dim, model_name)
        for stmt in schema_sql.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
        conn.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            [("model_name", model_name), ("embedding_dim", str(dim))],
        )

    note_id_by_slug = {}
    link_rows = []
    for fp in tqdm(files, desc="Parse notes"):
        try:
            note = parse_note_file(fp, vault_path)
        except Exception as e:
            print(f"Erro em {fp}: {e}")
            continue
        slug = note["slug"]
        note_id = len(note_id_by_slug) + 1
        note_id_by_slug[slug] = note_id
        conn.execute(
            """
            INSERT INTO notes (note_id, file_path, slug, title, content, frontmatter, tags, aliases,
                source_type, source_title, source_author, source_url, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                note_id,
                note["file_path"],
                slug,
                note["title"],
                note["content"],
                json.dumps(note["frontmatter"]) if note.get("frontmatter") else "{}",
                note["tags"],
                note["aliases"],
                note.get("source_type"),
                note.get("source_title"),
                note.get("source_author"),
                note.get("source_url"),
                note.get("word_count", 0),
            ],
        )
        for edge in extract_links_from_note(note["content"], slug):
            link_rows.append(edge)

    link_id = 0
    for edge in link_rows:
        link_id += 1
        conn.execute(
            "INSERT INTO links (link_id, source_slug, target_slug, link_text) VALUES (?, ?, ?, ?)",
            [link_id, edge["source_slug"], edge["target_slug"], edge["link_text"]],
        )

    chunk_rows = []
    texts_to_embed = []
    for fp in tqdm(files, desc="Chunk"):
        try:
            note = parse_note_file(fp, vault_path)
        except Exception:
            continue
        slug = note["slug"]
        note_id = note_id_by_slug.get(slug)
        if not note_id:
            continue
        chunks = chunk_note(note["content"], note["title"])
        for idx, ch in enumerate(chunks):
            chunk_id = len(chunk_rows) + 1
            chunk_rows.append({
                "chunk_id": chunk_id,
                "note_id": note_id,
                "chunk_index": idx,
                "content": ch.content,
                "heading_context": ch.heading_context or "",
                "chunk_type": ch.chunk_type,
                "start_line": ch.start_line,
                "end_line": ch.end_line,
                "text_for_embed": chunk_text_for_embedding(ch, note["title"]),
            })
            texts_to_embed.append(chunk_rows[-1]["text_for_embed"])

    for row in chunk_rows:
        conn.execute(
            "INSERT INTO chunks (chunk_id, note_id, chunk_index, content, heading_context, chunk_type, start_line, end_line) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row["chunk_id"],
                row["note_id"],
                row["chunk_index"],
                row["content"],
                row["heading_context"],
                row["chunk_type"],
                row["start_line"],
                row["end_line"],
            ],
        )

    print("Gerando embeddings...")
    embedder = Embedder(model_name)
    embeddings = embedder.encode(texts_to_embed)
    for i, row in enumerate(chunk_rows):
        emb = embeddings[i].tolist()
        conn.execute(
            "INSERT INTO embeddings (embedding_id, chunk_id, embedding, model_name) VALUES (?, ?, ?, ?)",
            [row["chunk_id"], row["chunk_id"], emb, model_name],
        )

    hyperedge_id = 0
    edge_value_to_id = {}
    for note_id, slug in [(v, k) for k, v in note_id_by_slug.items()]:
        res = conn.execute("SELECT tags FROM notes WHERE note_id = ?", [note_id]).fetchone()
        tags = res[0] if res and res[0] is not None else []
        if not tags:
            continue
        for tag in tags:
            key = ("tag", tag)
            if key not in edge_value_to_id:
                hyperedge_id += 1
                edge_value_to_id[key] = hyperedge_id
                conn.execute(
                    "INSERT INTO hyperedges (hyperedge_id, edge_type, edge_value) VALUES (?, ?, ?)",
                    [hyperedge_id, "tag", tag],
                )
            he_id = edge_value_to_id[key]
            conn.execute(
                "INSERT INTO hyperedge_members (hyperedge_id, note_id) VALUES (?, ?) ON CONFLICT (hyperedge_id, note_id) DO NOTHING",
                [he_id, note_id],
            )

    create_hnsw_index(conn)
    conn.close()
    print("Ingestão concluída.")
