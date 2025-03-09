from .index import router as index_router
from .spider import router as spider_router
from .schedule import router as schedule_router
from .environment import router as environment_router
from .admin import router as admin_router

__all__ = [
    'index_router',
    'spider_router',
    'schedule_router',
    'environment_router',
    'admin_router'
]