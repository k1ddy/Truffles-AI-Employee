"""Admin API endpoints for managing bot configuration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import Client, Prompt, ClientSettings

router = APIRouter(prefix="/admin", tags=["admin"])


# === SCHEMAS ===

class PromptUpdate(BaseModel):
    text: str
    
class PromptResponse(BaseModel):
    client_slug: str
    name: str
    text: str
    
class SettingsUpdate(BaseModel):
    mute_duration_first_minutes: Optional[int] = None
    mute_duration_second_hours: Optional[int] = None
    reminder_1_minutes: Optional[int] = None
    reminder_2_minutes: Optional[int] = None


# === PROMPT ENDPOINTS ===

@router.get("/prompt/{client_slug}")
async def get_prompt(client_slug: str, db: Session = Depends(get_db)) -> PromptResponse:
    """Get current system prompt for client."""
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")
    
    prompt = db.query(Prompt).filter(
        Prompt.client_id == client.id,
        Prompt.name == "system",
        Prompt.is_active == True
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt not found for '{client_slug}'")
    
    return PromptResponse(
        client_slug=client_slug,
        name="system",
        text=prompt.text
    )


@router.put("/prompt/{client_slug}")
async def update_prompt(
    client_slug: str, 
    data: PromptUpdate, 
    db: Session = Depends(get_db)
) -> PromptResponse:
    """Update system prompt for client.
    
    Validation:
    - Client must exist
    - Prompt text must not be empty
    - Prompt text must be < 10000 chars
    """
    # Validation
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty")
    
    if len(data.text) > 10000:
        raise HTTPException(status_code=400, detail="Prompt text too long (max 10000 chars)")
    
    # Find client
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")
    
    # Find or create prompt
    prompt = db.query(Prompt).filter(
        Prompt.client_id == client.id,
        Prompt.name == "system"
    ).first()
    
    if prompt:
        prompt.text = data.text.strip()
        prompt.is_active = True
    else:
        prompt = Prompt(
            client_id=client.id,
            name="system",
            text=data.text.strip(),
            is_active=True
        )
        db.add(prompt)
    
    db.commit()
    
    return PromptResponse(
        client_slug=client_slug,
        name="system",
        text=prompt.text
    )


# === SETTINGS ENDPOINTS ===

@router.get("/settings/{client_slug}")
async def get_settings(client_slug: str, db: Session = Depends(get_db)):
    """Get client settings."""
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")
    
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == client.id
    ).first()
    
    if not settings:
        return {
            "client_slug": client_slug,
            "mute_duration_first_minutes": 30,
            "mute_duration_second_hours": 24,
            "reminder_1_minutes": 15,
            "reminder_2_minutes": 60,
        }
    
    return {
        "client_slug": client_slug,
        "mute_duration_first_minutes": settings.mute_duration_first_minutes or 30,
        "mute_duration_second_hours": settings.mute_duration_second_hours or 24,
        "reminder_1_minutes": settings.reminder_1_minutes or 15,
        "reminder_2_minutes": settings.reminder_2_minutes or 60,
    }


@router.put("/settings/{client_slug}")
async def update_settings(
    client_slug: str,
    data: SettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update client settings.
    
    Validation:
    - mute_duration_first_minutes: 1-120
    - mute_duration_second_hours: 1-72
    - reminder_1_minutes: 5-60
    - reminder_2_minutes: 30-180
    """
    # Find client
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")
    
    # Validation
    if data.mute_duration_first_minutes is not None:
        if not 1 <= data.mute_duration_first_minutes <= 120:
            raise HTTPException(status_code=400, detail="mute_duration_first_minutes must be 1-120")
    
    if data.mute_duration_second_hours is not None:
        if not 1 <= data.mute_duration_second_hours <= 72:
            raise HTTPException(status_code=400, detail="mute_duration_second_hours must be 1-72")
    
    if data.reminder_1_minutes is not None:
        if not 5 <= data.reminder_1_minutes <= 60:
            raise HTTPException(status_code=400, detail="reminder_1_minutes must be 5-60")
    
    if data.reminder_2_minutes is not None:
        if not 30 <= data.reminder_2_minutes <= 180:
            raise HTTPException(status_code=400, detail="reminder_2_minutes must be 30-180")
    
    # Find or create settings
    settings = db.query(ClientSettings).filter(
        ClientSettings.client_id == client.id
    ).first()
    
    if not settings:
        settings = ClientSettings(client_id=client.id)
        db.add(settings)
    
    # Update only provided fields
    if data.mute_duration_first_minutes is not None:
        settings.mute_duration_first_minutes = data.mute_duration_first_minutes
    if data.mute_duration_second_hours is not None:
        settings.mute_duration_second_hours = data.mute_duration_second_hours
    if data.reminder_1_minutes is not None:
        settings.reminder_1_minutes = data.reminder_1_minutes
    if data.reminder_2_minutes is not None:
        settings.reminder_2_minutes = data.reminder_2_minutes
    
    db.commit()
    
    return await get_settings(client_slug, db)
