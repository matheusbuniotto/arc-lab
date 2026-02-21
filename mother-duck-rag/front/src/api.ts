const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function vaultParam(vault: string | null | undefined): string {
  return vault ? `vault=${encodeURIComponent(vault)}` : "";
}
function vaultQuery(vault: string | null | undefined): string {
  return vaultParam(vault) ? `&${vaultParam(vault)}` : "";
}

export type Vault = { id: string; name: string; vault_path: string };

export async function fetchVaults(): Promise<Vault[]> {
  const r = await fetch(`${API}/api/vaults`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function addVault(name: string, vault_path: string): Promise<Vault & { db_path: string }> {
  const r = await fetch(`${API}/api/vaults`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, vault_path }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type Note = {
  slug: string;
  title: string;
  source_type?: string;
  source_title?: string;
  source_author?: string;
  source_url?: string;
  tags?: string[];
};
export type SemanticHit = {
  title: string;
  slug: string;
  file_path: string;
  content: string;
  heading_context: string;
  similarity: number;
  source_type?: string;
  source_title?: string;
  source_author?: string;
};
export type BacklinkHit = { source_slug: string; link_text: string; target_slug: string };
export type ConnectionHit = { slug: string; hop: number };
export type HiddenHit = { title: string; slug: string; content: string; similarity: number };

export type GraphNode = { id: string; slug: string; title: string };
export type GraphLink = { source: string; target: string };
export type GraphData = { nodes: GraphNode[]; links: GraphLink[] };

export async function fetchGraph(vault?: string | null): Promise<GraphData> {
  const r = await fetch(`${API}/api/graph${vaultParam(vault) ? "?" + vaultParam(vault) : ""}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchNotes(vault?: string | null): Promise<Note[]> {
  const r = await fetch(`${API}/api/notes${vaultParam(vault) ? "?" + vaultParam(vault) : ""}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function semanticSearch(q: string, limit = 10, vault?: string | null): Promise<SemanticHit[]> {
  const r = await fetch(`${API}/api/semantic?q=${encodeURIComponent(q)}&limit=${limit}${vaultQuery(vault)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function backlinks(slug: string, vault?: string | null): Promise<BacklinkHit[]> {
  const r = await fetch(`${API}/api/backlinks/${encodeURIComponent(slug)}${vaultParam(vault) ? "?" + vaultParam(vault) : ""}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function connections(slug: string, hops = 2, vault?: string | null): Promise<ConnectionHit[]> {
  const r = await fetch(`${API}/api/connections/${encodeURIComponent(slug)}?hops=${hops}${vaultQuery(vault)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function hidden(q: string, seed: string, limit = 10, vault?: string | null): Promise<HiddenHit[]> {
  const r = await fetch(
    `${API}/api/hidden?q=${encodeURIComponent(q)}&seed=${encodeURIComponent(seed)}&limit=${limit}${vaultQuery(vault)}`
  );
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type ChatCitation = {
  title: string;
  slug: string;
  snippet: string;
  source_title?: string;
  source_author?: string;
};
export type ChatResponse = { answer: string; citations: ChatCitation[] };

export async function chat(message: string, vault?: string | null): Promise<ChatResponse> {
  const r = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, vault: vault || undefined }),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `Chat failed: ${r.status}`);
  }
  return r.json();
}

export type AgentStep = { tool: string; arguments: Record<string, unknown>; result_preview: string };
export type AgentResponse = { answer: string; steps: AgentStep[] };

export async function runAgent(task: string, vault?: string | null): Promise<AgentResponse> {
  const r = await fetch(`${API}/api/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, vault: vault || undefined }),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `Agent failed: ${r.status}`);
  }
  return r.json();
}

export type ResearchWeb = { answer: string; citations: string[] } | null;
export type ResearchNotes = SemanticHit[];

export async function research(query: string, vault?: string | null): Promise<{ web: ResearchWeb; notes: ResearchNotes }> {
  const r = await fetch(`${API}/api/research?q=${encodeURIComponent(query)}${vaultQuery(vault)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function health(vault?: string | null): Promise<{ ok: boolean; db_exists: boolean }> {
  const r = await fetch(`${API}/api/health${vaultParam(vault) ? "?" + vaultParam(vault) : ""}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
