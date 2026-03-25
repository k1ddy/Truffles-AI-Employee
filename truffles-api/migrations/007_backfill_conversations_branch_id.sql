-- Backfill conversations.branch_id from inbound instanceId (unambiguous only).
WITH instanced AS (
    SELECT
        c.id AS conversation_id,
        c.client_id,
        COUNT(DISTINCT m.metadata->>'instanceId') AS instance_count,
        MIN(m.metadata->>'instanceId') AS instance_id
    FROM conversations c
    JOIN messages m ON m.conversation_id = c.id
    WHERE c.branch_id IS NULL
      AND m.role = 'user'
      AND m.metadata->>'instanceId' IS NOT NULL
    GROUP BY c.id, c.client_id
),
eligible AS (
    SELECT conversation_id, client_id, instance_id
    FROM instanced
    WHERE instance_count = 1
)
UPDATE conversations c
SET branch_id = b.id
FROM eligible e
JOIN branches b
  ON b.instance_id = e.instance_id
 AND b.client_id = e.client_id
WHERE c.id = e.conversation_id
  AND c.branch_id IS NULL;

-- Fallback: if client has exactly one branch, assign it to legacy conversations.
WITH single_branch_clients AS (
    SELECT client_id, MIN(id::text)::uuid AS branch_id, COUNT(*) AS branch_count
    FROM branches
    GROUP BY client_id
    HAVING COUNT(*) = 1
)
UPDATE conversations c
SET branch_id = sb.branch_id
FROM single_branch_clients sb
WHERE c.client_id = sb.client_id
  AND c.branch_id IS NULL;
