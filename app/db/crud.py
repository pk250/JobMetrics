from sqlalchemy.orm import Session
from app.models import User, Spider, Schedule, ExecutionLog, Environment, EnvironmentVariable, SpiderEnvironment
from typing import List, Optional, Dict, Any, Type, TypeVar, Generic

T = TypeVar('T')


class CRUDBase(Generic[T]):
    """
    基础CRUD操作类
    """
    def __init__(self, model: Type[T]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[T]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[T]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> T:
        obj = self.model(**obj_in)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, *, db_obj: T, obj_in: Dict[str, Any]) -> T:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> T:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj


class CRUDUser(CRUDBase[User]):
    """
    用户相关的CRUD操作
    """
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()


class CRUDSpider(CRUDBase[Spider]):
    """
    爬虫相关的CRUD操作
    """
    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Spider]:
        return db.query(Spider).filter(Spider.user_id == user_id).offset(skip).limit(limit).all()

    def remove(self, db: Session, *, id: int) -> Spider:
        obj = db.query(self.model).get(id)
        if obj and obj.script_path:
            try:
                import os
                if os.path.exists(obj.script_path):
                    os.remove(obj.script_path)
            except Exception as e:
                # 记录错误但继续删除数据库记录
                from app.core.logger import logger
                logger.error(f"删除爬虫脚本文件失败: {str(e)}")
        db.delete(obj)
        db.commit()
        return obj


class CRUDSchedule(CRUDBase[Schedule]):
    """
    调度相关的CRUD操作
    """
    def get_by_spider(self, db: Session, spider_id: int) -> List[Schedule]:
        return db.query(Schedule).filter(Schedule.spider_id == spider_id).all()

    def get_active_schedules(self, db: Session) -> List[Schedule]:
        return db.query(Schedule).filter(Schedule.is_active == True).all()


class CRUDExecutionLog(CRUDBase[ExecutionLog]):
    """
    执行日志相关的CRUD操作
    """
    def get_by_spider(self, db: Session, spider_id: int, skip: int = 0, limit: int = 100) -> List[ExecutionLog]:
        return db.query(ExecutionLog).filter(ExecutionLog.spider_id == spider_id).offset(skip).limit(limit).all()
        
    def get_logs_with_order(self, db: Session, skip: int = 0, limit: int = 100) -> List[ExecutionLog]:
        """获取执行日志列表，按开始时间倒序排列"""
        return db.query(ExecutionLog).order_by(ExecutionLog.start_time.desc()).offset(skip).limit(limit).all()


class CRUDEnvironment(CRUDBase[Environment]):
    """
    环境相关的CRUD操作
    """
    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Environment]:
        return db.query(Environment).filter(Environment.user_id == user_id).offset(skip).limit(limit).all()


class CRUDEnvironmentVariable(CRUDBase[EnvironmentVariable]):
    """
    环境变量相关的CRUD操作
    """
    def get_by_environment(self, db: Session, environment_id: int) -> List[EnvironmentVariable]:
        return db.query(EnvironmentVariable).filter(EnvironmentVariable.environment_id == environment_id).all()


class CRUDSpiderEnvironment(CRUDBase[SpiderEnvironment]):
    """
    爬虫环境关联相关的CRUD操作
    """
    def get_by_spider(self, db: Session, spider_id: int) -> List[SpiderEnvironment]:
        return db.query(SpiderEnvironment).filter(SpiderEnvironment.spider_id == spider_id).all()

    def get_by_environment(self, db: Session, environment_id: int) -> List[SpiderEnvironment]:
        return db.query(SpiderEnvironment).filter(SpiderEnvironment.environment_id == environment_id).all()


# 实例化CRUD对象
user_crud = CRUDUser(User)
spider_crud = CRUDSpider(Spider)
schedule_crud = CRUDSchedule(Schedule)
execution_log_crud = CRUDExecutionLog(ExecutionLog)
environment_crud = CRUDEnvironment(Environment)
environment_variable_crud = CRUDEnvironmentVariable(EnvironmentVariable)
spider_environment_crud = CRUDSpiderEnvironment(SpiderEnvironment)