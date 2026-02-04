from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client

logger = get_logger(__name__)

_DEFAULT_STATUS_ALLOWLIST = ("active",)
_DEFAULT_BACKFILL_MAX_DAYS = 31

_METRICS_DAILY_SQL = """
WITH params AS (
  SELECT
    CAST(:client_id AS uuid) AS client_id,
    CAST(:metric_date AS date) AS metric_date
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
    ) AS total_asr_failed,
    SUM(
      CASE
        WHEN COALESCE((m.metadata->'decision_meta'->>'rag_confident')::boolean, FALSE) = FALSE
          AND (m.metadata->'decision_meta'->>'rag_reason') IN ('low_score', 'empty')
          THEN 1
        ELSE 0
      END
    ) AS total_rag_low_conf,
    SUM(
      CASE
        WHEN NULLIF(m.metadata->'decision_meta'->>'clarify_reason', '') IS NOT NULL
          OR COALESCE((m.metadata->'decision_meta'->>'clarify_limit')::boolean, FALSE)
          THEN 1
        ELSE 0
      END
    ) AS total_clarify,
    SUM(
      CASE
        WHEN NULLIF(m.metadata->'decision_meta'->>'clarify_reason', '') IS NOT NULL
          AND NOT COALESCE((m.metadata->'decision_meta'->>'clarify_limit')::boolean, FALSE)
          THEN 1
        ELSE 0
      END
    ) AS total_clarify_success
  FROM messages m
  JOIN bounds b ON m.client_id = b.client_id
  WHERE m.role = 'user'
    AND m.created_at >= b.start_ts
    AND m.created_at < b.end_ts
    AND COALESCE((m.metadata->>'simulation_mode')::boolean, FALSE) = FALSE
),
bot_messages AS (
  SELECT
    COUNT(*) AS total_bot_messages
  FROM messages m
  JOIN bounds b ON m.client_id = b.client_id
  WHERE m.role = 'assistant'
    AND m.created_at >= b.start_ts
    AND m.created_at < b.end_ts
    AND (
      m.metadata->>'source' = 'bot'
      OR (
        NOT (m.metadata ? 'source')
        AND COALESCE((m.metadata->>'system')::boolean, FALSE) = FALSE
        AND NULLIF(m.metadata->>'event', '') IS NULL
        AND (m.metadata->'decision_meta'->>'pending_action') IS NULL
        AND (m.metadata->'decision_meta'->>'pending_sla_ping') IS NULL
      )
    )
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
  rag_low_conf_rate,
  clarify_rate,
  clarify_success_rate,
  total_user_messages,
  total_bot_messages,
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
  COALESCE(ROUND(um.total_rag_low_conf::numeric / NULLIF(um.total_user_messages, 0), 4), 0),
  COALESCE(ROUND(um.total_clarify::numeric / NULLIF(um.total_user_messages, 0), 4), 0),
  COALESCE(ROUND(um.total_clarify_success::numeric / NULLIF(um.total_clarify, 0), 4), 0),
  COALESCE(um.total_user_messages, 0),
  COALESCE(bm.total_bot_messages, 0),
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
LEFT JOIN bot_messages bm ON TRUE
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
  rag_low_conf_rate = EXCLUDED.rag_low_conf_rate,
  clarify_rate = EXCLUDED.clarify_rate,
  clarify_success_rate = EXCLUDED.clarify_success_rate,
  total_user_messages = EXCLUDED.total_user_messages,
  total_bot_messages = EXCLUDED.total_bot_messages,
  total_outbox_sent = EXCLUDED.total_outbox_sent,
  total_outbox_failed = EXCLUDED.total_outbox_failed,
  total_llm_used = EXCLUDED.total_llm_used,
  total_llm_timeout = EXCLUDED.total_llm_timeout,
  total_handovers = EXCLUDED.total_handovers,
  total_fast_intent = EXCLUDED.total_fast_intent,
  updated_at = NOW();
"""

_METRICS_DAILY_ALTER_SQL = """
ALTER TABLE metrics_daily
  ADD COLUMN IF NOT EXISTS rag_low_conf_rate NUMERIC(6, 4),
  ADD COLUMN IF NOT EXISTS clarify_rate NUMERIC(6, 4),
  ADD COLUMN IF NOT EXISTS clarify_success_rate NUMERIC(6, 4),
  ADD COLUMN IF NOT EXISTS total_bot_messages INTEGER DEFAULT 0;
"""

_METRICS_ANALYTICS_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS metrics_analytics_daily (
  metric_date DATE NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  inbound_conversations_total INTEGER NOT NULL DEFAULT 0,
  bot_closed_sessions INTEGER NOT NULL DEFAULT 0,
  bot_closed_total_sessions INTEGER NOT NULL DEFAULT 0,
  bot_closed_incomplete_total INTEGER NOT NULL DEFAULT 0,
  bot_closed_rate NUMERIC(6, 4),
  manager_median_response_seconds NUMERIC(10, 2),
  manager_time_saved_seconds_estimate NUMERIC(12, 2),
  booking_total INTEGER NOT NULL DEFAULT 0,
  booking_attributed INTEGER NOT NULL DEFAULT 0,
  booking_missing_conversation_total INTEGER NOT NULL DEFAULT 0,
  booking_conversion_rate NUMERIC(6, 4),
  first_response_p50_seconds NUMERIC(10, 2),
  first_response_p90_seconds NUMERIC(10, 2),
  first_response_missing_total INTEGER NOT NULL DEFAULT 0,
  after_hours_total INTEGER NOT NULL DEFAULT 0,
  after_hours_covered INTEGER NOT NULL DEFAULT 0,
  after_hours_missing_total INTEGER NOT NULL DEFAULT 0,
  after_hours_coverage_rate NUMERIC(6, 4),
  escalation_total INTEGER NOT NULL DEFAULT 0,
  escalation_quality_total INTEGER NOT NULL DEFAULT 0,
  escalation_meta_missing_total INTEGER NOT NULL DEFAULT 0,
  escalation_quality_rate NUMERIC(6, 4),
  outbox_failed_total INTEGER NOT NULL DEFAULT 0,
  outbox_saved_total INTEGER NOT NULL DEFAULT 0,
  no_response_alert_total INTEGER NOT NULL DEFAULT 0,
  intent_missing_total INTEGER NOT NULL DEFAULT 0,
  top_intents JSONB,
  top_info_sections JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (metric_date, client_id)
);
"""

_METRICS_ANALYTICS_DAILY_SQL = """
WITH params AS (
  SELECT
    CAST(:client_id AS uuid) AS client_id,
    CAST(:metric_date AS date) AS metric_date
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
    m.conversation_id,
    m.created_at,
    m.metadata
  FROM messages m
  JOIN bounds b ON m.client_id = b.client_id
  WHERE m.role = 'user'
    AND m.created_at >= b.start_ts
    AND m.created_at < b.end_ts
    AND COALESCE((m.metadata->>'simulation_mode')::boolean, FALSE) = FALSE
),
inbound_conversations AS (
  SELECT
    conversation_id,
    MIN(created_at) AS first_user_at,
    MAX(created_at) AS last_user_at,
    COUNT(*) AS user_message_count
  FROM user_messages
  GROUP BY conversation_id
),
inbound_summary AS (
  SELECT COUNT(*) AS inbound_conversations_total
  FROM inbound_conversations
),
bot_closed_candidates AS (
  SELECT
    ic.conversation_id,
    ic.first_user_at,
    ic.last_user_at,
    (ic.last_user_at + INTERVAL '24 hours' <= NOW()) AS window_complete,
    EXISTS (
      SELECT 1
      FROM messages m
      WHERE m.conversation_id = ic.conversation_id
        AND m.role = 'assistant'
        AND m.created_at > ic.last_user_at
        AND m.created_at <= ic.last_user_at + INTERVAL '24 hours'
        AND (
          m.metadata->>'source' = 'bot'
          OR (
            NOT (m.metadata ? 'source')
            AND COALESCE((m.metadata->>'system')::boolean, FALSE) = FALSE
            AND NULLIF(m.metadata->>'event', '') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_action') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_sla_ping') IS NULL
          )
        )
    ) AS has_bot_reply,
    EXISTS (
      SELECT 1
      FROM handovers h
      WHERE h.conversation_id = ic.conversation_id
        AND h.created_at >= ic.first_user_at
        AND h.created_at <= ic.last_user_at + INTERVAL '24 hours'
    ) AS has_handover,
    EXISTS (
      SELECT 1
      FROM messages m
      WHERE m.conversation_id = ic.conversation_id
        AND m.role = 'user'
        AND m.created_at > ic.last_user_at
        AND m.created_at < ic.last_user_at + INTERVAL '24 hours'
        AND COALESCE((m.metadata->>'simulation_mode')::boolean, FALSE) = FALSE
    ) AS has_followup
  FROM inbound_conversations ic
),
bot_closed_summary AS (
  SELECT
    COUNT(*) FILTER (WHERE window_complete) AS bot_closed_total_sessions,
    COUNT(*) FILTER (WHERE NOT window_complete) AS bot_closed_incomplete_total,
    COUNT(*) FILTER (
      WHERE window_complete
        AND has_bot_reply
        AND NOT has_handover
        AND NOT has_followup
    ) AS bot_closed_sessions
  FROM bot_closed_candidates
),
metrics_daily_data AS (
  SELECT total_bot_messages
  FROM metrics_daily md
  JOIN bounds b ON md.client_id = b.client_id AND md.metric_date = b.metric_date
),
manager_first_response AS (
  SELECT
    ic.conversation_id,
    MIN(m.created_at) AS manager_first_at,
    ic.first_user_at
  FROM inbound_conversations ic
  JOIN messages m
    ON m.conversation_id = ic.conversation_id
   AND m.role = 'manager'
   AND m.created_at >= ic.first_user_at
  GROUP BY ic.conversation_id, ic.first_user_at
),
manager_summary AS (
  SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (
      ORDER BY EXTRACT(EPOCH FROM (manager_first_at - first_user_at))
    ) AS manager_median_response_seconds
  FROM manager_first_response
),
booking_day AS (
  SELECT a.id, a.conversation_id, a.created_at
  FROM appointments a
  JOIN bounds b ON a.client_id = b.client_id
  WHERE a.created_at >= b.start_ts
    AND a.created_at < b.end_ts
),
booking_summary AS (
  SELECT
    COUNT(*) AS booking_total,
    COUNT(*) FILTER (WHERE conversation_id IS NULL) AS booking_missing_conversation_total,
    COUNT(*) FILTER (
      WHERE conversation_id IS NOT NULL
        AND EXISTS (
          SELECT 1
          FROM messages m
          WHERE m.conversation_id = booking_day.conversation_id
            AND m.role = 'user'
            AND m.created_at >= booking_day.created_at - INTERVAL '24 hours'
            AND m.created_at <= booking_day.created_at
            AND COALESCE((m.metadata->>'simulation_mode')::boolean, FALSE) = FALSE
        )
    ) AS booking_attributed
  FROM booking_day
),
response_messages AS (
  SELECT m.conversation_id, m.created_at
  FROM messages m
  JOIN bounds b ON m.client_id = b.client_id
  WHERE (
      m.role = 'manager'
      OR (
        m.role = 'assistant'
        AND (
          m.metadata->>'source' = 'bot'
          OR (
            NOT (m.metadata ? 'source')
            AND COALESCE((m.metadata->>'system')::boolean, FALSE) = FALSE
            AND NULLIF(m.metadata->>'event', '') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_action') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_sla_ping') IS NULL
          )
        )
      )
    )
),
first_response_candidates AS (
  SELECT
    ic.conversation_id,
    ic.first_user_at,
    MIN(rm.created_at) AS first_response_at
  FROM inbound_conversations ic
  LEFT JOIN response_messages rm
    ON rm.conversation_id = ic.conversation_id
   AND rm.created_at >= ic.first_user_at
  GROUP BY ic.conversation_id, ic.first_user_at
),
first_response_summary AS (
  SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (
      ORDER BY EXTRACT(EPOCH FROM (first_response_at - first_user_at))
    ) FILTER (WHERE first_response_at IS NOT NULL) AS first_response_p50_seconds,
    PERCENTILE_CONT(0.9) WITHIN GROUP (
      ORDER BY EXTRACT(EPOCH FROM (first_response_at - first_user_at))
    ) FILTER (WHERE first_response_at IS NOT NULL) AS first_response_p90_seconds,
    COUNT(*) FILTER (WHERE first_response_at IS NULL) AS first_response_missing_total
  FROM first_response_candidates
),
user_messages_branch AS (
  SELECT
    m.conversation_id,
    m.created_at,
    c.branch_id,
    b.timezone,
    b.working_hours,
    CASE
      WHEN tz.name IS NOT NULL THEN (m.created_at AT TIME ZONE tz.name)
      ELSE NULL
    END AS local_ts
  FROM user_messages m
  JOIN conversations c ON c.id = m.conversation_id
  LEFT JOIN branches b ON b.id = c.branch_id
  LEFT JOIN pg_timezone_names tz ON tz.name = b.timezone
),
after_hours_candidates AS (
  SELECT
    umb.conversation_id,
    umb.created_at,
    umb.local_ts,
    umb.working_hours,
    CASE
      WHEN umb.local_ts IS NULL THEN NULL
      WHEN umb.working_hours IS NULL OR umb.working_hours = '{}'::jsonb THEN NULL
      ELSE CASE EXTRACT(ISODOW FROM umb.local_ts)
        WHEN 1 THEN 'mon'
        WHEN 2 THEN 'tue'
        WHEN 3 THEN 'wed'
        WHEN 4 THEN 'thu'
        WHEN 5 THEN 'fri'
        WHEN 6 THEN 'sat'
        WHEN 7 THEN 'sun'
      END
    END AS day_key
  FROM user_messages_branch umb
),
after_hours_flags AS (
  SELECT
    ahc.conversation_id,
    ahc.created_at,
    CASE
      WHEN ahc.local_ts IS NULL THEN FALSE
      WHEN ahc.day_key IS NULL THEN FALSE
      WHEN (ahc.working_hours->ahc.day_key) IS NULL THEN FALSE
      ELSE TRUE
    END AS has_schedule,
    CASE
      WHEN ahc.local_ts IS NULL THEN NULL
      WHEN ahc.day_key IS NULL THEN NULL
      WHEN (ahc.working_hours->ahc.day_key->>'start') IS NULL
        OR (ahc.working_hours->ahc.day_key->>'end') IS NULL THEN NULL
      WHEN (ahc.working_hours->ahc.day_key->>'start')::time
        <= (ahc.working_hours->ahc.day_key->>'end')::time
        THEN (
          ahc.local_ts::time >= (ahc.working_hours->ahc.day_key->>'start')::time
          AND ahc.local_ts::time < (ahc.working_hours->ahc.day_key->>'end')::time
        )
      ELSE (
        ahc.local_ts::time >= (ahc.working_hours->ahc.day_key->>'start')::time
        OR ahc.local_ts::time < (ahc.working_hours->ahc.day_key->>'end')::time
      )
    END AS within_hours,
    EXISTS (
      SELECT 1
      FROM messages m
      WHERE m.conversation_id = ahc.conversation_id
        AND m.role = 'assistant'
        AND m.created_at >= ahc.created_at
        AND m.created_at <= ahc.created_at + INTERVAL '10 minutes'
        AND (
          m.metadata->>'source' = 'bot'
          OR (
            NOT (m.metadata ? 'source')
            AND COALESCE((m.metadata->>'system')::boolean, FALSE) = FALSE
            AND NULLIF(m.metadata->>'event', '') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_action') IS NULL
            AND (m.metadata->'decision_meta'->>'pending_sla_ping') IS NULL
          )
        )
    ) AS has_bot_reply
  FROM after_hours_candidates ahc
),
after_hours_summary AS (
  SELECT
    COUNT(*) FILTER (WHERE has_schedule = FALSE) AS after_hours_missing_total,
    COUNT(*) FILTER (WHERE within_hours = FALSE) AS after_hours_total,
    COUNT(*) FILTER (WHERE within_hours = FALSE AND has_bot_reply) AS after_hours_covered
  FROM after_hours_flags
),
handovers_day AS (
  SELECT h.meta
  FROM handovers h
  JOIN bounds b ON h.client_id = b.client_id
  WHERE h.created_at >= b.start_ts
    AND h.created_at < b.end_ts
),
escalation_summary AS (
  SELECT
    COUNT(*) AS escalation_total,
    COUNT(*) FILTER (WHERE meta IS NULL) AS escalation_meta_missing_total,
    COUNT(*) FILTER (
      WHERE meta IS NOT NULL
        AND NULLIF(meta->'slots'->>'service', '') IS NOT NULL
        AND NULLIF(meta->'slots'->>'datetime', '') IS NOT NULL
        AND (
          NULLIF(meta->'slots'->>'phone', '') IS NOT NULL
          OR NULLIF(meta->'slots'->>'name', '') IS NOT NULL
        )
    ) AS escalation_quality_total
  FROM handovers_day
),
outbox_events_day AS (
  SELECT e.outbox_id, e.status, e.created_at
  FROM outbox_status_events e
  JOIN bounds b ON e.client_id = b.client_id
  WHERE e.created_at >= b.start_ts
    AND e.created_at < b.end_ts
),
outbox_summary AS (
  SELECT
    COUNT(*) FILTER (WHERE status = 'FAILED') AS outbox_failed_total
  FROM outbox_events_day
),
outbox_saved AS (
  SELECT
    COUNT(DISTINCT f.outbox_id) AS outbox_saved_total
  FROM outbox_events_day f
  WHERE f.status = 'FAILED'
    AND EXISTS (
      SELECT 1
      FROM outbox_status_events s
      WHERE s.outbox_id = f.outbox_id
        AND s.status = 'SENT'
        AND s.created_at > f.created_at
    )
),
alert_summary AS (
  SELECT COUNT(*) AS no_response_alert_total
  FROM alert_events a
  JOIN bounds b ON a.client_id = b.client_id
  WHERE a.created_at >= b.start_ts
    AND a.created_at < b.end_ts
    AND a.alert_type = 'no_response'
),
intent_missing AS (
  SELECT COUNT(*) AS intent_missing_total
  FROM user_messages um
  WHERE NULLIF(TRIM(um.metadata->'decision_meta'->>'intent'), '') IS NULL
),
intent_counts AS (
  SELECT
    LOWER(TRIM(um.metadata->'decision_meta'->>'intent')) AS intent,
    COUNT(*) AS total
  FROM user_messages um
  WHERE NULLIF(TRIM(um.metadata->'decision_meta'->>'intent'), '') IS NOT NULL
  GROUP BY LOWER(TRIM(um.metadata->'decision_meta'->>'intent'))
),
intent_totals AS (
  SELECT COALESCE(SUM(total), 0) AS total
  FROM intent_counts
),
top_intents AS (
  SELECT
    jsonb_agg(
      jsonb_build_object(
        'intent',
        ranked.intent,
        'count',
        ranked.total,
        'share',
        CASE
          WHEN intent_totals.total > 0 THEN ROUND(ranked.total::numeric / intent_totals.total, 4)
          ELSE 0
        END
      )
      ORDER BY ranked.total DESC, ranked.intent
    ) AS top_intents
  FROM (
    SELECT *
    FROM intent_counts
    ORDER BY total DESC, intent
    LIMIT 5
  ) ranked
  CROSS JOIN intent_totals
),
info_sections_raw AS (
  SELECT
    LOWER(value) AS section
  FROM user_messages um
  CROSS JOIN LATERAL jsonb_array_elements_text(
    CASE
      WHEN jsonb_typeof(um.metadata->'decision_meta'->'info_sections') = 'array'
        THEN um.metadata->'decision_meta'->'info_sections'
      ELSE '[]'::jsonb
    END
  ) AS value
),
info_sections_counts AS (
  SELECT section, COUNT(*) AS total
  FROM info_sections_raw
  WHERE section IS NOT NULL AND section <> ''
  GROUP BY section
),
info_sections_totals AS (
  SELECT COALESCE(SUM(total), 0) AS total
  FROM info_sections_counts
),
top_info_sections AS (
  SELECT
    jsonb_agg(
      jsonb_build_object(
        'section',
        ranked.section,
        'count',
        ranked.total,
        'share',
        CASE
          WHEN info_sections_totals.total > 0 THEN ROUND(ranked.total::numeric / info_sections_totals.total, 4)
          ELSE 0
        END
      )
      ORDER BY ranked.total DESC, ranked.section
    ) AS top_info_sections
  FROM (
    SELECT *
    FROM info_sections_counts
    ORDER BY total DESC, section
    LIMIT 5
  ) ranked
  CROSS JOIN info_sections_totals
)
INSERT INTO metrics_analytics_daily (
  metric_date,
  client_id,
  inbound_conversations_total,
  bot_closed_sessions,
  bot_closed_total_sessions,
  bot_closed_incomplete_total,
  bot_closed_rate,
  manager_median_response_seconds,
  manager_time_saved_seconds_estimate,
  booking_total,
  booking_attributed,
  booking_missing_conversation_total,
  booking_conversion_rate,
  first_response_p50_seconds,
  first_response_p90_seconds,
  first_response_missing_total,
  after_hours_total,
  after_hours_covered,
  after_hours_missing_total,
  after_hours_coverage_rate,
  escalation_total,
  escalation_quality_total,
  escalation_meta_missing_total,
  escalation_quality_rate,
  outbox_failed_total,
  outbox_saved_total,
  no_response_alert_total,
  intent_missing_total,
  top_intents,
  top_info_sections,
  created_at,
  updated_at
)
SELECT
  b.metric_date,
  b.client_id,
  COALESCE(isum.inbound_conversations_total, 0),
  COALESCE(bcs.bot_closed_sessions, 0),
  COALESCE(bcs.bot_closed_total_sessions, 0),
  COALESCE(bcs.bot_closed_incomplete_total, 0),
  COALESCE(
    ROUND(bcs.bot_closed_sessions::numeric / NULLIF(bcs.bot_closed_total_sessions, 0), 4),
    0
  ),
  ROUND(ms.manager_median_response_seconds::numeric, 2),
  CASE
    WHEN ms.manager_median_response_seconds IS NULL THEN NULL
    ELSE ROUND(ms.manager_median_response_seconds::numeric * COALESCE(mdd.total_bot_messages, 0), 2)
  END,
  COALESCE(bs.booking_total, 0),
  COALESCE(bs.booking_attributed, 0),
  COALESCE(bs.booking_missing_conversation_total, 0),
  COALESCE(
    ROUND(bs.booking_attributed::numeric / NULLIF(isum.inbound_conversations_total, 0), 4),
    0
  ),
  ROUND(frs.first_response_p50_seconds::numeric, 2),
  ROUND(frs.first_response_p90_seconds::numeric, 2),
  COALESCE(frs.first_response_missing_total, 0),
  COALESCE(ahs.after_hours_total, 0),
  COALESCE(ahs.after_hours_covered, 0),
  COALESCE(ahs.after_hours_missing_total, 0),
  COALESCE(
    ROUND(ahs.after_hours_covered::numeric / NULLIF(ahs.after_hours_total, 0), 4),
    0
  ),
  COALESCE(es.escalation_total, 0),
  COALESCE(es.escalation_quality_total, 0),
  COALESCE(es.escalation_meta_missing_total, 0),
  COALESCE(
    ROUND(es.escalation_quality_total::numeric / NULLIF(es.escalation_total, 0), 4),
    0
  ),
  COALESCE(osum.outbox_failed_total, 0),
  COALESCE(osaved.outbox_saved_total, 0),
  COALESCE(asum.no_response_alert_total, 0),
  COALESCE(im.intent_missing_total, 0),
  ti.top_intents,
  tis.top_info_sections,
  NOW(),
  NOW()
FROM bounds b
LEFT JOIN inbound_summary isum ON TRUE
LEFT JOIN bot_closed_summary bcs ON TRUE
LEFT JOIN metrics_daily_data mdd ON TRUE
LEFT JOIN manager_summary ms ON TRUE
LEFT JOIN booking_summary bs ON TRUE
LEFT JOIN first_response_summary frs ON TRUE
LEFT JOIN after_hours_summary ahs ON TRUE
LEFT JOIN escalation_summary es ON TRUE
LEFT JOIN outbox_summary osum ON TRUE
LEFT JOIN outbox_saved osaved ON TRUE
LEFT JOIN alert_summary asum ON TRUE
LEFT JOIN intent_missing im ON TRUE
LEFT JOIN top_intents ti ON TRUE
LEFT JOIN top_info_sections tis ON TRUE
ON CONFLICT (metric_date, client_id) DO UPDATE SET
  inbound_conversations_total = EXCLUDED.inbound_conversations_total,
  bot_closed_sessions = EXCLUDED.bot_closed_sessions,
  bot_closed_total_sessions = EXCLUDED.bot_closed_total_sessions,
  bot_closed_incomplete_total = EXCLUDED.bot_closed_incomplete_total,
  bot_closed_rate = EXCLUDED.bot_closed_rate,
  manager_median_response_seconds = EXCLUDED.manager_median_response_seconds,
  manager_time_saved_seconds_estimate = EXCLUDED.manager_time_saved_seconds_estimate,
  booking_total = EXCLUDED.booking_total,
  booking_attributed = EXCLUDED.booking_attributed,
  booking_missing_conversation_total = EXCLUDED.booking_missing_conversation_total,
  booking_conversion_rate = EXCLUDED.booking_conversion_rate,
  first_response_p50_seconds = EXCLUDED.first_response_p50_seconds,
  first_response_p90_seconds = EXCLUDED.first_response_p90_seconds,
  first_response_missing_total = EXCLUDED.first_response_missing_total,
  after_hours_total = EXCLUDED.after_hours_total,
  after_hours_covered = EXCLUDED.after_hours_covered,
  after_hours_missing_total = EXCLUDED.after_hours_missing_total,
  after_hours_coverage_rate = EXCLUDED.after_hours_coverage_rate,
  escalation_total = EXCLUDED.escalation_total,
  escalation_quality_total = EXCLUDED.escalation_quality_total,
  escalation_meta_missing_total = EXCLUDED.escalation_meta_missing_total,
  escalation_quality_rate = EXCLUDED.escalation_quality_rate,
  outbox_failed_total = EXCLUDED.outbox_failed_total,
  outbox_saved_total = EXCLUDED.outbox_saved_total,
  no_response_alert_total = EXCLUDED.no_response_alert_total,
  intent_missing_total = EXCLUDED.intent_missing_total,
  top_intents = EXCLUDED.top_intents,
  top_info_sections = EXCLUDED.top_info_sections,
  updated_at = NOW();
"""


def get_metrics_daily_status_allowlist(raw: str | None = None) -> list[str] | None:
    value = raw if raw is not None else os.environ.get("METRICS_DAILY_STATUS_ALLOWLIST")
    if value is None:
        return list(_DEFAULT_STATUS_ALLOWLIST)
    normalized = value.strip().lower()
    if not normalized or normalized in {"*", "all"}:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or list(_DEFAULT_STATUS_ALLOWLIST)


def get_metrics_daily_backfill_max_days(raw: str | None = None) -> int:
    value = raw if raw is not None else os.environ.get("METRICS_DAILY_BACKFILL_MAX_DAYS")
    if value is None:
        return _DEFAULT_BACKFILL_MAX_DAYS
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_BACKFILL_MAX_DAYS
    return max(parsed, 1)


def get_metrics_daily_default_date(
    now: datetime | None = None,
    *,
    offset_days: int = 1,
) -> date:
    now = now or datetime.now(timezone.utc)
    safe_offset = max(offset_days, 0)
    return (now - timedelta(days=safe_offset)).date()


def _resolve_metrics_daily_clients(
    db: Session,
    *,
    client_ids: Iterable[UUID] | None,
    status_allowlist: list[str] | None,
) -> list[Client]:
    if client_ids:
        ids = list(client_ids)
        if not ids:
            return []
        return db.query(Client).filter(Client.id.in_(ids)).all()

    query = db.query(Client)
    if status_allowlist:
        query = query.filter(Client.status.in_(status_allowlist))
    return query.all()


def ensure_metrics_daily_columns(db: Session) -> None:
    db.execute(text(_METRICS_DAILY_ALTER_SQL))
    db.commit()


def ensure_metrics_analytics_daily_table(db: Session) -> None:
    db.execute(text(_METRICS_ANALYTICS_CREATE_SQL))
    db.commit()


def run_metrics_daily_snapshot(
    db: Session,
    *,
    metric_date: date,
    client_ids: Iterable[UUID] | None = None,
    status_allowlist: list[str] | None = None,
) -> dict:
    if not isinstance(metric_date, date):
        raise ValueError("metric_date must be date")

    ensure_metrics_daily_columns(db)
    ensure_metrics_analytics_daily_table(db)
    clients = _resolve_metrics_daily_clients(
        db,
        client_ids=client_ids,
        status_allowlist=status_allowlist,
    )
    results = {
        "metric_date": metric_date.isoformat(),
        "clients_total": len(clients),
        "updated": 0,
        "errors": 0,
        "error_details": [],
    }

    if not clients:
        return results

    for client in clients:
        try:
            db.execute(
                text(_METRICS_DAILY_SQL),
                {"client_id": client.id, "metric_date": metric_date},
            )
            db.execute(
                text(_METRICS_ANALYTICS_DAILY_SQL),
                {"client_id": client.id, "metric_date": metric_date},
            )
            db.commit()
            results["updated"] += 1
        except Exception as exc:
            db.rollback()
            results["errors"] += 1
            error_detail = {
                "client_id": str(client.id),
                "client_slug": client.name,
                "error": str(exc)[:200],
            }
            results["error_details"].append(error_detail)
            logger.warning(
                "Metrics daily snapshot failed",
                extra={"context": {**error_detail, "metric_date": metric_date.isoformat()}},
            )

    return results
