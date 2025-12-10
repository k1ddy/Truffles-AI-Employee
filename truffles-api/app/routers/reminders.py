from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.schemas.reminder import (
    RemindersResponse,
    ReminderSentRequest,
    ReminderSentResponse,
)
from app.services.reminder_service import get_pending_reminders, mark_reminder_sent

router = APIRouter()


@router.get("/reminders", response_model=RemindersResponse)
def get_reminders(db: Session = Depends(get_db)):
    """Get list of handovers that need reminders."""
    reminders = get_pending_reminders(db)
    return RemindersResponse(
        count=len(reminders),
        reminders=reminders
    )


@router.post("/reminders/{handover_id}/sent", response_model=ReminderSentResponse)
def reminder_sent(
    handover_id: UUID,
    request: ReminderSentRequest,
    db: Session = Depends(get_db)
):
    """Mark reminder as sent."""
    success = mark_reminder_sent(db, handover_id, request.reminder_type)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Handover {handover_id} not found")
    
    db.commit()
    
    return ReminderSentResponse(
        success=True,
        handover_id=handover_id,
        reminder_type=request.reminder_type,
        message=f"{request.reminder_type} marked as sent"
    )
