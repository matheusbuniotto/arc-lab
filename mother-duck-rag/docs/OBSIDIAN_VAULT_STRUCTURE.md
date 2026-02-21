# The Obsidian vault structure for projects, learning & AI

A single structure for **personal projects**, **learning** (books, courses, talks), and **AI** (RAG, graph, chat). Designed to work with Arc-Lab’s ingest: semantic search, graph, and Q&A use your folders, frontmatter, and links.

---

## Principles

1. **One place for everything** — projects, book notes, course notes, and evergreen notes live in one vault.
2. **Source = traceability** — every learning note knows *what* it came from (book, course, talk). The RAG can filter and cite by source.
3. **Tags = topics** — `#ai`, `#management`, `#soft-skills` etc. Filter search and chat by topic.
4. **Links = thinking** — use `[[wikilinks]]` to connect ideas. The graph and “backlinks” are built from these.
5. **MOCs = maps** — a few “Map of Content” notes tie clusters together and give you entry points.

---

## Folder structure

Keep it flat or use **one level** of folders by type. Avoid deep nesting.

```
vault/
├── _templates/           # Obsidian templates (optional)
├── 00-MOCs/              # Maps of content (hubs)
├── 01-Inbox/             # Fleeting notes, quick captures
├── 02-Learning/          # All learning content
│   ├── Books/
│   ├── Courses/
│   └── Talks/
├── 03-Projects/          # One folder per active project
└── 04-Slipbox/           # Permanent / evergreen notes (atomic ideas)
```

- **00-MOCs** — Notes like `AI.md`, `Leadership.md` that list and link to other notes. Your “home” pages.
- **01-Inbox** — Raw captures. Process into Learning or Slipbox when you have time.
- **02-Learning** — Books, courses, talks. One note per chapter/lesson/talk, or one per book with sections.
- **03-Projects** — One subfolder per project; inside: project overview note + linked notes.
- **04-Slipbox** — Atomic, evergreen notes. No “source”; they’re your own concepts, linked to learning notes.

You can start with just `02-Learning` and `04-Slipbox` and add the rest later.

---

## Naming conventions

- **Lowercase, hyphenated** for files: `agentic-ai-overview.md`, `crucial-conversations-summary.md`.
- **Consistent prefixes** (optional): e.g. `book-atomic-habits.md`, `course-ml-Andrew-Ng.md`, `talk-rewiring-ai-sam-altman.md`.
- **Slug = path without .md** — Arc-Lab uses this for links and the graph. So `02-Learning/Books/atomic-habits.md` → slug `02-Learning/Books/atomic-habits`.

---

## Frontmatter (source + tags)

Every note can have:

```yaml
---
title: "Your display title"
tags: [ai, generative-ai, habits]
source_type: book    # book | course | talk | project | permanent
source_title: "Atomic Habits"
source_author: "James Clear"
source_url: ""       # optional: purchase link, course URL, video URL
---
```

- **source_type** — Drives “From: book / course / talk” in RAG and filters.
  - `book` — Notes from a book (one note per chapter or one big note).
  - `course` — Online course (Coursera, Udemy, etc.); use `source_title` = course name, optional `source_author` = instructor.
  - `talk` — Conference talk, podcast, video; `source_url` = YouTube etc.
  - `project` — Note belongs to a project (optional: `source_title` = project name).
  - `permanent` or omit — Evergreen/slipbox note; no source.
- **source_title** — Name of the book, course, or talk.
- **source_author** — Author, instructor, or speaker.
- **source_url** — Link to the resource (optional).
- **tags** — Topic tags. Examples: `ai`, `generative-ai`, `ai-ops`, `agentic-ai`, `software`, `management`, `leadership`, `soft-skills`, `influence`, `productivity`.

Arc-Lab ingest reads these and stores them so you can filter search/chat by source and tag.

---

## Templates (copy into `_templates/` in Obsidian)

### Book note (one per chapter or one per book)

```yaml
---
title: "{{title}}"
tags: [{{tags}}]
source_type: book
source_title: "{{book_title}}"
source_author: "{{author}}"
source_url: ""
---
# {{title}}

> Key quotes and highlights.

## My take
Your summary and links to other notes, e.g. [[habit-stacking]].
```

### Course note (one per module/lesson)

```yaml
---
title: "{{title}}"
tags: [{{tags}}]
source_type: course
source_title: "{{course_name}}"
source_author: "{{instructor}}"
source_url: "{{course_link}}"
---
# {{title}}

## Summary
...

## Links
- [[related-note]]
```

### Talk / video note

```yaml
---
title: "{{title}}"
tags: [{{tags}}]
source_type: talk
source_title: "{{talk_title}}"
source_author: "{{speaker}}"
source_url: "{{video_url}}"
---
# {{title}}

## Summary
...

## Key quotes
...
```

### Project note

```yaml
---
title: "{{project_name}}"
tags: [project, {{topic_tags}}]
source_type: project
source_title: "{{project_name}}"
---
# {{project_name}}

## Goal
...

## Notes
- [[note-1]]
```

### Permanent / slipbox note (no source)

```yaml
---
title: "{{concept}}"
tags: [{{tags}}]
---
# {{concept}}

One idea, one note. Link to [[learning-note]] and [[other-concept]].
```

---

## Topic tags (suggested)

Use these (or your own) so filters and AI stay consistent:

| Area | Tags |
|------|------|
| AI | `ai`, `generative-ai`, `ai-ops`, `agentic-ai`, `llm`, `rag` |
| Software | `software`, `architecture`, `devops`, `product` |
| People & org | `management`, `leadership`, `soft-skills`, `influence`, `communication`, `productivity` |

Add more as you go; keep them lowercase, no spaces (use `-`).

---

## Linking rules

1. **Link to notes by name** — `[[atomic-habits-ch1]]` or `[[Habit stacking]]` (Obsidian resolves).
2. **Prefer one concept per note** in the Slipbox; link from learning notes to those concepts.
3. **MOCs** — In `00-MOCs/AI.md`, list and link: `- [[agentic-ai-overview]]`, `- [[llm-ops]]`. Gives you a “table of contents” and strong graph nodes.
4. **Backlinks** — When you link A → B, “backlinks” for B will show A. Use that in Arc-Lab to see what points to a note.

---

## How Arc-Lab uses this

- **Ingest** — Reads all `.md` files, frontmatter (`source_*`, `tags`), and `[[wikilinks]]`. Builds the graph and embeddings.
- **Semantic search** — Finds notes by meaning; you can later filter by `source_type` or `tags`.
- **Chat** — “What do my **books** say about X?” uses only notes with `source_type: book`.
- **Graph** — Nodes = notes; edges = wikilinks. Filter by tag or source in the UI.
- **Citations** — “From: *Atomic Habits* (James Clear)” comes from `source_title` and `source_author`.

---

## Quick start checklist

1. Create the folder structure (at least `02-Learning`, `04-Slipbox`).
2. Add `_templates/` and the templates above (optional).
3. Create one MOC, e.g. `00-MOCs/AI.md`, with a few links.
4. Add one book note and one slipbox note; link them.
5. Point Arc-Lab’s `VAULT_PATH` to this folder and run `make ingest`.
6. In the app: search, graph, and Ask (Q&A) over your vault.

You can grow into projects and inbox later; the same structure scales.
