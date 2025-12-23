import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import setup_logging
from app.models import Conversation, Handover, Message, User
from app.routers import admin, alerts, callback, message, reminders, telegram_webhook, webhook

setup_logging()

app = FastAPI(
    title="Truffles API",
    description="Backend service for Truffles chatbot",
    version="0.1.0",
)

cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
if not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(message.router)
app.include_router(callback.router)
app.include_router(reminders.router)
app.include_router(webhook.router)
app.include_router(telegram_webhook.router)
app.include_router(alerts.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    conversations_count = db.query(Conversation).count()
    users_count = db.query(User).count()
    messages_count = db.query(Message).count()
    handovers_count = db.query(Handover).count()
    return {
        "status": "ok",
        "conversations": conversations_count,
        "users": users_count,
        "messages": messages_count,
        "handovers": handovers_count,
    }
