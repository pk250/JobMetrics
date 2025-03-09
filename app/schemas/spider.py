from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SpiderBase(BaseModel):
    """爬虫基础模型"""
    name: str
    description: Optional[str] = None
    script_path: str
    is_active: bool = True


class SpiderCreate(SpiderBase):
    """创建爬虫模型"""
    user_id: int


class SpiderUpdate(BaseModel):
    """更新爬虫模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    is_active: Optional[bool] = None


class SpiderResponse(SpiderBase):
    """爬虫响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        orm_mode = True