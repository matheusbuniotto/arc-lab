-- Conexões a N saltos a partir de um slug (CTE recursivo).
WITH RECURSIVE connected AS (
    SELECT target_slug AS slug, 1 AS hop
    FROM links
    WHERE source_slug = $seed_slug
    UNION
    SELECT l.target_slug, c.hop + 1
    FROM connected c
    JOIN links l ON l.source_slug = c.slug
    WHERE c.hop < $hops
)
SELECT DISTINCT slug, hop FROM connected ORDER BY hop, slug;
