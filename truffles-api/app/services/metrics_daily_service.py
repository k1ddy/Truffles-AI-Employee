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
