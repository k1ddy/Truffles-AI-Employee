from app.routers import console as console_router


def test_resolve_kpi_status_fact():
    assert console_router._resolve_kpi_status(0.2) == "fact"


def test_resolve_kpi_status_need_on_missing_total():
    assert console_router._resolve_kpi_status(0.2, missing_total=3) == "need"


def test_resolve_kpi_status_estimate():
    assert console_router._resolve_kpi_status(120, estimate=True) == "estimate"


def test_resolve_kpi_status_need_on_none():
    assert console_router._resolve_kpi_status(None) == "need"


def test_resolve_threshold_kpi_status_need_on_none():
    assert console_router._resolve_threshold_kpi_status(None, max_fact=1.0) == "need"


def test_resolve_threshold_kpi_status_fact_on_threshold():
    assert console_router._resolve_threshold_kpi_status(0.05, max_fact=0.05) == "fact"


def test_resolve_threshold_kpi_status_need_above_threshold():
    assert console_router._resolve_threshold_kpi_status(181.0, max_fact=180.0) == "need"


def test_derive_stale_view_rate_none_when_inbound_missing():
    assert (
        console_router._derive_stale_view_rate(
            inbound_total=0,
            no_response_alert_total=3,
        )
        is None
    )


def test_derive_stale_view_rate_none_when_alerts_missing():
    assert (
        console_router._derive_stale_view_rate(
            inbound_total=10,
            no_response_alert_total=None,
        )
        is None
    )


def test_derive_stale_view_rate_ratio_and_rounding():
    assert (
        console_router._derive_stale_view_rate(
            inbound_total=27,
            no_response_alert_total=3,
        )
        == 0.1111
    )


def test_derive_stale_view_rate_clamps_to_one():
    assert (
        console_router._derive_stale_view_rate(
            inbound_total=5,
            no_response_alert_total=9,
        )
        == 1.0
    )
