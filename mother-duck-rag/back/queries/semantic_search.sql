-- Busca semântica: ordenar chunks por similaridade de cosseno ao vetor da query.
SELECT DISTINCT
    n.title,
    n.slug,
    n.file_path,
    n.source_type,
    n.source_title,
    n.source_author,
    c.content,
    c.heading_context,
    1 - array_cosine_distance(e.embedding, $query_embedding) AS similarity
FROM embeddings e
JOIN chunks c ON c.chunk_id = e.chunk_id
JOIN notes n ON n.note_id = c.note_id
ORDER BY similarity DESC
LIMIT $limit;
