from sqlalchemy import Column, Integer, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class StateLog(Base):
    __tablename__ = "state_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    wake_time = Column(DateTime, nullable=True)
    startup_time = Column(DateTime, nullable=False)
    mood_score = Column(Integer, nullable=False) # Scales 1 to 5
    computed_state_score = Column(Float, nullable=False) # 0 to 100

    # Relationships
    user = relationship("User", back_populates="state_logs")
