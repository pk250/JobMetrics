from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.crud import schedule_crud, spider_crud
from app.models import Schedule
from app.models.database import get_db
from pydantic import BaseModel
from datetime import datetime
from app.services.scheduler import get_scheduler

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ScheduleBase(BaseModel):
    spider_id: Optional[int] = None
    cron_expression: str
    is_active: bool = True


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


@router.get("/", response_model=List[ScheduleResponse])
async def get_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有调度任务"""
    schedules = schedule_crud.get_multi(db, skip=skip, limit=limit)
    return schedules


@router.get("/spider/{spider_id}", response_model=List[ScheduleResponse])
async def get_schedules_by_spider(spider_id: int, db: Session = Depends(get_db)):
    """获取特定爬虫的所有调度任务"""
    # 检查爬虫是否存在
    spider = spider_crud.get(db, spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    schedules = schedule_crud.get_by_spider(db, spider_id)
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """获取特定调度任务"""
    schedule = schedule_crud.get(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    return schedule


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(schedule: ScheduleCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """创建新调度任务"""
    # 检查爬虫是否存在
    spider = spider_crud.get(db, schedule.spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    # 创建调度任务
    new_schedule = schedule_crud.create(db, obj_in=schedule.dict())
    
    # 在后台添加到调度器
    background_tasks.add_task(add_job_to_scheduler, new_schedule.id)
    
    return new_schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, schedule: ScheduleUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """更新调度任务"""
    db_schedule = schedule_crud.get(db, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    
    # 更新调度任务
    update_data = schedule.dict(exclude_unset=True)
    updated_schedule = schedule_crud.update(db, db_obj=db_schedule, obj_in=update_data)
    
    # 在后台更新调度器中的任务
    background_tasks.add_task(update_job_in_scheduler, updated_schedule.id)
    
    return updated_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """删除调度任务"""
    db_schedule = schedule_crud.get(db, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="调度任务不存在")
    
    # 在后台从调度器中移除任务
    remove_job_from_scheduler(schedule_id)
    # 删除调度任务
    schedule_crud.remove(db, id=schedule_id)
    return None


# 辅助函数，用于在后台操作调度器
def add_job_to_scheduler(schedule_id: int):
    """将任务添加到调度器"""
    try:
        scheduler = get_scheduler()
        scheduler.update_job(schedule_id)
    except Exception as e:
        print(f"添加调度任务失败: {str(e)}")


def update_job_in_scheduler(schedule_id: int):
    """更新调度器中的任务"""
    try:
        scheduler = get_scheduler()
        scheduler.update_job(schedule_id)
    except Exception as e:
        print(f"更新调度任务失败: {str(e)}")


def remove_job_from_scheduler(schedule_id: int):
    """从调度器中移除任务"""
    try:
        scheduler = get_scheduler()
        scheduler.remove_job(schedule_id)
    except Exception as e:
        from app.services.scheduler import logger
        logger.error(f"移除调度任务失败: {str(e)}")
        raise

from typing import Dict

@router.get("/count", response_model=Dict[str, int])
async def get_schedules_count(db: Session = Depends(get_db)):
    """获取调度任务总数"""
    count = db.query(Schedule).count()
    return {"total": count}