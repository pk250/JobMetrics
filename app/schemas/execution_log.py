from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.spider import SpiderResponse


class ExecutionLogBase(BaseModel):
    """执行日志基础模型"""
    spider_id: Optional[int] = None
    status: str  # 'success', 'failed', 'running'
    log_content: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionLogCreate(ExecutionLogBase):
    """创建执行日志模型"""
    start_time: datetime
    end_time: Optional[datetime] = None


class ExecutionLogUpdate(BaseModel):
    """更新执行日志模型"""
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    log_content: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionLogResponse(ExecutionLogBase):
    """执行日志响应模型"""
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    spider: Optional[SpiderResponse] = None

    class Config:
        orm_mode = True