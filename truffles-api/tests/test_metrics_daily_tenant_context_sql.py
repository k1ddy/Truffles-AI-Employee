from app.services import metrics_daily_service


def test_metrics_daily_sql_contains_tenant_context_filter():
    sql = metrics_daily_service._METRICS_DAILY_SQL
    assert "m.metadata->'tenant_context'->>'client_id'" in sql
    assert "(TRIM(m.metadata->'tenant_context'->>'client_id'))::uuid = b.client_id" in sql


def test_metrics_analytics_daily_sql_contains_tenant_context_filter():
    sql = metrics_daily_service._METRICS_ANALYTICS_DAILY_SQL
    assert "m.metadata->'tenant_context'->>'client_id'" in sql
    assert "(TRIM(m.metadata->'tenant_context'->>'client_id'))::uuid = b.client_id" in sql
