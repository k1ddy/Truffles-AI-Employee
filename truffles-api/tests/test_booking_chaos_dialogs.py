from app.routers import webhook as webhook_router
from app.routers.webhook import _legacy as legacy_router


def test_booking_chaos_dialog_suite_no_longer_targets_public_webhook_package() -> None:
    assert not hasattr(webhook_router, "_handle_webhook_payload")
    assert hasattr(legacy_router, "_handle_webhook_payload")
