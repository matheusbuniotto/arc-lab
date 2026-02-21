-- Hidden connections: similares à query que NÃO estão linkadas à nota semente.
WITH semantic_similar AS (
    SELECT DISTINCT
        n.slug,
        n.title,
        c.content,
        (1 - array_cosine_distance(e.embedding, $query_embedding)) AS similarity
    FROM embeddings e
    JOIN chunks c ON c.chunk_id = e.chunk_id
    JOIN notes n ON n.note_id = c.note_id
    WHERE n.slug != $seed_slug
),
direct_links AS (
    SELECT target_slug AS slug FROM links WHERE source_slug = $seed_slug
    UNION
    SELECT source_slug AS slug FROM links WHERE target_slug = $seed_slug
)
SELECT ss.title, ss.slug, ss.content, ss.similarity
FROM semantic_similar ss
LEFT JOIN direct_links dl ON ss.slug = dl.slug
WHERE dl.slug IS NULL
ORDER BY ss.similarity DESC
LIMIT $limit;
