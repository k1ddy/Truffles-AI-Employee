from app.routers import console as console_router


def test_resolve_kpi_status_fact():
    assert console_router._resolve_kpi_status(0.2) == "fact"


def test_resolve_kpi_status_need_on_missing_total():
    assert console_router._resolve_kpi_status(0.2, missing_total=3) == "need"


def test_resolve_kpi_status_estimate():
    assert console_router._resolve_kpi_status(120, estimate=True) == "estimate"


def test_resolve_kpi_status_need_on_none():
    assert console_router._resolve_kpi_status(None) == "need"
