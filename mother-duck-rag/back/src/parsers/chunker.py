"""
Chunking markdown-aware: corta o texto em pedaços (~max_chars) respeitando
headings e parágrafos, sem quebrar blocos de código.
"""
import re
from dataclasses import dataclass

DEFAULT_MAX_CHARS = 512


@dataclass
class Chunk:
    content: str
    heading_context: str
    chunk_type: str
    start_line: int
    end_line: int


def _split_into_blocks(lines: list[str]) -> list[tuple[str, str, str, int, int]]:
    blocks = []
    current_heading = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            code_lines = [line]
            start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                code_lines.append(lines[i])
                i += 1
            content = "\n".join(code_lines)
            blocks.append((content, current_heading, "code", start + 1, i))
            continue
        if line.strip().startswith("#"):
            current_heading = line.strip().lstrip("#").strip()
            blocks.append((line, current_heading, "heading", i + 1, i + 1))
            i += 1
            continue
        para_lines = []
        start = i
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#") and not lines[i].strip().startswith("```"):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            content = "\n".join(para_lines)
            blocks.append((content, current_heading, "paragraph", start + 1, start + len(para_lines)))
        while i < len(lines) and not lines[i].strip():
            i += 1
    return blocks


def chunk_note(
    content: str,
    title: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[Chunk]:
    """Quebra o conteúdo da nota em chunks de até max_chars caracteres."""
    lines = content.split("\n")
    blocks = _split_into_blocks(lines)
    chunks = []
    for block_content, heading_ctx, block_type, start_line, end_line in blocks:
        if len(block_content) <= max_chars:
            chunks.append(Chunk(
                content=block_content,
                heading_context=heading_ctx,
                chunk_type=block_type,
                start_line=start_line,
                end_line=end_line,
            ))
        else:
            if block_type == "code":
                chunks.append(Chunk(block_content, heading_ctx, block_type, start_line, end_line))
            else:
                parts = re.split(r"\n\s*\n", block_content)
                offset = 0
                for part in parts:
                    if not part.strip():
                        continue
                    if len(part) <= max_chars:
                        chunks.append(Chunk(part, heading_ctx, "paragraph", start_line + offset, start_line + offset))
                        offset += part.count("\n") + 1
                    else:
                        rest = part
                        while rest:
                            take = rest[:max_chars]
                            last_nl = take.rfind("\n")
                            if last_nl > max_chars // 2:
                                take = take[: last_nl + 1]
                                rest = rest[len(take):]
                            else:
                                rest = rest[max_chars:]
                            chunks.append(Chunk(take.strip(), heading_ctx, "paragraph", start_line + offset, start_line + offset))
                            offset += take.count("\n") + 1
    return chunks


def chunk_text_for_embedding(chunk: Chunk, note_title: str) -> str:
    """Texto final que será enviado ao modelo de embedding (Title | Section | content)."""
    parts = []
    if note_title:
        parts.append(f"Title: {note_title}")
    if chunk.heading_context:
        parts.append(f"Section: {chunk.heading_context}")
    parts.append(chunk.content)
    return " | ".join(parts)
