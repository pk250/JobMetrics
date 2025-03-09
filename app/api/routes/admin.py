from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.models.database import get_db

# 创建路由
router = APIRouter(tags=["admin"])

# 设置模板目录
templates_path = Path("app/templates")
templates = Jinja2Templates(directory=templates_path)

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """后台管理页面"""
    return templates.TemplateResponse("admin.html", {"request": request})