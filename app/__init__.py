# 导出应用包
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 导出模块
__all__ = ['setup_static_files']

# 设置静态文件
def setup_static_files(app):
    """设置静态文件目录"""
    static_dir = Path("app/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")