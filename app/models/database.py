from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from .base import Base

# 数据库URL
DATABASE_URL = "sqlite:///spider_manager.db"

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """获取数据库会话"""
    return SessionLocal()


def get_db():
    """依赖项，用于获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()