from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.crud import environment_crud, environment_variable_crud, spider_environment_crud, spider_crud
from app.models import Environment, EnvironmentVariable, SpiderEnvironment
from app.models.database import get_db
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/environments", tags=["environments"])


class EnvironmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    user_id: int


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class EnvironmentResponse(EnvironmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class EnvironmentVariableBase(BaseModel):
    key: str
    value: str
    is_secret: bool = False


class EnvironmentVariableCreate(EnvironmentVariableBase):
    environment_id: int


class EnvironmentVariableUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    is_secret: Optional[bool] = None


class EnvironmentVariableResponse(EnvironmentVariableBase):
    id: int
    environment_id: int

    class Config:
        orm_mode = True


class SpiderEnvironmentCreate(BaseModel):
    spider_id: int
    environment_id: int


class SpiderEnvironmentResponse(SpiderEnvironmentCreate):
    id: int

    class Config:
        orm_mode = True


# 环境管理API
@router.get("/", response_model=List[EnvironmentResponse])
async def get_environments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """获取所有环境，支持分页"""
    return environment_crud.get_multi(db, skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=List[EnvironmentResponse])
async def get_environments_by_user(user_id: int, db: Session = Depends(get_db)):
    """获取特定用户的所有环境"""
    environments = environment_crud.get_by_user(db, user_id)
    return environments


@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(environment_id: int, db: Session = Depends(get_db)):
    """获取特定环境"""
    environment = environment_crud.get(db, environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    return environment


@router.post("/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(environment: EnvironmentCreate, db: Session = Depends(get_db)):
    """创建新环境"""
    new_environment = environment_crud.create(db, obj_in=environment.dict())
    return new_environment


@router.put("/{environment_id}", response_model=EnvironmentResponse)
async def update_environment(environment_id: int, environment: EnvironmentUpdate, db: Session = Depends(get_db)):
    """更新环境"""
    db_environment = environment_crud.get(db, environment_id)
    if not db_environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    update_data = environment.dict(exclude_unset=True)
    updated_environment = environment_crud.update(db, db_obj=db_environment, obj_in=update_data)
    return updated_environment


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(environment_id: int, db: Session = Depends(get_db)):
    """删除环境"""
    db_environment = environment_crud.get(db, environment_id)
    if not db_environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 删除环境
    environment_crud.remove(db, id=environment_id)
    return None


# 环境变量管理API
@router.get("/{environment_id}/variables", response_model=List[EnvironmentVariableResponse])
async def get_environment_variables(environment_id: int, db: Session = Depends(get_db)):
    """获取特定环境的所有变量"""
    environment = environment_crud.get(db, environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    variables = environment_variable_crud.get_by_environment(db, environment_id)
    return variables


@router.post("/variables", response_model=EnvironmentVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_environment_variable(variable: EnvironmentVariableCreate, db: Session = Depends(get_db)):
    """创建新环境变量"""
    environment = environment_crud.get(db, variable.environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    new_variable = environment_variable_crud.create(db, obj_in=variable.dict())
    return new_variable


@router.put("/variables/{variable_id}", response_model=EnvironmentVariableResponse)
async def update_environment_variable(variable_id: int, variable: EnvironmentVariableUpdate, db: Session = Depends(get_db)):
    """更新环境变量"""
    db_variable = environment_variable_crud.get(db, variable_id)
    if not db_variable:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    update_data = variable.dict(exclude_unset=True)
    updated_variable = environment_variable_crud.update(db, db_obj=db_variable, obj_in=update_data)
    return updated_variable


@router.delete("/variables/{variable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment_variable(variable_id: int, db: Session = Depends(get_db)):
    """删除环境变量"""
    db_variable = environment_variable_crud.get(db, variable_id)
    if not db_variable:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    environment_variable_crud.remove(db, id=variable_id)
    return None


# 爬虫环境关联API
@router.get("/spider/{spider_id}", response_model=List[EnvironmentResponse])
async def get_spider_environments(spider_id: int, db: Session = Depends(get_db)):
    """获取特定爬虫关联的所有环境"""
    spider = spider_crud.get(db, spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    # 获取爬虫关联的环境ID
    spider_envs = spider_environment_crud.get_by_spider(db, spider_id)
    environment_ids = [se.environment_id for se in spider_envs]
    
    # 获取环境详情
    environments = [environment_crud.get(db, env_id) for env_id in environment_ids]
    return [env for env in environments if env is not None]


@router.post("/spider", response_model=SpiderEnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def link_spider_environment(link: SpiderEnvironmentCreate, db: Session = Depends(get_db)):
    """关联爬虫和环境"""
    # 检查爬虫和环境是否存在
    spider = spider_crud.get(db, link.spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    environment = environment_crud.get(db, link.environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 检查关联是否已存在
    existing = spider_environment_crud.get_by_spider_and_environment(db, link.spider_id, link.environment_id)
    if existing:
        raise HTTPException(status_code=400, detail="爬虫和环境已关联")
    
    # 创建关联
    new_link = spider_environment_crud.create(db, obj_in=link.dict())
    return new_link


@router.delete("/spider/{spider_id}/environment/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_spider_environment(spider_id: int, environment_id: int, db: Session = Depends(get_db)):
    """解除爬虫和环境的关联"""
    # 检查爬虫和环境是否存在
    spider = spider_crud.get(db, spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    
    environment = environment_crud.get(db, environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 检查关联是否存在
    existing = spider_environment_crud.get_by_spider_and_environment(db, spider_id, environment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="爬虫和环境未关联")
    
    # 删除关联
    spider_environment_crud.remove(db, id=existing.id)
    return None