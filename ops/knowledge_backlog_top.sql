-- Knowledge backlog top misses (last N days)
-- Usage:
--   psql -U $DB_USER -d chatbot -v client_slug=demo_salon -f ops/knowledge_backlog_top.sql
--
-- Defaults:
--   client_slug = demo_salon
--   days = 7
--   limit = 20

\if :{?client_slug}
\else
\set client_slug 'demo_salon'
\endif
\if :{?days}
\else
\set days '7'
\endif
\if :{?limit}
\else
\set limit '20'
\endif

SELECT
  kb.miss_type,
  kb.user_text,
  kb.language,
  kb.repeat_count,
  kb.first_seen_at,
  kb.last_seen_at
FROM knowledge_backlog kb
JOIN clients c ON c.id = kb.client_id
WHERE c.name = :'client_slug'
  AND kb.last_seen_at >= (NOW() - (:'days'::int * INTERVAL '1 day'))
ORDER BY kb.repeat_count DESC, kb.last_seen_at DESC
LIMIT :'limit'::int;
