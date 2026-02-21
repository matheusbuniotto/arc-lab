"""
Parser de arquivos Markdown no estilo Obsidian.

Lê um .md do disco e extrai:
- frontmatter (YAML entre --- no topo): tags, title, aliases, datas, etc.
- título da nota (primeiro # ou nome do arquivo)
- conteúdo bruto (para chunking e para extrair links)

O "slug" é o identificador único da nota: normalmente o path do arquivo
sem extensão, ou um alias do frontmatter. Usamos para o grafo de links.
"""
import re
from pathlib import Path
from typing import Any

import yaml


def slug_from_path(file_path: Path, vault_root: Path) -> str:
    """
    Gera o slug a partir do caminho relativo ao vault.
    """
    try:
        rel = file_path.relative_to(vault_root)
    except ValueError:
        rel = file_path
    return str(rel.with_suffix("")).replace("\\", "/")


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Separa frontmatter (YAML entre ---) do resto do conteúdo.
    Retorna (dict do frontmatter, corpo do markdown).
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        fm = {}
    return fm, parts[2].lstrip("\n")


def parse_title_from_body(body: str) -> str | None:
    """Primeiro heading de nível 1 (# Título) no corpo."""
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else None


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Tags no frontmatter podem vir como '#tag' ou 'tag'; normalizamos para 'tag'."""
    if not tags:
        return []
    return [t.lstrip("#").strip() for t in tags if t and isinstance(t, str)]


def parse_note_file(file_path: Path, vault_root: Path) -> dict[str, Any]:
    """
    Lê um arquivo .md e retorna um dicionário com:
    - file_path, slug, title, content, frontmatter, tags, aliases, etc.
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(text)
    slug = slug_from_path(file_path, vault_root)
    title = (
        frontmatter.get("title")
        or parse_title_from_body(body)
        or file_path.stem
    )
    if isinstance(title, list):
        title = title[0] if title else file_path.stem
    tags = normalize_tags(
        frontmatter.get("tags")
        if isinstance(frontmatter.get("tags"), list)
        else [frontmatter["tags"]] if frontmatter.get("tags") else []
    )
    aliases = frontmatter.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]

    source_type = frontmatter.get("source_type")
    if source_type and not isinstance(source_type, str):
        source_type = None
    source_title = frontmatter.get("source_title")
    if source_title is not None and not isinstance(source_title, str):
        source_title = str(source_title)
    source_author = frontmatter.get("source_author")
    if source_author is not None and not isinstance(source_author, str):
        source_author = str(source_author)
    source_url = frontmatter.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        source_url = str(source_url)

    return {
        "file_path": str(file_path),
        "slug": slug,
        "title": title,
        "content": body,
        "frontmatter": frontmatter,
        "tags": tags,
        "aliases": aliases,
        "source_type": source_type,
        "source_title": source_title,
        "source_author": source_author,
        "source_url": source_url,
        "word_count": len(body.split()),
    }
