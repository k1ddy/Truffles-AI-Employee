-- Daily metrics snapshot
-- Usage:
--   psql -U $DB_USER -d chatbot -v client_slug=demo_salon -v metric_date='2025-12-27' -f ops/metrics_daily_snapshot.sql
--
-- Defaults:
--   client_slug = demo_salon
--   metric_date = yesterday (UTC)

\if :{?client_slug}
\else
\set client_slug 'demo_salon'
\endif
\if :{?metric_date}
\else
\set metric_date ''
\endif

WITH params AS (
  SELECT
    (SELECT id FROM clients WHERE name = :'client_slug') AS client_id,
    COALESCE(NULLIF(:'metric_date', '')::date, (CURRENT_DATE - INTERVAL '1 day')::date) AS metric_date
),
bounds AS (
  SELECT
    client_id,
    metric_date,
    metric_date::timestamp AT TIME ZONE 'UTC' AS start_ts,
    (metric_date + 1)::timestamp AT TIME ZONE 'UTC' AS end_ts
  FROM params
),
user_messages AS (
  SELECT
    COUNT(*) AS total_user_messages,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'decision_meta'->>'fast_intent')::boolean, FALSE) THEN 1
        ELSE 0
      END
    ) AS total_fast_intent,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'decision_meta'->>'llm_used')::boolean, FALSE) THEN 1
        ELSE 0
      END
    ) AS total_llm_used,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'decision_meta'->>'llm_timeout')::boolean, FALSE) THEN 1
        ELSE 0
      END
    ) AS total_llm_timeout,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'asr'->>'asr_used')::boolean, FALSE) THEN 1
        ELSE 0
      END
    ) AS total_asr_used,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'asr'->>'asr_failed')::boolean, FALSE) THEN 1
        ELSE 0
      END
    ) AS total_asr_failed
  FROM messages m
  JOIN bounds b ON m.client_id = b.client_id
  WHERE m.role = 'user'
    AND m.created_at >= b.start_ts
    AND m.created_at < b.end_ts
),
handovers_day AS (
  SELECT COUNT(*) AS total_handovers
  FROM handovers h
  JOIN bounds b ON h.client_id = b.client_id
  WHERE h.created_at >= b.start_ts
    AND h.created_at < b.end_ts
),
outbox_sent AS (
  SELECT
    COUNT(*) AS total_outbox_sent,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (o.updated_at - o.created_at))) AS outbox_p50,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (o.updated_at - o.created_at))) AS outbox_p90
  FROM outbox_messages o
  JOIN bounds b ON o.client_id = b.client_id
  WHERE o.status = 'SENT'
    AND o.created_at >= b.start_ts
    AND o.created_at < b.end_ts
),
outbox_failed AS (
  SELECT COUNT(*) AS total_outbox_failed
  FROM outbox_messages o
  JOIN bounds b ON o.client_id = b.client_id
  WHERE o.status = 'FAILED'
    AND o.created_at >= b.start_ts
    AND o.created_at < b.end_ts
)
INSERT INTO metrics_daily (
  metric_date,
  client_id,
  outbox_latency_p50,
  outbox_latency_p90,
  llm_timeout_rate,
  llm_used_rate,
  escalation_rate,
  fast_intent_rate,
  asr_fail_rate,
  total_user_messages,
  total_outbox_sent,
  total_outbox_failed,
  total_llm_used,
  total_llm_timeout,
  total_handovers,
  total_fast_intent,
  total_asr_used,
  total_asr_failed,
  created_at,
  updated_at
)
SELECT
  b.metric_date,
  b.client_id,
  ROUND(os.outbox_p50::numeric, 2),
  ROUND(os.outbox_p90::numeric, 2),
  COALESCE(ROUND(um.total_llm_timeout::numeric / NULLIF(um.total_llm_used, 0), 4), 0),
  COALESCE(ROUND(um.total_llm_used::numeric / NULLIF(um.total_user_messages, 0), 4), 0),
  COALESCE(ROUND(h.total_handovers::numeric / NULLIF(um.total_user_messages, 0), 4), 0),
  COALESCE(ROUND(um.total_fast_intent::numeric / NULLIF(um.total_user_messages, 0), 4), 0),
  COALESCE(ROUND(um.total_asr_failed::numeric / NULLIF(um.total_asr_used, 0), 4), 0),
  COALESCE(um.total_user_messages, 0),
  COALESCE(os.total_outbox_sent, 0),
  COALESCE(ofx.total_outbox_failed, 0),
  COALESCE(um.total_llm_used, 0),
  COALESCE(um.total_llm_timeout, 0),
  COALESCE(h.total_handovers, 0),
  COALESCE(um.total_fast_intent, 0),
  COALESCE(um.total_asr_used, 0),
  COALESCE(um.total_asr_failed, 0),
  NOW(),
  NOW()
FROM bounds b
LEFT JOIN user_messages um ON TRUE
LEFT JOIN handovers_day h ON TRUE
LEFT JOIN outbox_sent os ON TRUE
LEFT JOIN outbox_failed ofx ON TRUE
ON CONFLICT (metric_date, client_id) DO UPDATE SET
  outbox_latency_p50 = EXCLUDED.outbox_latency_p50,
  outbox_latency_p90 = EXCLUDED.outbox_latency_p90,
  llm_timeout_rate = EXCLUDED.llm_timeout_rate,
  llm_used_rate = EXCLUDED.llm_used_rate,
  escalation_rate = EXCLUDED.escalation_rate,
  fast_intent_rate = EXCLUDED.fast_intent_rate,
  total_user_messages = EXCLUDED.total_user_messages,
  total_outbox_sent = EXCLUDED.total_outbox_sent,
  total_outbox_failed = EXCLUDED.total_outbox_failed,
  total_llm_used = EXCLUDED.total_llm_used,
  total_llm_timeout = EXCLUDED.total_llm_timeout,
  total_handovers = EXCLUDED.total_handovers,
  total_fast_intent = EXCLUDED.total_fast_intent,
  updated_at = NOW();
