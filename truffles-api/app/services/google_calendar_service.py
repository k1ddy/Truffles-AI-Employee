"""
Google Calendar Service - handles OAuth2 and Calendar API operations.
IMPORTANT: Google API libraries are optional. If not installed, service gracefully degrades.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import get_logger

logger = get_logger(__name__)

# Try to import Google libraries (optional)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    logger.warning("Google Calendar libraries not installed. Calendar sync disabled.")
    GOOGLE_AVAILABLE = False
    Credentials = None
    Flow = None
    HttpError = Exception

# OAuth2 Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8001/console/v1/calendar/google/callback")
CALENDAR_TOKEN_ENC_KEY = os.environ.get("CALENDAR_TOKEN_ENC_KEY", "")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarService:
    """
    Service for interacting with Google Calendar API.
    Handles OAuth2 flow and calendar operations.
    Gracefully degrades if Google libraries not installed.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.available = GOOGLE_AVAILABLE

    def _get_token_key(self) -> Optional[str]:
        if not CALENDAR_TOKEN_ENC_KEY:
            logger.warning("CALENDAR_TOKEN_ENC_KEY not set; encrypted tokens unavailable.")
            return None
        return CALENDAR_TOKEN_ENC_KEY

    def _encrypt_token(self, token: Optional[str]) -> Optional[bytes]:
        if not token:
            return None
        token_key = self._get_token_key()
        if not token_key:
            return None
        result = self.db.execute(
            text("SELECT pgp_sym_encrypt(:token, :key)"),
            {"token": token, "key": token_key}
        ).scalar_one()
        return result

    def _decrypt_token(self, token_enc: Optional[bytes]) -> Optional[str]:
        if not token_enc:
            return None
        token_key = self._get_token_key()
        if not token_key:
            logger.error("Encrypted calendar token present, but CALENDAR_TOKEN_ENC_KEY is missing.")
            return None
        result = self.db.execute(
            text("SELECT pgp_sym_decrypt(:token_enc, :key)"),
            {"token_enc": token_enc, "key": token_key}
        ).scalar_one()
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return result
    
    # ==================== OAuth2 Flow ====================
    
    def get_auth_url(self, client_id: UUID, branch_id: Optional[UUID] = None) -> Optional[str]:
        """Generate OAuth2 authorization URL."""
        if not self.available:
            logger.warning("Google Calendar not available")
            return None
            
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        state = f"{client_id}"
        if branch_id:
            state = f"{client_id}:{branch_id}"
        
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent"
        )
        
        return auth_url
    
    def handle_callback(self, code: str, state: str) -> Optional[Any]:
        """Handle OAuth2 callback."""
        if not self.available:
            return None
            
        from app.models.google_calendar_token import GoogleCalendarToken
        from app.services.calendar_sync_service import ensure_calendar_connection
        
        parts = state.split(":")
        client_id = UUID(parts[0])
        branch_id = UUID(parts[1]) if len(parts) > 1 else None
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        existing = self.db.query(GoogleCalendarToken).filter(
            GoogleCalendarToken.client_id == client_id,
            GoogleCalendarToken.branch_id == branch_id
        ).first()
        
        access_token_enc = self._encrypt_token(credentials.token)
        refresh_token_enc = self._encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
        token_key = self._get_token_key()

        if existing:
            if token_key and access_token_enc:
                existing.access_token_enc = access_token_enc
                if refresh_token_enc:
                    existing.refresh_token_enc = refresh_token_enc
                existing.encrypted_at = datetime.now(timezone.utc)
            else:
                existing.access_token = credentials.token
                if credentials.refresh_token:
                    existing.refresh_token = credentials.refresh_token
                existing.encryption_version = 0
            existing.expires_at = credentials.expiry
            existing.scopes = list(credentials.scopes) if credentials.scopes else SCOPES
            existing.updated_at = datetime.now(timezone.utc)
            token = existing
        else:
            token = GoogleCalendarToken(
                client_id=client_id,
                branch_id=branch_id,
                access_token=credentials.token if not token_key else "",
                refresh_token=credentials.refresh_token if not token_key else "",
                access_token_enc=access_token_enc,
                refresh_token_enc=refresh_token_enc,
                encryption_version=1 if token_key else 0,
                encrypted_at=datetime.now(timezone.utc) if token_key else None,
                expires_at=credentials.expiry,
                scopes=list(credentials.scopes) if credentials.scopes else SCOPES
            )
            self.db.add(token)
        
        if branch_id:
            ensure_calendar_connection(
                self.db,
                client_id=client_id,
                branch_id=branch_id,
                provider="google_calendar",
                calendar_id="primary",
            )
        self.db.commit()
        return token
    
    def get_credentials(self, client_id: UUID, branch_id: Optional[UUID] = None) -> Optional[Any]:
        """Get valid credentials."""
        if not self.available:
            return None
            
        from app.models.google_calendar_token import GoogleCalendarToken
        
        token = self.db.query(GoogleCalendarToken).filter(
            GoogleCalendarToken.client_id == client_id,
            GoogleCalendarToken.branch_id == branch_id
        ).first()
        
        if not token:
            return None
        
        decrypted_access = self._decrypt_token(token.access_token_enc)
        decrypted_refresh = self._decrypt_token(token.refresh_token_enc)

        if token.access_token_enc and decrypted_access is None:
            return None

        access_token = decrypted_access or token.access_token
        refresh_token = decrypted_refresh or token.refresh_token

        if not access_token:
            return None

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=token.scopes
        )
        
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(None)
                access_token_enc = self._encrypt_token(credentials.token)
                token_key = self._get_token_key()
                if token_key and access_token_enc:
                    token.access_token_enc = access_token_enc
                    token.encrypted_at = datetime.now(timezone.utc)
                else:
                    token.access_token = credentials.token
                    token.encryption_version = 0
                token.expires_at = credentials.expiry
                token.updated_at = datetime.now(timezone.utc)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None
        
        return credentials
    
    # ==================== Calendar Operations ====================
    
    def get_free_busy(
        self,
        calendar_id: str,
        client_id: UUID,
        branch_id: Optional[UUID],
        time_min: datetime,
        time_max: datetime
    ) -> List[Dict[str, datetime]]:
        """Get busy time slots from Google Calendar."""
        if not self.available:
            return []
            
        credentials = self.get_credentials(client_id, branch_id)
        if not credentials:
            return []
        
        try:
            service = build("calendar", "v3", credentials=credentials)
            
            body = {
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "items": [{"id": calendar_id}]
            }
            
            result = service.freebusy().query(body=body).execute()
            busy_slots = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
            
            return [
                {
                    "start": datetime.fromisoformat(slot["start"].replace("Z", "+00:00")),
                    "end": datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
                }
                for slot in busy_slots
            ]
        except Exception as e:
            logger.error(f"Google Calendar API error: {e}")
            return []
    
    def create_event(
        self,
        calendar_id: str,
        client_id: UUID,
        branch_id: Optional[UUID],
        appointment: Any,
        specialist_name: Optional[str],
        service_name: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Create a calendar event for an appointment."""
        if not self.available:
            return None
            
        credentials = self.get_credentials(client_id, branch_id)
        if not credentials:
            return None
        
        try:
            service = build("calendar", "v3", credentials=credentials)
            
            summary_service = service_name or getattr(appointment, "service_type", None) or "Запись"
            summary_name = appointment.customer_name or "Клиент"
            event = {
                "summary": f"{summary_service} - {summary_name}",
                "description": (
                    f"Телефон: {appointment.customer_phone or 'Не указан'}\n\n"
                    f"Примечания: {appointment.notes or '-'}"
                ),
                "start": {
                    "dateTime": appointment.start_at.isoformat(),
                    "timeZone": "Asia/Almaty"
                },
                "end": {
                    "dateTime": appointment.end_at.isoformat(),
                    "timeZone": "Asia/Almaty"
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 60},
                        {"method": "popup", "minutes": 15},
                    ]
                }
            }
            
            result = service.events().insert(calendarId=calendar_id, body=event).execute()
            logger.info(f"Created Google Calendar event: {result.get('id')}")
            return {"id": result.get("id"), "etag": result.get("etag"), "raw": result}
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def update_event(
        self,
        calendar_id: str,
        client_id: UUID,
        branch_id: Optional[UUID],
        event_id: str,
        appointment: Any,
        specialist_name: Optional[str],
        service_name: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update a calendar event for an appointment."""
        if not self.available:
            return None

        credentials = self.get_credentials(client_id, branch_id)
        if not credentials:
            return None

        try:
            service = build("calendar", "v3", credentials=credentials)
            summary_service = service_name or getattr(appointment, "service_type", None) or "Запись"
            summary_name = appointment.customer_name or "Клиент"
            event = {
                "summary": f"{summary_service} - {summary_name}",
                "description": (
                    f"Телефон: {appointment.customer_phone or 'Не указан'}\n\n"
                    f"Примечания: {appointment.notes or '-'}"
                ),
                "start": {
                    "dateTime": appointment.start_at.isoformat(),
                    "timeZone": "Asia/Almaty",
                },
                "end": {
                    "dateTime": appointment.end_at.isoformat(),
                    "timeZone": "Asia/Almaty",
                },
            }
            result = service.events().patch(calendarId=calendar_id, eventId=event_id, body=event).execute()
            logger.info("Updated Google Calendar event: %s", result.get("id"))
            return {"id": result.get("id"), "etag": result.get("etag"), "raw": result}
        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return None

    def list_events(
        self,
        calendar_id: str,
        client_id: UUID,
        branch_id: Optional[UUID],
        *,
        sync_token: Optional[str] = None,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> tuple[list[dict[str, Any]], Optional[str], Optional[str]]:
        """List calendar events with optional sync token."""
        if not self.available:
            return [], None, "provider_unavailable"

        credentials = self.get_credentials(client_id, branch_id)
        if not credentials:
            return [], None, "credentials_missing"

        try:
            service = build("calendar", "v3", credentials=credentials)
            params: dict[str, Any] = {
                "calendarId": calendar_id,
                "singleEvents": True,
                "showDeleted": True,
                "maxResults": 2500,
            }
            if sync_token:
                params["syncToken"] = sync_token
            else:
                if time_min:
                    params["timeMin"] = time_min.isoformat()
                if time_max:
                    params["timeMax"] = time_max.isoformat()
                params["orderBy"] = "startTime"

            result = service.events().list(**params).execute()
            events = result.get("items", []) if isinstance(result, dict) else []
            next_token = result.get("nextSyncToken") if isinstance(result, dict) else None
            return events, next_token, None
        except HttpError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code is None and getattr(exc, "resp", None) is not None:
                status_code = getattr(exc.resp, "status", None)
            if status_code == 410:
                return [], None, "sync_token_invalid"
            return [], None, "provider_error"
        except Exception as exc:
            logger.error("Failed to list calendar events: %s", exc)
            return [], None, "provider_error"
    
    def delete_event(
        self,
        calendar_id: str,
        client_id: UUID,
        branch_id: Optional[UUID],
        event_id: str
    ) -> bool:
        """Delete a calendar event."""
        if not self.available:
            return False
            
        credentials = self.get_credentials(client_id, branch_id)
        if not credentials:
            return False
        
        try:
            service = build("calendar", "v3", credentials=credentials)
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            logger.info(f"Deleted Google Calendar event: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False
