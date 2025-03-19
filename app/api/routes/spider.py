from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Body, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pathlib import Path
from app.db.crud import spider_crud
from app.models import Spider
from app.models.database import get_db
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
import tempfile
import subprocess
import sys
import time

router = APIRouter(prefix="/api/spiders", tags=["spiders"])

# 新增脚本管理路由
from app.core.config import settings
import re

# 脚本存储目录配置
SCRIPTS_ROOT = Path('data/spider_scripts').resolve()
SCRIPT_DIR = Path(settings.BASE_DIR) / "scripts"
SCRIPT_DIR.mkdir(exist_ok=True, parents=True)

def validate_script_path(relative_path):
    try:
        secured_path = re.sub(r'[^\w_.-]', '_', relative_path)
        full_path = (SCRIPTS_ROOT / secured_path).resolve()
        if SCRIPTS_ROOT.resolve() not in full_path.parents:
            return None
        return full_path
    except Exception:
        return None

@router.post("/upload-script")
async def upload_spider_script(file: UploadFile = File(...)):
    if not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="只支持Python脚本文件")
    
    try:
        script_path = SCRIPT_DIR / file.filename
        with script_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"path": str(script_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.post("/save-script")
async def save_spider_script(data: dict = Body(...)):
    if not data or 'path' not in data or 'content' not in data:
        raise HTTPException(status_code=400, detail="缺少必要参数")

    target_path = validate_script_path(data['path'])
    if not target_path:
        raise HTTPException(status_code=400, detail="非法文件路径")

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        return JSONResponse({"status": "success", "path": str(target_path.relative_to(SCRIPTS_ROOT))})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'文件操作失败: {str(e)}')

@router.get("/script-content")
async def get_spider_script(path: str):
    try:
        filename = Path(path).name
        script_path = SCRIPT_DIR / filename
        if not script_path.resolve().is_relative_to(SCRIPT_DIR):
            raise HTTPException(status_code=400, detail="非法路径访问")
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="脚本不存在")
            
        return script_path.read_text(encoding='utf-8')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")


class SpiderBase(BaseModel):
    name: str
    description: Optional[str] = None
    script_path: str
    is_active: bool = True


class SpiderCreate(SpiderBase):
    user_id: int


class SpiderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    is_active: Optional[bool] = None


class TestResult(BaseModel):
    task_id: str
    status: str
    logs: str
    execution_time: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class SpiderTestTask(BaseModel):
    id: int
    script_path: str
    status: str
    logs: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    execution_time: Optional[float] = None

class SpiderResponse(SpiderBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


@router.get("/", response_model=List[SpiderResponse])
async def get_spiders(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取爬虫列表，支持分页和搜索"""
    if search:
        # 如果有搜索关键词，执行模糊搜索
        spiders = db.query(Spider).filter(
            (Spider.name.ilike(f"%{search}%")) |
            (Spider.description.ilike(f"%{search}%"))
        ).offset(skip).limit(limit).all()
    else:
        # 否则返回所有爬虫
        spiders = spider_crud.get_multi(db, skip=skip, limit=limit)
    return spiders


@router.get("/{spider_id}", response_model=SpiderResponse)
async def get_spider(spider_id: int, db: Session = Depends(get_db)):
    """获取特定爬虫"""
    spider = spider_crud.get(db, spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    return spider


@router.post("/", response_model=SpiderResponse, status_code=status.HTTP_201_CREATED)
async def create_spider(spider: SpiderCreate, db: Session = Depends(get_db)):
    """创建新爬虫"""
    # 检查脚本路径是否存在
    if not os.path.exists(spider.script_path):
        raise HTTPException(status_code=400, detail="脚本路径不存在")
    
    # 创建爬虫
    new_spider = spider_crud.create(db, obj_in=spider.dict())
    return new_spider





@router.put("/{spider_id}", response_model=SpiderResponse)
async def update_spider(spider_id: int, spider: SpiderUpdate, db: Session = Depends(get_db)):
    """更新爬虫"""
    db_spider = spider_crud.get(db, spider_id)
    if not db_spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    # 如果更新了脚本路径，检查新路径是否存在
    if spider.script_path and not os.path.exists(spider.script_path):
        raise HTTPException(status_code=400, detail="脚本路径不存在")
    
    # 更新爬虫
    update_data = spider.dict(exclude_unset=True)
    updated_spider = spider_crud.update(db, db_obj=db_spider, obj_in=update_data)
    
    # 如果爬虫被禁用，更新相关调度任务的状态
    if spider.is_active is False:
        from app.db.crud import schedule_crud
        schedules = schedule_crud.get_by_spider(db, spider_id)
        for schedule in schedules:
            schedule_crud.update(db, db_obj=schedule, obj_in={"is_active": False})
    
    return updated_spider

@router.delete("/{spider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spider(spider_id: int, db: Session = Depends(get_db)):
    """删除爬虫"""
    db_spider = spider_crud.get(db, spider_id)
    if not db_spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    # 删除爬虫
    spider_crud.remove(db, id=spider_id)
    return None


@router.get("/count", response_model=Dict[str, int])
async def get_spiders_count(db: Session = Depends(get_db)):
    """获取爬虫总数"""
    count = db.query(Spider).count()
    return {"total": count}