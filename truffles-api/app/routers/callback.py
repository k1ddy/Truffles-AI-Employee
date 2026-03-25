from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.callback import CallbackRequest, CallbackResponse
from app.services.callback_service import CallbackError, process_callback

router = APIRouter()


@router.post("/callback", response_model=CallbackResponse)
def handle_callback(request: CallbackRequest, db: Session = Depends(get_db)):
    """Handle manager callback action (take/resolve/skip/return)."""

    try:
        old_state, new_state = process_callback(
            db, request.conversation_id, request.action, request.manager_id, request.manager_name
        )

        db.commit()

        messages = {
            "take": "Manager took the conversation",
            "resolve": "Conversation resolved",
            "skip": "Conversation skipped",
            "return": "Conversation returned to bot",
        }

        return CallbackResponse(
            success=True,
            conversation_id=request.conversation_id,
            action=request.action,
            old_state=old_state,
            new_state=new_state,
            message=messages.get(request.action),
        )

    except CallbackError as e:
        raise HTTPException(status_code=400, detail=e.message)
