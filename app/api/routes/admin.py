from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.models.database import get_db

# 创建路由
router = APIRouter(prefix="/admin",tags=["admin"])

# 设置模板目录
templates_path = Path("app/templates")
templates = Jinja2Templates(directory=templates_path)

@router.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    """后台管理页面"""
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/resumemanager", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """初筛页面"""
    return templates.TemplateResponse("resumemanager.html", {"request": request})

@router.get("/joblists", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """职位列表页面"""
    return templates.TemplateResponse("joblists.html", {"request": request})

@router.get("/spidermanager", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """脚本管理页面"""
    return templates.TemplateResponse("spidermanager.html", {"request": request})

@router.get("/spideredit", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """脚本管理页面"""
    return templates.TemplateResponse("spideredit.html", {"request": request})

@router.get("/spidercookie", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """账号管理页面"""
    return templates.TemplateResponse("spidercookie.html", {"request": request})

@router.get("/spiderule", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """规则管理页面"""
    return templates.TemplateResponse("spiderule.html", {"request": request})

@router.get("/spiderlogs", response_class=HTMLResponse)
async def admin_users_page(request: Request, db=Depends(get_db)):
    """日志管理页面"""
    return templates.TemplateResponse("spiderlogs.html", {"request": request})