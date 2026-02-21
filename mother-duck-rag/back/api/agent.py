"""
AI agent that uses the vault RAG and graph as tools (OpenAI function calling).
Run via POST /api/agent with {"task": "..."}.
"""
import json
import os
from typing import Any

# Lazy import to avoid loading heavy deps at module load
def _get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return OpenAI(api_key=api_key, base_url=base_url)


# Tool definitions for OpenAI function calling
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Semantic search over the vault. Find notes by meaning (e.g. 'agentic AI', 'habit stacking').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (natural language)"},
                    "limit": {"type": "integer", "description": "Max results (default 8)", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List all notes in the vault (slug, title, source_type, tags). Use to see what exists.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_backlinks",
            "description": "Get notes that link TO the given note (backlinks). Slug is the note id (path without .md).",
            "parameters": {
                "type": "object",
                "properties": {"slug": {"type": "string", "description": "Note slug (e.g. '04-Slipbox/rag-pattern')"}},
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_connections",
            "description": "Get notes within N hops of a note in the link graph (neighbors, then their neighbors).",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Note slug"},
                    "hops": {"type": "integer", "description": "Max graph distance (1 or 2)", "default": 2},
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_hidden_gems",
            "description": "Find notes semantically similar to a topic that are NOT directly linked to a seed note. Good for 'notes I might have missed' or 'suggest links'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic to search for"},
                    "seed_slug": {"type": "string", "description": "Note slug to exclude direct links from"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query", "seed_slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_rag",
            "description": "Ask a direct question and get an answer grounded in retrieved note chunks (RAG). Use for 'what do my notes say about X?'.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "The question"}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_research",
            "description": "Search the web for current information (Perplexity). Use for recent events, definitions, or to compare with the user's notes. Returns an answer with web sources.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search/research query (e.g. 'latest on agentic AI 2025', 'RAG best practices')"}},
                "required": ["query"],
            },
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any], context: dict) -> str:
    """
    Execute one agent tool. context must have: get_conn, load_sql, get_db_meta, _retrieve_chunks, _chat_impl (for ask_rag).
    Returns JSON string of the result (for the LLM).
    """
    conn_factory = context["get_conn"]
    load_sql = context["load_sql"]
    get_db_meta = context["get_db_meta"]
    retrieve_chunks = context["_retrieve_chunks"]
    chat_impl = context.get("_chat_impl")

    try:
        if name == "list_notes":
            conn = conn_factory()
            try:
                rows = conn.execute(
                    "SELECT slug, title, source_type, source_title, source_author, source_url, tags FROM notes ORDER BY title"
                ).fetchall()
                out = [
                    {"slug": r[0], "title": r[1] or r[0], "source_type": r[2], "source_title": r[3], "tags": list(r[6]) if r[6] else []}
                    for r in rows
                ]
                return json.dumps(out, ensure_ascii=False)[:8000]
            finally:
                conn.close()

        if name == "search_notes":
            q = (arguments.get("query") or "").strip()
            limit = int(arguments.get("limit") or 8)
            conn = conn_factory()
            try:
                model_name, dim = get_db_meta(conn)
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name)
                query_vec = model.encode([q or " "], convert_to_numpy=True)[0].tolist()
                sql = load_sql("semantic_search")
                sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
                sql = sql.replace("$limit", str(limit))
                rows = conn.execute(sql, [query_vec]).fetchall()
                cols = ["title", "slug", "source_type", "source_title", "source_author", "content", "heading_context", "similarity"]
                out = [dict(zip(cols, r)) for r in rows]
                for o in out:
                    if o.get("content"):
                        o["content"] = (o["content"] or "")[:500]
                return json.dumps(out, ensure_ascii=False)[:12000]
            finally:
                conn.close()

        if name == "get_backlinks":
            slug = (arguments.get("slug") or "").strip()
            conn = conn_factory()
            try:
                sql = load_sql("find_backlinks").replace("$slug", "?")
                rows = conn.execute(sql, [slug]).fetchall()
                out = [{"source_slug": r[0], "link_text": r[1], "target_slug": r[2]} for r in rows]
                return json.dumps(out, ensure_ascii=False)
            finally:
                conn.close()

        if name == "get_connections":
            slug = (arguments.get("slug") or "").strip()
            hops = int(arguments.get("hops") or 2)
            conn = conn_factory()
            try:
                sql = load_sql("find_connections")
                sql = sql.replace("$seed_slug", "?")
                sql = sql.replace("$hops", str(hops))
                rows = conn.execute(sql, [slug]).fetchall()
                out = [{"slug": r[0], "hop": r[1]} for r in rows]
                return json.dumps(out, ensure_ascii=False)
            finally:
                conn.close()

        if name == "find_hidden_gems":
            q = (arguments.get("query") or "").strip()
            seed = (arguments.get("seed_slug") or "").strip()
            limit = int(arguments.get("limit") or 5)
            conn = conn_factory()
            try:
                model_name, dim = get_db_meta(conn)
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name)
                query_vec = model.encode([q or " "], convert_to_numpy=True)[0].tolist()
                sql = load_sql("hidden_connections")
                sql = sql.replace("$query_embedding", f"CAST(? AS FLOAT[{dim}])")
                sql = sql.replace("$seed_slug", "?")
                sql = sql.replace("$limit", str(limit))
                rows = conn.execute(sql, [query_vec, seed, seed, seed]).fetchall()
                cols = ["title", "slug", "content", "similarity"]
                out = [dict(zip(cols, r)) for r in rows]
                return json.dumps(out, ensure_ascii=False)[:8000]
            finally:
                conn.close()

        if name == "ask_rag":
            msg = (arguments.get("message") or "").strip()
            if not msg:
                return json.dumps({"error": "message is required"})
            if not chat_impl:
                return json.dumps({"error": "RAG not available"})
            result = chat_impl(msg)
            return json.dumps({"answer": result.get("answer", ""), "citations": result.get("citations", [])}, ensure_ascii=False)[:6000]

        if name == "web_research":
            web_impl = context.get("_web_research")
            if not web_impl:
                return json.dumps({"error": "Web research not configured. Set PERPLEXITY_API_KEY in .env."})
            q = (arguments.get("query") or "").strip()
            if not q:
                return json.dumps({"error": "query is required"})
            result = web_impl(q)
            return json.dumps(result, ensure_ascii=False)[:8000]

        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_agent(task: str, context: dict, max_steps: int = 15) -> dict:
    """
    Run the agent loop: LLM with tools until it returns a final answer or max_steps.
    Returns {"answer": str, "steps": [{"tool": str, "arguments": dict, "result_preview": str}]}.
    """
    client = _get_openai_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system = (
        "You are an AI assistant with access to the user's Obsidian vault (notes, links, semantic search) and optional web research (Perplexity). "
        "Use the tools to find information, then answer the user's task. Be concise. "
        "Use search_notes or ask_rag for the user's own notes; use web_research for current or external info (definitions, recent events, best practices). "
        "When suggesting links or notes, use exact slugs from the results. After you have enough information, respond with your final answer without calling more tools."
    )
    messages = [{"role": "user", "content": task}]
    steps = []

    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}] + messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )
        choice = resp.choices[0]
        msg = choice.message

        if not getattr(msg, "tool_calls", None) or len(msg.tool_calls) == 0:
            answer = (msg.content or "").strip()
            return {"answer": answer or "I couldn't produce an answer.", "steps": steps}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            f = tc.function
            name = f.name
            try:
                args = json.loads(f.arguments) if isinstance(f.arguments, str) else f.arguments
            except json.JSONDecodeError:
                args = {}
            result = run_tool(name, args, context)
            preview = result[:400] + "..." if len(result) > 400 else result
            steps.append({"tool": name, "arguments": args, "result_preview": preview})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    answer = "Reached max steps without a final reply. Try a simpler task or check the steps above."
    return {"answer": answer, "steps": steps}
