"""
Extração de wikilinks no estilo Obsidian: [[Alvo]], [[Alvo|texto]], [[Alvo#seção]].

Cada link vira uma aresta no grafo: (slug_da_nota_atual, slug_do_alvo).
"""
import re

WIKILINK_RE = re.compile(
    r"\[\["
    r"([^\]|#]+)"
    r"(?:\|[^\]]*)?"
    r"(?:#[^\]]*)?"
    r"\]\]",
    re.IGNORECASE,
)


def link_text_to_slug(text: str) -> str:
    """Converte 'Título da Nota' em slug 'titulo-da-nota'."""
    return text.strip().lower().replace(" ", "-").replace("_", "-")


def extract_wikilinks(content: str) -> list[dict]:
    """Retorna lista de dicts com target_slug e link_text."""
    links = []
    for m in WIKILINK_RE.finditer(content):
        target = m.group(1).strip()
        if not target:
            continue
        if "/" in target:
            target_slug = "/".join(link_text_to_slug(p) for p in target.split("/"))
        else:
            target_slug = link_text_to_slug(target)
        full_match = m.group(0)
        if "|" in full_match:
            link_text = full_match.split("|", 1)[1].rstrip("]").strip()
        else:
            link_text = target.strip()
        links.append({"target_slug": target_slug, "link_text": link_text})
    return links


def extract_links_from_note(content: str, source_slug: str) -> list[dict]:
    """Retorna lista de arestas para inserir em links."""
    edges = []
    for info in extract_wikilinks(content):
        edges.append({
            "source_slug": source_slug,
            "target_slug": info["target_slug"],
            "link_text": info["link_text"],
        })
    return edges
