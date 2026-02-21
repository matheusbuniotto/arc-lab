-- Backlinks: quais notas linkam PARA a nota dada (target_slug)?
SELECT source_slug, link_text, target_slug
FROM links
WHERE target_slug = $slug
ORDER BY source_slug;
