# Entendendo o RAG de notas Obsidian (DuckDB + embeddings)

Este documento explica **como** o sistema funciona e **por que** cada peça existe.

---

## Visão geral

Seu vault vira **dois tipos de informação**: (1) um **grafo de links** entre notas (quem linka quem) e (2) **vetores de significado** (embeddings) de cada pedaço de texto. As consultas combinam esses dois mundos de formas diferentes.

---

## Os dois "mundos" de dados

### 1. Grafo (wikilinks)

- **Onde:** tabela `links`. Cada linha é uma aresta: `source_slug` → `target_slug`.
- **Origem:** o parser extrai `[[Alvo]]` ou `[[Alvo|texto]]`. O slug da nota atual vira `source_slug`; o alvo normalizado vira `target_slug`.
- **Uso:** backlinks, connections N hops, hidden connections (excluir o que já está linkado), graph-boosted.

### 2. Embeddings (significado)

- **Onde:** tabelas `chunks` e `embeddings`. Cada chunk tem um vetor de N números (ex.: 384 ou 1024).
- **Origem:** o texto é cortado em chunks (~512 caracteres); cada chunk (com contexto "Title: X | Section: Y") é passado ao modelo; a saída é o vetor.
- **Uso:** busca semântica = similaridade de cosseno entre o vetor da pergunta e os vetores dos chunks.

---

## Fluxo da ingestão

1. Listar todos os `.md` no vault.
2. **Parse:** frontmatter, título, slug, conteúdo.
3. **Links:** regex `[[...]]` → tabela `links`.
4. **Chunks:** quebrar por heading/parágrafo/código, ~512 chars, `heading_context`.
5. **Embeddings:** texto "Title: X | Section: Y | conteúdo" → modelo → vetor em `embeddings`.
6. **Hyperedges:** por tag no frontmatter.
7. **Índice HNSW** em `embeddings(embedding)` (cosine) para busca rápida.

---

## Tipos de consulta

| Consulta        | Grafo | Embeddings | O que faz |
|-----------------|-------|------------|-----------|
| **Backlinks**   | sim   | não        | Quais notas linkam para esta? |
| **Connections** | sim   | não        | Notas a N saltos de link. |
| **Semantic**    | não   | sim        | Chunks mais parecidos com o texto da busca. |
| **Hidden**      | sim   | sim        | Similares à busca que **não** estão linkados à nota semente. |

---

## Onde está cada coisa no código

- **Schema:** `src/database/schema.py`
- **Parse .md:** `src/parsers/markdown_parser.py`
- **Links:** `src/parsers/link_extractor.py`
- **Chunking:** `src/parsers/chunker.py`
- **Embeddings:** `src/embeddings/embedder.py`
- **Pipeline:** `src/database/ingestion.py`
- **Consultas:** `scripts/query.py` + `queries/*.sql`

---

## Referência

- [Building an Obsidian RAG with DuckDB and MotherDuck](https://motherduck.com/blog/obsidian-rag-duckdb-motherduck/)
- [sspaeti/obsidian-note-taking-assistant](https://github.com/sspaeti/obsidian-note-taking-assistant)
