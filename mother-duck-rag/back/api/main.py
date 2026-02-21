"""
FastAPI server for the RAG backend. Serves semantic search, backlinks, connections, hidden, chat.
Run from mother-duck-rag/back: uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""
import json
import os
import re
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACK_RAG_DIR = Path(__file__).resolve().parent.parent
QUERIES_DIR = BACK_RAG_DIR / "queries"
VAULTS_FILE = BACK_RAG_DIR / "vaults.json"

app = FastAPI(title="Back-RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_vaults() -> list[dict]:
    """Load vault registry; fallback to env-based default if missing."""
    if not VAULTS_FILE.exists():
        path = os.environ.get("VAULT_PATH", "")
        db = os.environ.get("DB_PATH", "second_brain.duckdb")
        if not Path(db).is_absolute():
            db = str(BACK_RAG_DIR / db)
        return [{"id": "default", "name": "Default", "vault_path": path, "db_path": db}]
    try:
        data = json.loads(VAULTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_vaults(vaults: list[dict]) -> None:
    VAULTS_FILE.write_text(json.dumps(vaults, indent=2), encoding="utf-8")


def get_vault(vault_id: str | None) -> dict | None:
    """Resolve vault by id; return first if vault_id is None. db_path is absolute."""
    vaults = load_vaults()
    if not vaults:
        return None
    if vault_id:
        for v in vaults:
            if v.get("id") == vault_id:
                out = dict(v)
                if not Path(out.get("db_path", "")).is_absolute():
                    out["db_path"] = str(BACK_RAG_DIR / out["db_path"])
                return out
    v = vaults[0]
    out = dict(v)
    if not Path(out.get("db_path", "")).is_absolute():
        out["db_path"] = str(BACK_RAG_DIR / out["db_path"])
    return out


def get_db_path(vault_id: str | None = None) -> str:
    v = get_vault(vault_id)
    if v:
        return v["db_path"]
    path = os.environ.get("DB_PATH", "second_brain.duckdb")
    if not Path(path).is_absolute():
        path = str(BACK_RAG_DIR / path)
    return path


def get_conn(vault_id: str | None = None):
    db_path = get_db_path(vault_id)
    if not Path(db_path).exists():
        raise HTTPException(status_code=503, detail="Database not found. Run ingest first.")
    return duckdb.connect(db_path, read_only=True)


def load_sql(name: str) -> str:
    p = QUERIES_DIR / f"{name}.sql"
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8").strip()


def get_db_meta(conn: duckdb.DuckDBPyConnection) -> tuple[str, int]:
    r = conn.execute(
        "SELECT key, value FROM metadata WHERE key IN ('model_name', 'embedding_dim')"
    ).fetchall()
    meta = dict(r)
    return meta.get("model_name", "all-MiniLM-L6-v2"), int(
        meta.get("embedding_dim", "384")
    )


@app.get("/api/vaults")
def list_vaults():
    """List registered vaults (id, name, vault_path)."""
    vaults = load_vaults()
    return [{"id": v["id"], "name": v["name"], "vault_path": v.get("vault_path", "")} for v in vaults]


class AddVaultRequest(BaseModel):
    name: str
    vault_path: str


@app.post("/api/vaults")
def add_vault(body: AddVaultRequest):
    """Register a new vault. vault_path must be an existing directory (absolute or relative)."""
    name = (body.name or "").strip()
    vault_path = (body.vault_path or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not vault_path:
        raise HTTPException(status_code=400, detail="vault_path is required")
    path = Path(vault_path)
    if not path.is_absolute():
        path = BACK_RAG_DIR / vault_path
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="vault_path is not an existing directory")
    vault_path_str = str(path.resolve())
    vaults = load_vaults()
    id_slug = re.sub(r"[^a-z0-9_-]", "-", name.lower())[:32].strip("-") or "vault"
    vid = id_slug
    n = 0
    while any(v.get("id") == vid for v in vaults):
        n += 1
        vid = f"{id_slug}-{n}"
    db_path = f"{vid}.duckdb"
    vaults.append({"id": vid, "name": name, "vault_path": vault_path_str, "db_path": db_path})
    save_vaults(vaults)
    return {"id": vid, "name": name, "vault_path": vault_path_str, "db_path": db_path}


@app.get("/api/notes")
def list_notes(vault: str | None = Query(None)):
    """List all notes with slug, title, source_*, tags for dropdowns and filters."""
    conn = get_conn(vault)
    try:
        rows = conn.execute(
            "SELECT slug, title, source_type, source_title, source_author, source_url, tags FROM notes ORDER BY title"
        ).fetchall()
        return [
            {
                "slug": r[0],
                "title": r[1] or r[0],
                "source_type": r[2],
                "source_title": r[3],
                "source_author": r[4],
                "source_url": r[5],
                "tags": list(r[6]) if r[6] is not None else [],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/semantic")
def semantic(q: str = "", limit: int = 10, vault: str | None = Query(None)):
    """Semantic search by query text."""
    conn = get_conn(vault)
    try:
        model_name, dim = get_db_meta(conn)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        query_vec = model.encode([q or " "], convert_to_numpy=True)[0].tolist()
        sql = load_sql("semantic_search")
        sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
        sql = sql.replace("$limit", str(int(limit)))
        rows = conn.execute(sql, [query_vec]).fetchall()
        cols = ["title", "slug", "file_path", "source_type", "source_title", "source_author", "content", "heading_context", "similarity"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


@app.get("/api/backlinks/{slug}")
def backlinks(slug: str, vault: str | None = Query(None)):
    """Backlinks to the given note slug."""
    conn = get_conn(vault)
    try:
        sql = load_sql("find_backlinks").replace("$slug", "?")
        rows = conn.execute(sql, [slug]).fetchall()
        return [{"source_slug": r[0], "link_text": r[1], "target_slug": r[2]} for r in rows]
    finally:
        conn.close()


@app.get("/api/connections/{slug}")
def connections(slug: str, hops: int = 2, vault: str | None = Query(None)):
    """Notes N hops away from the given slug."""
    conn = get_conn(vault)
    try:
        sql = load_sql("find_connections")
        sql = sql.replace("$seed_slug", "?")
        sql = sql.replace("$hops", str(int(hops)))
        rows = conn.execute(sql, [slug]).fetchall()
        return [{"slug": r[0], "hop": r[1]} for r in rows]
    finally:
        conn.close()


@app.get("/api/hidden")
def hidden(q: str = "", seed: str = "", limit: int = 10, vault: str | None = Query(None)):
    """Hidden connections: similar to q but not linked to seed."""
    conn = get_conn(vault)
    try:
        model_name, dim = get_db_meta(conn)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        query_vec = model.encode([q or " "], convert_to_numpy=True)[0].tolist()
        sql = load_sql("hidden_connections")
        sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
        sql = sql.replace("$seed_slug", "?")
        sql = sql.replace("$limit", str(int(limit)))
        rows = conn.execute(sql, [query_vec, seed, seed, seed]).fetchall()
        cols = ["title", "slug", "content", "similarity"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


@app.get("/api/graph")
def graph(vault: str | None = Query(None)):
    """Full graph: nodes (slug, title) and links (source_slug, target_slug) for the network view."""
    conn = get_conn(vault)
    try:
        notes = conn.execute("SELECT slug, title FROM notes").fetchall()
        link_rows = conn.execute(
            "SELECT source_slug, target_slug FROM links"
        ).fetchall()
        # Nodes: all notes; add any slug from links that might be missing (broken link)
        node_by_slug = {r[0]: {"id": r[0], "slug": r[0], "title": r[1] or r[0]} for r in notes}
        for src, tgt in link_rows:
            if src not in node_by_slug:
                node_by_slug[src] = {"id": src, "slug": src, "title": src}
            if tgt not in node_by_slug:
                node_by_slug[tgt] = {"id": tgt, "slug": tgt, "title": tgt}
        nodes = list(node_by_slug.values())
        links = [{"source": src, "target": tgt} for src, tgt in link_rows]
        return {"nodes": nodes, "links": links}
    finally:
        conn.close()


class ChatRequest(BaseModel):
    message: str
    vault: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]


def _retrieve_chunks(conn, query: str, limit: int = 8) -> list[dict]:
    """Run semantic search and return chunks with title, slug, content."""
    model_name, dim = get_db_meta(conn)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    query_vec = model.encode([query or " "], convert_to_numpy=True)[0].tolist()
    sql = load_sql("semantic_search")
    sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
    sql = sql.replace("$limit", str(int(limit)))
    rows = conn.execute(sql, [query_vec]).fetchall()
    cols = ["title", "slug", "file_path", "source_type", "source_title", "source_author", "content", "heading_context", "similarity"]
    return [dict(zip(cols, r)) for r in rows]


def _chat_impl(message: str, vault_id: str | None = None) -> dict:
    """RAG answer (retrieve + LLM). Returns {answer, citations} for use by chat endpoint and agent."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"answer": "OPENAI_API_KEY not set.", "citations": []}
    conn = get_conn(vault_id)
    try:
        chunks = _retrieve_chunks(conn, message.strip(), limit=8)
        if not chunks:
            return {"answer": "No relevant notes found.", "citations": []}
        context_parts = []
        for i, c in enumerate(chunks, 1):
            title = c.get("title") or c.get("slug", "")
            heading = c.get("heading_context") or ""
            content = (c.get("content") or "").strip()
            source_title = c.get("source_title")
            source_author = c.get("source_author")
            source_line = f"From: {source_title} ({source_author})" if (source_title or source_author) else ""
            context_parts.append(f"[{i}] Note: {title}\n{source_line}\nSection: {heading}\n{content}".strip())
        context = "\n\n---\n\n".join(context_parts)
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        system = (
            "You answer questions using only the provided excerpts from the user's notes. "
            "Be concise. When you use information from an excerpt, mention the note title in your answer. "
            "Do not make up facts; if the excerpts don't contain enough information, say so."
        )
        user_content = f"Relevant excerpts:\n\n{context}\n\n---\n\nQuestion: {message.strip()}"
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user_content}], max_tokens=1024)
        answer = (resp.choices[0].message.content or "").strip()
        citations = [
            {"title": c.get("title") or c.get("slug"), "slug": c.get("slug"), "source_title": c.get("source_title"), "source_author": c.get("source_author"), "snippet": (c.get("content") or "")[:200]}
            for c in chunks
        ]
        return {"answer": answer, "citations": citations}
    finally:
        conn.close()


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """Answer a question using RAG: retrieve relevant chunks, then LLM with citations."""
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set. Add it to .env for chat.")
    out = _chat_impl(body.message.strip(), body.vault)
    if not out.get("answer") and not out.get("citations"):
        out["answer"] = "I couldn't find any relevant notes. Try rephrasing or run ingest."
    return ChatResponse(answer=out["answer"], citations=out.get("citations", []))


class AgentRequest(BaseModel):
    task: str
    vault: str | None = None


class AgentStep(BaseModel):
    tool: str
    arguments: dict
    result_preview: str


class AgentResponse(BaseModel):
    answer: str
    steps: list[AgentStep]


def _web_research(query: str) -> dict | None:
    """Call Perplexity Sonar for web-grounded answer. Returns {answer, citations} or None if not configured."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return None
    base_url = (os.environ.get("PERPLEXITY_BASE_URL") or "https://api.perplexity.ai").rstrip("/")
    model = os.environ.get("PERPLEXITY_MODEL", "sonar")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            max_tokens=1024,
        )
        content = (resp.choices[0].message.content or "").strip()
        citations = getattr(resp.choices[0].message, "citations", None) or []
        return {"answer": content, "citations": citations}
    except Exception:
        return None


@app.get("/api/research")
def research(q: str = "", vault: str | None = Query(None)):
    """Web research (Perplexity) + vault notes for the same query. Returns { web, notes }."""
    web = None
    if q.strip():
        web = _web_research(q.strip())
    notes = []
    if q.strip():
        conn = get_conn(vault)
        try:
            model_name, dim = get_db_meta(conn)
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name)
            query_vec = model.encode([q or " "], convert_to_numpy=True)[0].tolist()
            sql = load_sql("semantic_search")
            sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
            sql = sql.replace("$limit", "8")
            rows = conn.execute(sql, [query_vec]).fetchall()
            cols = ["title", "slug", "file_path", "source_type", "source_title", "source_author", "content", "heading_context", "similarity"]
            notes = [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()
    return {"web": web, "notes": notes}


@app.post("/api/agent", response_model=AgentResponse)
def agent_endpoint(body: AgentRequest):
    """Run the AI agent: it can search notes, get backlinks/connections, find hidden gems, ask RAG, and web research. Returns final answer and tool steps."""
    if not body.task or not body.task.strip():
        raise HTTPException(status_code=400, detail="task is required")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set. Add it to .env for the agent.")
    from api.agent import run_agent
    vault_id = body.vault
    context = {
        "get_conn": lambda: get_conn(vault_id),
        "load_sql": load_sql,
        "get_db_meta": get_db_meta,
        "_retrieve_chunks": _retrieve_chunks,
        "_chat_impl": lambda msg: _chat_impl(msg, vault_id),
        "_web_research": _web_research,
    }
    result = run_agent(body.task.strip(), context)
    return AgentResponse(
        answer=result["answer"],
        steps=[AgentStep(tool=s["tool"], arguments=s["arguments"], result_preview=s["result_preview"]) for s in result["steps"]],
    )


@app.get("/api/health")
def health(vault: str | None = Query(None)):
    db_path = get_db_path(vault)
    return {"ok": True, "db_exists": Path(db_path).exists()}
