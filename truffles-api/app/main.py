from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Conversation, Message, Handover
from app.routers import message, callback, reminders, webhook, telegram_webhook, admin

app = FastAPI(
    title="Truffles API",
    description="Backend service for Truffles chatbot",
    version="0.1.0",
)

app.include_router(message.router)
app.include_router(callback.router)
app.include_router(reminders.router)
app.include_router(webhook.router)
app.include_router(telegram_webhook.router)
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
