from sqlalchemy import ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import Optional, TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from app.models.user import User

class StateLog(Base):
    __tablename__ = "state_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[datetime.date] = mapped_column(Date)
    wake_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    startup_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    mood_score: Mapped[int] = mapped_column() # Scales 1 to 5
    computed_state_score: Mapped[float] = mapped_column() # 0 to 100

    # Relationships
    user: Mapped["User"] = relationship(back_populates="state_logs")
