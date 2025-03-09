from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Spider(Base):
    __tablename__ = 'spiders'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    script_path = Column(String(255), nullable=False)  # 爬虫脚本的路径
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = Column(Integer, ForeignKey('users.id'))

    # 关联关系
    user = relationship('User', back_populates='spiders')
    schedules = relationship('Schedule', back_populates='spider')
    execution_logs = relationship('ExecutionLog', back_populates='spider')
    environments = relationship('SpiderEnvironment', back_populates='spider')