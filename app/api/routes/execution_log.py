from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import ExecutionLog
from app.db.crud import execution_log_crud, spider_crud
from app.schemas.execution_log import ExecutionLogResponse, ExecutionLogCreate, ExecutionLogUpdate
from pydantic import BaseModel

router = APIRouter(prefix="/api/execution-logs", tags=["execution-logs"])

class logsModel(BaseModel):
    total: int
    logs: List[ExecutionLogResponse] 

@router.get("/", response_model=logsModel)
async def get_execution_logs(page: int = 0, limit: int = 10, db: Session = Depends(get_db)) -> Any:
    """获取执行日志列表，支持分页和倒序排列"""
    logs = execution_log_crud.get_logs_with_order(db, skip=(page-1)*limit, limit=limit)
    total = db.query(ExecutionLog).count()
    return {"total": total, "logs": logs}

@router.get("/count", response_model=Dict[str, int])
async def get_execution_logs_count(db: Session = Depends(get_db)):
    """获取执行日志总数"""
    count = db.query(ExecutionLog).count()
    return {"total": count}

@router.get("/{log_id}", response_model=ExecutionLogResponse)
async def get_execution_log(log_id: int, db: Session = Depends(get_db)):
    """获取执行日志详情"""
    log = execution_log_crud.get(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="执行日志不存在")
    return log

@router.post("/", response_model=ExecutionLogResponse)
async def create_execution_log(log: ExecutionLogCreate, db: Session = Depends(get_db)):
    """创建执行日志"""
    # 检查爬虫是否存在
    spider = spider_crud.get(db, log.spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    # 创建执行日志
    db_log = execution_log_crud.create(db, obj_in=log)
    return db_log

@router.put("/{log_id}", response_model=ExecutionLogResponse)
async def update_execution_log(log_id: int, log: ExecutionLogUpdate, db: Session = Depends(get_db)):
    """更新执行日志"""
    db_log = execution_log_crud.get(db, log_id)
    if not db_log:
        raise HTTPException(status_code=404, detail="执行日志不存在")
    
    # 更新执行日志
    update_data = log.dict(exclude_unset=True)
    updated_log = execution_log_crud.update(db, db_obj=db_log, obj_in=update_data)
    return updated_log