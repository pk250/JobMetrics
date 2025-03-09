from sqlalchemy import Column, Integer, String, JSON, DateTime
from app.models.database import Base
from datetime import datetime

class BossCookie(Base):
    __tablename__ = 'boss_cookies'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    cookies = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    def __repr__(self):
        return f'<BossCookie {self.id}>'