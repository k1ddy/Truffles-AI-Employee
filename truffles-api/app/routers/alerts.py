"""Alert endpoints for testing Telegram alert delivery."""

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.services.alert_service import send_alert

router = APIRouter()


class AlertTestResponse(BaseModel):
    success: bool
    message: str


def _require_admin_token(provided: Optional[str]) -> None:
    expected = os.environ.get("ALERTS_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ALERTS_ADMIN_TOKEN not configured",
        )
    if not provided or provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.post("/alerts/test", response_model=AlertTestResponse)
def alerts_test(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    _require_admin_token(x_admin_token)
    sent = send_alert("INFO", "Alerts test", {"source": "alerts.test"})
    if sent:
        return AlertTestResponse(success=True, message="Alert sent")
    return AlertTestResponse(success=False, message="Alert not sent (check ALERT_BOT_TOKEN/ALERT_CHAT_ID)")
