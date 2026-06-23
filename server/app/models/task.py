from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import Optional, List, TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from app.models.user import User

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    raw_source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50)) # 'manual', 'voice', 'highlight', 'calendar'
    deadline: Mapped[datetime.datetime] = mapped_column(DateTime)
    estimated_hours: Mapped[float] = mapped_column()
    interest_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending") # 'pending', 'completed', 'failed'
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )
    pinch_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    sub_blocks: Mapped[List["SubBlock"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class SubBlock(Base):
    __tablename__ = "sub_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column()
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(default=120)
    scheduled_date: Mapped[datetime.date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="pending") # 'pending', 'completed', 'skipped'
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="sub_blocks")
