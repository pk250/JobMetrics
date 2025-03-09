from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/")
async def root():
    return {"message": "爬虫管理平台API"}