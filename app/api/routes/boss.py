from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.services.boss_service import BossService
from app.models.database import get_db
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/boss", tags=["boss"])

class BossLoginRequest(BaseModel):
    user_id: int

class BossStatusResponse(BaseModel):
    status: str
    last_login: Optional[datetime] = None
    cookies_valid: bool = False

@router.post("/login", status_code=status.HTTP_202_ACCEPTED)
async def boss_login(request: BossLoginRequest, db: Session = Depends(get_db)):
    try:
        service = BossService(user_id=request.user_id)
        service.login(db)
        return {"message": "登录流程已启动，请扫码认证"}
    except Exception as e:
        logger.error(f"BOSS登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="登录初始化失败")

@router.get("/status/{user_id}", response_model=BossStatusResponse)
async def check_boss_status(user_id: int, db: Session = Depends(get_db)):
    try:
        service = BossService(user_id=user_id)
        status = service.check_login_status(db)
        return {
            "status": "authenticated" if status else "unauthenticated",
            "cookies_valid": status
        }
    except Exception as e:
        logger.error(f"状态检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="状态检查失败")

@router.post("/execute/{user_id}")
async def execute_boss_spider(user_id: int, db: Session = Depends(get_db)):
    try:
        service = BossService(user_id=user_id)
        result = service.execute(db)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"爬虫执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="爬虫执行失败")