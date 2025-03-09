from fastapi import FastAPI
from app.api.routes import index, spider, schedule, environment, admin, execution_log, websocket
from contextlib import asynccontextmanager
from app.models.database import init_db, get_db_session
from app.services.scheduler import init_scheduler
from app.services.script_scanner import init_script_scanner
from app import setup_static_files

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在启动爬虫管理平台...")
    # 初始化数据库
    init_db()
    # 获取数据库会话
    db = get_db_session()
    # 初始化调度器
    scheduler = init_scheduler(db)
    # 初始化脚本扫描器
    script_scanner = init_script_scanner(db)
    print("爬虫管理平台启动完成")
    yield
    # 关闭调度器
    scheduler.shutdown()
    # 关闭数据库连接
    db.close()
    print("爬虫管理平台已关闭")

app = FastAPI(
    title="爬虫管理平台",
    description="一个用于管理爬虫脚本、定时任务和环境变量的平台",
    version="1.0.0",
    lifespan=lifespan
)

# 设置静态文件
setup_static_files(app)

# 注册路由
app.include_router(index.router)
app.include_router(spider.router)
app.include_router(schedule.router)
app.include_router(environment.router)
app.include_router(admin.router)
app.include_router(execution_log.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)