from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import Optional, Dict, Any, TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from app.models.user import User

class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(50)) # 'theme', 'audio', 'interest_drop'
    unlocked_at: Mapped[datetime.datetime] = mapped_column(DateTime(), server_default=func.now())
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True) # Maps to json/jsonb natively in Postgres

    # Relationships
    user: Mapped["User"] = relationship(back_populates="rewards")
