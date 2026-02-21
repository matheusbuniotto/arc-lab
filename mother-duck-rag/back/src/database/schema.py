"""
Schema do DuckDB para o RAG de notas Obsidian.

Por que essas tabelas?
- notes: uma linha por arquivo .md (metadados + conteúdo). É a "fonte da verdade" por nota.
- links: cada [[Wikilink]] vira uma aresta source_slug -> target_slug. Forma o GRAFO da sua base.
- chunks: cada nota é cortada em pedaços (~512 chars) para não passar o limite de contexto do modelo.
- embeddings: cada chunk vira um vetor (ex. 384 ou 1024 floats). Busca semântica = similaridade entre vetores.
- hyperedges / hyperedge_members: agrupam notas por tag ou pasta (multiway relations) para consultas "notas que compartilham N tags".
"""
import duckdb

# Modelo -> dimensão do vetor. O schema do DuckDB exige FLOAT[N] fixo; N depende do modelo.
MODEL_CONFIGS = {
    "all-MiniLM-L6-v2": 384,
    "BAAI/bge-m3": 1024,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
}

DEFAULT_MODEL = "all-MiniLM-L6-v2"


def get_embedding_dim(model_name: str) -> int | None:
    """Retorna a dimensão do embedding para o modelo; None se desconhecido."""
    return MODEL_CONFIGS.get(model_name)


def get_schema_sql(embedding_dim: int, model_name: str) -> str:
    """Gera o SQL do schema com a dimensão correta do vetor (embedding_dim)."""
    return f"""
-- Notas: uma linha por arquivo .md do vault
-- source_*: for learning (book/course/talk) and projects, used by RAG filters and citations
CREATE TABLE IF NOT EXISTS notes (
    note_id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL UNIQUE,
    slug VARCHAR NOT NULL UNIQUE,
    title VARCHAR,
    content TEXT,
    frontmatter JSON,
    tags VARCHAR[],
    aliases VARCHAR[],
    source_type VARCHAR,
    source_title VARCHAR,
    source_author VARCHAR,
    source_url VARCHAR,
    created_date DATE,
    modified_date TIMESTAMP,
    word_count INTEGER
);

-- Arestas do grafo: cada [[Wikilink]] vira (source_slug, target_slug)
CREATE TABLE IF NOT EXISTS links (
    link_id INTEGER PRIMARY KEY,
    source_slug VARCHAR NOT NULL,
    target_slug VARCHAR NOT NULL,
    link_text VARCHAR,
    link_type VARCHAR DEFAULT 'wikilink'
);

-- Chunks: pedaços de texto por nota para RAG (~512 chars, respeitando headings)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id INTEGER PRIMARY KEY,
    note_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    heading_context VARCHAR,
    chunk_type VARCHAR,
    start_line INTEGER,
    end_line INTEGER,
    FOREIGN KEY (note_id) REFERENCES notes(note_id)
);

-- Vetores por chunk. Dimensão fixa conforme o modelo (384 ou 1024).
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL UNIQUE,
    embedding FLOAT[{embedding_dim}] NOT NULL,
    model_name VARCHAR DEFAULT '{model_name}',
    created_at TIMESTAMP DEFAULT current_timestamp,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);

-- Hyperedges: uma "aresta" conecta várias notas (ex.: tag #data-eng conecta todas com essa tag)
CREATE TABLE IF NOT EXISTS hyperedges (
    hyperedge_id INTEGER PRIMARY KEY,
    edge_type VARCHAR NOT NULL,
    edge_value VARCHAR NOT NULL,
    UNIQUE(edge_type, edge_value)
);

CREATE TABLE IF NOT EXISTS hyperedge_members (
    hyperedge_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL,
    PRIMARY KEY (hyperedge_id, note_id),
    FOREIGN KEY (hyperedge_id) REFERENCES hyperedges(hyperedge_id),
    FOREIGN KEY (note_id) REFERENCES notes(note_id)
);

CREATE INDEX IF NOT EXISTS idx_notes_slug ON notes(slug);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_slug);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_slug);
CREATE INDEX IF NOT EXISTS idx_chunks_note ON chunks(note_id);
CREATE INDEX IF NOT EXISTS idx_hyperedge_members_note ON hyperedge_members(note_id);

-- Guardamos modelo e dimensão para consultas e re-ingestão
CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL
);
"""


def init_database(
    db_path: str,
    model_name: str | None = None,
    embedding_dim: int | None = None,
) -> duckdb.DuckDBPyConnection:
    """
    Cria o banco (ou conecta), instala a extensão VSS (vector similarity search)
    e cria todas as tabelas com a dimensão correta do embedding.
    """
    model_name = model_name or DEFAULT_MODEL
    if embedding_dim is None:
        embedding_dim = get_embedding_dim(model_name)
    if embedding_dim is None:
        raise ValueError(
            f"Modelo '{model_name}' não está em MODEL_CONFIGS. "
            "Use --embedding-dim N para especificar a dimensão."
        )

    conn = duckdb.connect(db_path)

    # VSS = Vector Similarity Search; HNSW = índice aproximado para cosine similarity
    conn.execute("INSTALL vss;")
    conn.execute("LOAD vss;")
    conn.execute("SET hnsw_enable_experimental_persistence = true;")

    schema_sql = get_schema_sql(embedding_dim, model_name)
    for stmt in schema_sql.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)

    conn.executemany(
        "INSERT INTO metadata (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        [("model_name", model_name), ("embedding_dim", str(embedding_dim))],
    )
    return conn


def create_hnsw_index(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Índice HNSW em embeddings(embedding) com métrica cosine.
    Acelera muito a busca por similaridade (nearest neighbor).
    """
    conn.execute("""
        CREATE INDEX IF NOT EXISTS embedding_cosine_idx
        ON embeddings USING HNSW (embedding)
        WITH (metric = 'cosine')
    """)


def drop_all_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Remove tabelas para re-ingestão limpa (ordem por FK)."""
    for table in ["hyperedge_members", "hyperedges", "embeddings", "chunks", "links", "notes", "metadata"]:
        conn.execute(f"DROP TABLE IF EXISTS {table};")
