import { useState, useEffect } from "react";
import {
  fetchNotes,
  fetchGraph,
  fetchVaults,
  semanticSearch,
  backlinks,
  connections,
  hidden,
  chat,
  runAgent,
  research,
  health,
  type Note,
  type Vault,
  type SemanticHit,
  type BacklinkHit,
  type ConnectionHit,
  type HiddenHit,
  type GraphData,
  type GraphNode,
  type ChatCitation,
  type AgentStep,
  type ResearchWeb,
} from "./api";
import { GraphView } from "./GraphView";
import "./App.css";

type Mode = "graph" | "chat" | "agent" | "research" | "semantic" | "backlinks" | "connections" | "hidden";

type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; citations: ChatCitation[] };

function App() {
  const [mode, setMode] = useState<Mode>("graph");
  const [notes, setNotes] = useState<Note[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [query, setQuery] = useState("");
  const [seedSlug, setSeedSlug] = useState("");
  const [hops, setHops] = useState(2);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [semanticResults, setSemanticResults] = useState<SemanticHit[]>([]);
  const [backlinkResults, setBacklinkResults] = useState<BacklinkHit[]>([]);
  const [connectionResults, setConnectionResults] = useState<ConnectionHit[]>([]);
  const [hiddenResults, setHiddenResults] = useState<HiddenHit[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [agentTask, setAgentTask] = useState("");
  const [agentResult, setAgentResult] = useState<{ answer: string; steps: AgentStep[] } | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [researchQuery, setResearchQuery] = useState("");
  const [researchResult, setResearchResult] = useState<{ web: ResearchWeb; notes: SemanticHit[] } | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [vaults, setVaults] = useState<Vault[]>([]);
  const [selectedVaultId, setSelectedVaultId] = useState<string | null>(() =>
    typeof localStorage !== "undefined" ? localStorage.getItem("arc-lab-vault") : null
  );

  useEffect(() => {
    health(selectedVaultId)
      .then((h) => setApiOk(h.ok && h.db_exists))
      .catch(() => setApiOk(false));
  }, [selectedVaultId]);

  useEffect(() => {
    if (apiOk) {
      fetchVaults()
        .then(setVaults)
        .catch(() => setVaults([]));
    }
  }, [apiOk]);

  useEffect(() => {
    if (selectedVaultId != null && typeof localStorage !== "undefined") {
      localStorage.setItem("arc-lab-vault", selectedVaultId);
    }
  }, [selectedVaultId]);

  useEffect(() => {
    if (apiOk && vaults.length > 0) {
      if (!selectedVaultId || !vaults.some((v) => v.id === selectedVaultId)) {
        setSelectedVaultId(vaults[0].id);
      }
    }
  }, [apiOk, vaults, selectedVaultId]);

  useEffect(() => {
    if (apiOk && selectedVaultId) {
      fetchNotes(selectedVaultId)
        .then(setNotes)
        .catch(() => setNotes([]));
      fetchGraph(selectedVaultId)
        .then(setGraphData)
        .catch(() => setGraphData(null));
    }
  }, [apiOk, selectedVaultId]);

  const runSearch = async () => {
    setError(null);
    setLoading(true);
    try {
      if (mode === "semantic") {
        const res = await semanticSearch(query, limit, selectedVaultId);
        setSemanticResults(res);
        setBacklinkResults([]);
        setConnectionResults([]);
        setHiddenResults([]);
      } else if (mode === "backlinks" && seedSlug) {
        const res = await backlinks(seedSlug, selectedVaultId);
        setBacklinkResults(res);
        setSemanticResults([]);
        setConnectionResults([]);
        setHiddenResults([]);
      } else if (mode === "connections" && seedSlug) {
        const res = await connections(seedSlug, hops, selectedVaultId);
        setConnectionResults(res);
        setSemanticResults([]);
        setBacklinkResults([]);
        setHiddenResults([]);
      } else if (mode === "hidden" && seedSlug) {
        const res = await hidden(query, seedSlug, limit, selectedVaultId);
        setHiddenResults(res);
        setSemanticResults([]);
        setBacklinkResults([]);
        setConnectionResults([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGraphNodeClick = (node: GraphNode) => {
    setSeedSlug(node.slug ?? node.id);
    setMode("backlinks");
  };

  const sendChat = async () => {
    const msg = chatInput.trim();
    if (!msg || chatLoading) return;
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: msg }]);
    setChatLoading(true);
    setError(null);
    try {
      const res = await chat(msg, selectedVaultId);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, citations: res.citations },
      ]);
    } catch (e) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e instanceof Error ? e.message : String(e)}`, citations: [] },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const runAgentTask = async () => {
    const task = agentTask.trim();
    if (!task || agentLoading) return;
    setAgentLoading(true);
    setError(null);
    setAgentResult(null);
    try {
      const res = await runAgent(task, selectedVaultId);
      setAgentResult({ answer: res.answer, steps: res.steps });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAgentLoading(false);
    }
  };

  const runResearch = async () => {
    const q = researchQuery.trim();
    if (!q || researchLoading) return;
    setResearchLoading(true);
    setError(null);
    setResearchResult(null);
    try {
      const res = await research(q, selectedVaultId);
      setResearchResult({ web: res.web, notes: res.notes });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setResearchLoading(false);
    }
  };

  if (apiOk === null) {
    return (
      <div className="app">
        <div className="api-check">Checking API...</div>
      </div>
    );
  }
  if (apiOk === false) {
    return (
      <div className="app">
        <div className="api-error">
          <h1>Arc-Lab</h1>
          <p className="error">
            Backend not available. Start it with: <code>cd mother-duck-rag/back && make serve</code>
          </p>
          <p className="muted">Ensure the DB exists (run <code>make ingest</code> in mother-duck-rag/back first).</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-title">Arc-Lab</h1>
          <p className="sidebar-subtitle">RAG & graph over your vault</p>
        </div>
        <div className="nav-section vault-picker-section">
          <p className="nav-section-label">Vault</p>
          <select
            className="vault-select"
            value={selectedVaultId ?? ""}
            onChange={(e) => setSelectedVaultId(e.target.value || null)}
            title="Select vault"
          >
            {vaults.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        <nav className="nav-section">
          <p className="nav-section-label">Views</p>
          <button
            className={`nav-btn ${mode === "graph" ? "active" : ""}`}
            onClick={() => setMode("graph")}
            type="button"
          >
            <GraphIcon />
            Graph
          </button>
          <button
            className={`nav-btn ${mode === "chat" ? "active" : ""}`}
            onClick={() => setMode("chat")}
            type="button"
          >
            <ChatIcon />
            Ask (Q&A)
          </button>
          <button
            className={`nav-btn ${mode === "agent" ? "active" : ""}`}
            onClick={() => setMode("agent")}
            type="button"
          >
            <AgentIcon />
            Agent
          </button>
          <button
            className={`nav-btn ${mode === "research" ? "active" : ""}`}
            onClick={() => setMode("research")}
            type="button"
          >
            <ResearchIcon />
            Research
          </button>
          <button
            className={`nav-btn ${mode === "semantic" ? "active" : ""}`}
            onClick={() => setMode("semantic")}
            type="button"
          >
            <SearchIcon />
            Semantic search
          </button>
          <button
            className={`nav-btn ${mode === "backlinks" ? "active" : ""}`}
            onClick={() => setMode("backlinks")}
            type="button"
          >
            <BacklinkIcon />
            Backlinks
          </button>
          <button
            className={`nav-btn ${mode === "connections" ? "active" : ""}`}
            onClick={() => setMode("connections")}
            type="button"
          >
            <ConnectionsIcon />
            Connections
          </button>
          <button
            className={`nav-btn ${mode === "hidden" ? "active" : ""}`}
            onClick={() => setMode("hidden")}
            type="button"
          >
            <HiddenIcon />
            Hidden gems
          </button>
        </nav>
        <div className="nav-section">
          <p className="nav-section-label">Notes</p>
          <div className="notes-list">
            {notes.slice(0, 50).map((n) => (
              <button
                key={n.slug}
                type="button"
                className="nav-btn"
                onClick={() => {
                  setSeedSlug(n.slug);
                  setMode("backlinks");
                }}
              >
                {n.title || n.slug}
              </button>
            ))}
            {notes.length > 50 && <span className="muted">+{notes.length - 50} more</span>}
          </div>
        </div>
      </aside>

      <main className="main">
        {mode === "graph" && (
          <>
            <header className="main-header">
              <h2 className="main-title">Graph — wikilinks between notes</h2>
            </header>
            <GraphView data={graphData} onNodeClick={handleGraphNodeClick} />
          </>
        )}

        {mode === "agent" && (
          <>
            <header className="main-header">
              <h2 className="main-title">Agent — multi-step tasks over your vault</h2>
            </header>
            <section className="agent-pane">
              {error && mode === "agent" && <p className="error">{error}</p>}
              <p className="muted agent-desc">
                Give a task (e.g. &quot;What do I have on agentic AI and what notes link to RAG?&quot;). The agent can search, follow links, and ask the RAG.
              </p>
              <div className="chat-input-row">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Task for the agent..."
                  value={agentTask}
                  onChange={(e) => setAgentTask(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && runAgentTask()}
                  disabled={agentLoading}
                />
                <button type="button" className="primary chat-send" onClick={runAgentTask} disabled={agentLoading || !agentTask.trim()}>
                  {agentLoading ? "Running…" : "Run"}
                </button>
              </div>
              {agentResult && (
                <div className="agent-result">
                  {agentResult.steps.length > 0 && (
                    <details className="agent-steps">
                      <summary>Steps ({agentResult.steps.length})</summary>
                      <ul>
                        {agentResult.steps.map((s, i) => (
                          <li key={i}>
                            <strong>{s.tool}</strong>
                            <pre className="agent-step-args">{JSON.stringify(s.arguments, null, 2)}</pre>
                            <pre className="agent-step-preview">{s.result_preview}</pre>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <div className="agent-answer">
                    <h3>Answer</h3>
                    <div className="chat-msg-content">{agentResult.answer}</div>
                  </div>
                </div>
              )}
            </section>
          </>
        )}

        {mode === "research" && (
          <>
            <header className="main-header">
              <h2 className="main-title">Research — web (Perplexity) + your notes</h2>
            </header>
            <section className="research-pane">
              {error && mode === "research" && <p className="error">{error}</p>}
              <p className="muted agent-desc">
                One query: get a web answer (if PERPLEXITY_API_KEY is set) and matching notes from your vault.
              </p>
              <div className="chat-input-row">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Research topic or question..."
                  value={researchQuery}
                  onChange={(e) => setResearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && runResearch()}
                  disabled={researchLoading}
                />
                <button type="button" className="primary chat-send" onClick={runResearch} disabled={researchLoading || !researchQuery.trim()}>
                  {researchLoading ? "Searching…" : "Search"}
                </button>
              </div>
              {researchResult && (
                <div className="research-result">
                  {researchResult.web && (
                    <div className="research-block">
                      <h3>Web (Perplexity)</h3>
                      <div className="chat-msg-content">{researchResult.web.answer}</div>
                      {researchResult.web.citations?.length > 0 && (
                        <div className="chat-citations">
                          <span className="chat-citations-label">Sources:</span>
                          {researchResult.web.citations.map((c, i) => (
                            <a key={i} href={typeof c === "string" ? c : (c as { url?: string }).url} target="_blank" rel="noreferrer" className="chat-citation">
                              {typeof c === "string" ? c : (c as { title?: string }).title || "Link"}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {!researchResult.web && (
                    <p className="muted">Web research not configured (set PERPLEXITY_API_KEY) or failed.</p>
                  )}
                  <div className="research-block">
                    <h3>Your notes</h3>
                    {researchResult.notes.length === 0 ? (
                      <p className="muted">No matching notes.</p>
                    ) : (
                      <ul>
                        {researchResult.notes.map((r, i) => (
                          <li key={i}>
                            <strong>{r.title}</strong> ({r.slug}) — similarity {r.similarity.toFixed(3)}
                            <p className="snippet">{(r.content || "").slice(0, 200)}…</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </section>
          </>
        )}

        {mode === "chat" && (
          <>
            <header className="main-header">
              <h2 className="main-title">Ask — Q&A over your vault</h2>
            </header>
            <section className="chat-pane">
              <div className="chat-messages">
                {chatMessages.length === 0 && (
                  <p className="muted chat-placeholder">Ask anything about your notes. Answers are grounded in retrieved chunks.</p>
                )}
                {chatMessages.map((m, i) => (
                  <div key={i} className={`chat-msg chat-msg--${m.role}`}>
                    <div className="chat-msg-content">{m.content}</div>
                    {m.role === "assistant" && m.citations?.length > 0 && (
                      <div className="chat-citations">
                        <span className="chat-citations-label">Sources:</span>
                        {m.citations.map((c, j) => (
                          <span key={j} className="chat-citation" title={c.snippet}>
                            {c.source_title && c.source_author
                              ? `${c.source_title} (${c.source_author})`
                              : c.title}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-msg chat-msg--assistant">
                    <div className="chat-msg-content">Thinking…</div>
                  </div>
                )}
              </div>
              <div className="chat-input-row">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Ask a question about your vault..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendChat()}
                  disabled={chatLoading}
                />
                <button type="button" className="primary chat-send" onClick={sendChat} disabled={chatLoading || !chatInput.trim()}>
                  Send
                </button>
              </div>
            </section>
          </>
        )}

        {(mode === "semantic" || mode === "backlinks" || mode === "connections" || mode === "hidden") && (
          <>
            <header className="main-header">
              <h2 className="main-title">
                {mode === "semantic" && "Semantic search"}
                {mode === "backlinks" && "Backlinks"}
                {mode === "connections" && "Connections"}
                {mode === "hidden" && "Hidden gems"}
              </h2>
            </header>
            <section className="controls">
              {mode === "semantic" && (
                <>
                  <input
                    type="text"
                    placeholder="Search by meaning..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && runSearch()}
                  />
                  <label>Limit</label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  />
                </>
              )}
              {(mode === "backlinks" || mode === "connections" || mode === "hidden") && (
                <>
                  <label>Note</label>
                  <select value={seedSlug} onChange={(e) => setSeedSlug(e.target.value)}>
                    <option value="">Select note...</option>
                    {notes.map((n) => (
                      <option key={n.slug} value={n.slug}>
                        {n.title}
                      </option>
                    ))}
                  </select>
                </>
              )}
              {mode === "connections" && (
                <>
                  <label>Hops</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={hops}
                    onChange={(e) => setHops(Number(e.target.value))}
                  />
                </>
              )}
              {mode === "hidden" && (
                <>
                  <input
                    type="text"
                    placeholder="Topic to search..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <label>Limit</label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  />
                </>
              )}
              <button type="button" className="primary" onClick={runSearch} disabled={loading}>
                {loading ? "Loading..." : "Search"}
              </button>
            </section>

            {error && <div className="results-pane"><p className="error">{error}</p></div>}

            <section className="results-pane">
              {semanticResults.length > 0 && (
                <ul>
                  {semanticResults.map((r, i) => (
                    <li key={i}>
                      <strong>{r.title}</strong> ({r.slug}) — similarity {r.similarity.toFixed(3)}
                      <p className="snippet">{r.content?.slice(0, 200)}…</p>
                    </li>
                  ))}
                </ul>
              )}
              {backlinkResults.length > 0 && (
                <ul>
                  {backlinkResults.map((r, i) => (
                    <li key={i}>
                      <strong>{r.source_slug}</strong> → {r.target_slug} ({r.link_text})
                    </li>
                  ))}
                </ul>
              )}
              {connectionResults.length > 0 && (
                <ul>
                  {connectionResults.map((r, i) => (
                    <li key={i}>
                      <strong>{r.slug}</strong> (hop {r.hop})
                    </li>
                  ))}
                </ul>
              )}
              {hiddenResults.length > 0 && (
                <ul>
                  {hiddenResults.map((r, i) => (
                    <li key={i}>
                      <strong>{r.title}</strong> ({r.slug}) — similarity {r.similarity.toFixed(3)}
                      <p className="snippet">{r.content?.slice(0, 200)}…</p>
                    </li>
                  ))}
                </ul>
              )}
              {!loading &&
                semanticResults.length === 0 &&
                backlinkResults.length === 0 &&
                connectionResults.length === 0 &&
                hiddenResults.length === 0 &&
                (mode === "semantic" || mode === "hidden" ? query : seedSlug) && (
                  <p className="muted">No results.</p>
                )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function AgentIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function ResearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
      <path d="M8 12h6M12 8v8" />
    </svg>
  );
}

function GraphIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" />
      <circle cx="6" cy="8" r="2" />
      <circle cx="18" cy="8" r="2" />
      <circle cx="6" cy="16" r="2" />
      <circle cx="18" cy="16" r="2" />
      <path d="M8 9l4 3 4-3M8 15l4 3 4-3M12 12V9M12 15v-3" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

function BacklinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function ConnectionsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 20V10" />
      <path d="M12 20V4" />
      <path d="M6 20v-6" />
    </svg>
  );
}

function HiddenIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a12 12 0 0 0 8.5 3A12 12 0 0 1 12 21a12 12 0 0 1-8.5-3A12 12 0 0 0 12 3z" />
    </svg>
  );
}

export default App;
