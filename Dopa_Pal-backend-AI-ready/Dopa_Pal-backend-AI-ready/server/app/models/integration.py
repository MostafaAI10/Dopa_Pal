from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import Optional, Dict, Any, TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from app.models.user import User

class IntegrationToken(Base):
    __tablename__ = "integration_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50)) # 'google', 'notion', 'jira', 'canvas'
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Refresh token might be empty for API-key configs
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    settings_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True) # Configurations, toggles, calendars metadata

    # Relationships
    user: Mapped["User"] = relationship(back_populates="integration_tokens")
