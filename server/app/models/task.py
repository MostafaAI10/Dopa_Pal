from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    raw_source_text = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False) # 'manual', 'voice', 'highlight', 'calendar'
    deadline = Column(DateTime, nullable=False)
    estimated_hours = Column(Float, nullable=False)
    interest_tag = Column(String(100), nullable=True)
    status = Column(String(50), default="pending", nullable=False) # 'pending', 'completed', 'failed'

    # Relationships
    user = relationship("User", back_populates="tasks")
    sub_blocks = relationship("SubBlock", back_populates="task", cascade="all, delete-orphan")


class SubBlock(Base):
    __tablename__ = "sub_blocks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, default=120, nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(String(50), default="pending", nullable=False) # 'pending', 'completed', 'skipped'
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="sub_blocks")
