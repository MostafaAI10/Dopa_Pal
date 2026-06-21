from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import List, TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.state import StateLog
    from app.models.reward import Reward
    from app.models.integration import IntegrationToken

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="ar")
    wake_time_pref: Mapped[datetime.time] = mapped_column(Time)

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    state_logs: Mapped[List["StateLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rewards: Mapped[List["Reward"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    integration_tokens: Mapped[List["IntegrationToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
