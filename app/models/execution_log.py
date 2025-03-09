from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class ExecutionLog(Base):
    __tablename__ = 'execution_logs'

    id = Column(Integer, primary_key=True, index=True)
    spider_id = Column(Integer, ForeignKey('spiders.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'running'
    log_content = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # 关联关系
    spider = relationship('Spider', back_populates='execution_logs')