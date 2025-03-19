from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.orm import Session
from app.models import Schedule, ExecutionLog, Spider, SpiderEnvironment, EnvironmentVariable
from app.db.crud import schedule_crud, execution_log_crud, spider_crud
from datetime import datetime
import subprocess
import os
import logging
import json
import asyncio
from app.models.database import get_db_session

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SpiderScheduler:
    def __init__(self, db: Session):
        self.db = db
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("调度器已启动")

    def load_schedules(self):
        """从数据库加载所有活跃的调度任务"""
        try:
            active_schedules = schedule_crud.get_active_schedules(self.db)
            for schedule in active_schedules:
                self.add_job(schedule)
            logger.info(f"已加载 {len(active_schedules)} 个调度任务")
        except Exception as e:
            logger.error(f"加载调度任务失败: {str(e)}")

    def add_job(self, schedule):
        """添加一个调度任务"""
        try:
            spider = spider_crud.get(self.db, schedule.spider_id)
            if not spider or not spider.is_active:
                logger.warning(f"爬虫ID {schedule.spider_id} 不存在或未激活，跳过添加调度任务")
                return

            job_id = f"spider_{spider.id}_{schedule.id}"
            # 检查任务是否已存在
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除现有任务: {job_id}")

            # 添加新任务，不再传递self.db，而是传递spider_id
            self.scheduler.add_job(
                run_spider_job,  # 使用独立的函数而不是实例方法
                CronTrigger.from_crontab(schedule.cron_expression),
                id=job_id,
                args=[spider.id],
                replace_existing=True
            )
            logger.info(f"已添加调度任务: {job_id}, cron表达式: {schedule.cron_expression}")
        except Exception as e:
            logger.error(f"添加调度任务失败: {str(e)}")

    def remove_job(self, schedule_id):
        """移除一个调度任务"""
        try:
            schedule = schedule_crud.get(self.db, schedule_id)
            if not schedule:
                logger.warning(f"调度任务ID {schedule_id} 不存在")
                return

            job_id = f"spider_{schedule.spider_id}_{schedule.id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除调度任务: {job_id}")
            else:
                logger.warning(f"调度任务 {job_id} 不存在于调度器中")
        except Exception as e:
            logger.error(f"移除调度任务失败: {str(e)}")

    def update_job(self, schedule_id):
        """更新一个调度任务"""
        try:
            schedule = schedule_crud.get(self.db, schedule_id)
            if not schedule:
                logger.warning(f"调度任务ID {schedule_id} 不存在")
                return

            # 如果调度任务不再活跃，则移除它
            if not schedule.is_active:
                self.remove_job(schedule_id)
                return

            # 否则，重新添加它（会替换现有的）
            self.add_job(schedule)
        except Exception as e:
            logger.error(f"更新调度任务失败: {str(e)}")

    def get_environment_variables(self, spider_id):
        """获取爬虫的环境变量"""
        try:
            from app.db.crud import spider_environment_crud, environment_variable_crud
            # 获取爬虫关联的环境
            spider_envs = spider_environment_crud.get_by_spider(self.db, spider_id)
            env_vars = {}

            # 获取每个环境的变量
            for se in spider_envs:
                variables = environment_variable_crud.get_by_environment(self.db, se.environment_id)
                for var in variables:
                    env_vars[var.key] = var.value

            return env_vars
        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return {}

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")


# 独立的爬虫执行函数，不依赖于SpiderScheduler实例
def run_spider_job(spider_id):
    """执行爬虫脚本（同步版本）"""
    asyncio.run(run_spider_async(spider_id))


async def run_spider_async(spider_id):
    """异步执行爬虫脚本"""
    # 创建新的数据库会话
    db = get_db_session()
    try:
        # 获取爬虫信息
        spider = spider_crud.get(db, spider_id)
        if not spider or not spider.is_active:
            logger.warning(f"爬虫ID {spider_id} 不存在或未激活，跳过执行")
            return

        # 创建执行日志
        log_data = {
            "spider_id": spider_id,
            "start_time": datetime.now(),
            "status": "running",
        }
        log_entry = execution_log_crud.create(db, obj_in=log_data)
        logger.info(f"开始执行爬虫: {spider.name} (ID: {spider_id})")

        # 获取环境变量
        env_vars = get_environment_variables(db, spider_id)
        env = os.environ.copy()
        env.update(env_vars)

        # 执行爬虫脚本
        script_path = os.path.abspath(spider.script_path)
        if not os.path.exists(script_path):
            error_msg = f"爬虫脚本不存在: {script_path}"
            update_log(db, log_entry.id, "failed", error_message=error_msg)
            return

        # 获取虚拟环境python路径
        venv_python = os.path.abspath(os.path.join(os.getcwd(), '.venv', 'Scripts', 'python.exe'))
        if not os.path.exists(venv_python):
            logger.warning(f"虚拟环境Python解释器未找到: {venv_python}")
            venv_python = 'python'

        # 执行脚本并捕获输出
        process = subprocess.Popen(
            [venv_python, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        stdout, stderr = process.communicate()

        # 更新执行日志
        if process.returncode == 0:
            update_log(db, log_entry.id, "success", log_content=stdout)
            logger.info(f"爬虫执行成功: {spider.name} (ID: {spider_id})")
        else:
            update_log(db, log_entry.id, "failed", log_content=stdout, error_message=stderr)
            logger.error(f"爬虫执行失败: {spider.name} (ID: {spider_id})\n错误: {stderr}")

    except Exception as e:
        logger.error(f"执行爬虫时发生错误: {str(e)}")
        # 如果已创建日志条目，则更新它
        if 'log_entry' in locals() and log_entry:
            update_log(db, log_entry.id, "failed", error_message=str(e))
    finally:
        # 关闭数据库会话
        db.close()


def update_log(db, log_id, status, log_content=None, error_message=None):
    """更新执行日志"""
    try:
        update_data = {
            "status": status,
            "end_time": datetime.now()
        }
        if log_content:
            update_data["log_content"] = log_content
        if error_message:
            update_data["error_message"] = error_message

        execution_log_crud.update(db, db_obj=execution_log_crud.get(db, log_id), obj_in=update_data)
    except Exception as e:
        logger.error(f"更新执行日志失败: {str(e)}")


def get_environment_variables(db, spider_id):
    """获取爬虫的环境变量"""
    try:
        from app.db.crud import spider_environment_crud, environment_variable_crud
        # 获取爬虫关联的环境
        spider_envs = spider_environment_crud.get_by_spider(db, spider_id)
        env_vars = {}

        # 获取每个环境的变量
        for se in spider_envs:
            variables = environment_variable_crud.get_by_environment(db, se.environment_id)
            for var in variables:
                env_vars[var.key] = var.value

        return env_vars
    except Exception as e:
        logger.error(f"获取环境变量失败: {str(e)}")
        return {}


# 全局调度器实例
_scheduler = None


def init_scheduler(db_session):
    """初始化调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SpiderScheduler(db_session)
        _scheduler.load_schedules()
    return _scheduler


def get_scheduler():
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("调度器尚未初始化")
    return _scheduler