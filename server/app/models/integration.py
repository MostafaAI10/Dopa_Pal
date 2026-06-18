from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class IntegrationToken(Base):
    __tablename__ = "integration_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False) # 'google', 'notion', 'jira', 'canvas'
    access_token_enc = Column(Text, nullable=False)
    refresh_token_enc = Column(Text, nullable=True) # Refresh token might be empty for API-key configs
    expires_at = Column(DateTime, nullable=False)
    settings_json = Column(JSON, nullable=True) # Configurations, toggles, calendars metadata

    # Relationships
    user = relationship("User", back_populates="integration_tokens")
