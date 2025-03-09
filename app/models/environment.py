from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Environment(Base):
    __tablename__ = 'environments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = Column(Integer, ForeignKey('users.id'))

    # 关联关系
    user = relationship('User', back_populates='environments')
    variables = relationship('EnvironmentVariable', back_populates='environment')
    spider_environments = relationship('SpiderEnvironment', back_populates='environment')


class EnvironmentVariable(Base):
    __tablename__ = 'environment_variables'

    id = Column(Integer, primary_key=True, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'))
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    is_secret = Column(Boolean, default=False)  # 是否为敏感信息（如cookie）

    # 关联关系
    environment = relationship('Environment', back_populates='variables')


class SpiderEnvironment(Base):
    __tablename__ = 'spider_environments'

    id = Column(Integer, primary_key=True, index=True)
    spider_id = Column(Integer, ForeignKey('spiders.id'))
    environment_id = Column(Integer, ForeignKey('environments.id'))

    # 关联关系
    spider = relationship('Spider', back_populates='environments')
    environment = relationship('Environment', back_populates='spider_environments')