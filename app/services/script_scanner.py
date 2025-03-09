import os
import re
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.crud import spider_crud
from app.models import Spider
from apscheduler.schedulers.background import BackgroundScheduler

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScriptScanner:
    """脚本扫描器，用于自动扫描scripts目录下的Python文件并更新到数据库中"""
    
    def __init__(self, db_session: Session):
        """初始化脚本扫描器
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.scripts_dir = Path("scripts")
        self.scheduler = None
    
    def start_scheduler(self):
        """启动定时扫描任务"""
        if self.scheduler is None:
            self.scheduler = BackgroundScheduler()
            # 每小时扫描一次脚本目录
            self.scheduler.add_job(self.scan_scripts, 'interval', hours=1)
            self.scheduler.start()
            logger.info("脚本扫描定时任务已启动")
    
    def stop_scheduler(self):
        """停止定时扫描任务"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.scheduler = None
            logger.info("脚本扫描定时任务已停止")
    
    def scan_scripts(self):
        """扫描脚本目录，更新数据库中的脚本信息"""
        try:
            logger.info(f"开始扫描脚本目录: {self.scripts_dir}")
            
            # 获取所有Python脚本文件
            script_files = list(self.scripts_dir.glob("*.py"))
            logger.info(f"找到 {len(script_files)} 个Python脚本文件")
            
            # 获取数据库中已有的脚本记录
            existing_spiders = spider_crud.get_multi(self.db)
            existing_paths = {spider.script_path for spider in existing_spiders}
            
            # 处理每个脚本文件
            for script_file in script_files:
                script_path = str(script_file.absolute())
                
                # 如果脚本已存在于数据库中，跳过
                if script_path in existing_paths:
                    logger.debug(f"脚本已存在于数据库中: {script_path}")
                    continue
                
                # 提取脚本元数据
                metadata = self.extract_script_metadata(script_file)
                
                # 创建新的爬虫记录
                spider_data = {
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "script_path": script_path,
                    "is_active": True,
                    "user_id": 1  # 默认用户ID，可以根据实际情况调整
                }
                
                # 保存到数据库
                new_spider = spider_crud.create(self.db, obj_in=spider_data)
                logger.info(f"已添加新爬虫: {new_spider.name} (ID: {new_spider.id})")
            
            logger.info("脚本扫描完成")
            return True
        except Exception as e:
            logger.error(f"扫描脚本目录失败: {str(e)}")
            return False
    
    def extract_script_metadata(self, script_file: Path) -> dict:
        """从脚本文件中提取元数据
        
        Args:
            script_file: 脚本文件路径
            
        Returns:
            包含脚本元数据的字典
        """
        try:
            # 默认元数据
            metadata = {
                "name": script_file.stem,  # 使用文件名作为默认名称
                "description": ""
            }
            
            # 读取文件内容
            content = script_file.read_text(encoding="utf-8")
            
            # 尝试从文件注释中提取描述
            doc_match = re.search(r'"""([\s\S]*?)"""', content)
            if doc_match:
                doc_text = doc_match.group(1).strip()
                # 提取第一行作为名称（如果有）
                lines = doc_text.split('\n')
                if lines and lines[0].strip():
                    metadata["name"] = lines[0].strip()
                # 剩余行作为描述
                if len(lines) > 1:
                    metadata["description"] = '\n'.join(lines[1:]).strip()
            
            # 尝试从类名提取更好的名称
            class_match = re.search(r'class\s+([A-Za-z0-9_]+)\s*[:\(]', content)
            if class_match:
                class_name = class_match.group(1)
                # 如果类名以Spider结尾，使用它作为名称的一部分
                if class_name.endswith("Spider"):
                    base_name = class_name[:-6]  # 移除"Spider"后缀
                    if base_name:
                        metadata["name"] = f"{base_name}爬虫"
            
            return metadata
        except Exception as e:
            logger.error(f"提取脚本元数据失败: {str(e)}")
            # 返回默认元数据
            return {
                "name": script_file.stem,
                "description": ""
            }

# 初始化脚本扫描器
def init_script_scanner(db_session: Session):
    """初始化脚本扫描器
    
    Args:
        db_session: 数据库会话
        
    Returns:
        初始化后的脚本扫描器实例
    """
    scanner = ScriptScanner(db_session)
    # 立即执行一次扫描
    scanner.scan_scripts()
    # 启动定时扫描任务
    scanner.start_scheduler()
    return scanner