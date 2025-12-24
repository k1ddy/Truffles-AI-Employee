from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ClientSettings(Base):
    __tablename__ = "client_settings"

    client_id = Column(UUID(as_uuid=True), primary_key=True)
    telegram_chat_id = Column(Text)
    telegram_bot_token = Column(Text)
    reminder_timeout_1 = Column(Integer, default=30)
    reminder_timeout_2 = Column(Integer, default=60)
    auto_close_timeout = Column(Integer, default=120)
    owner_telegram_id = Column(Text)
    enable_reminders = Column(Boolean, default=True)
    enable_owner_escalation = Column(Boolean, default=True)
    mute_duration_first_minutes = Column(Integer, default=30)
    mute_duration_second_hours = Column(Integer, default=24)
    branch_resolution_mode = Column(Text, default="hybrid")
    remember_branch_preference = Column(Boolean, default=True)
    manager_scope = Column(Text, default="branch")
    require_branch_for_pricing = Column(Boolean, default=True)
    auto_approve_roles = Column(Text, default="owner,admin")
    webhook_secret = Column(Text)
