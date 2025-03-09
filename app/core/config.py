import os
import platform
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # 根据操作系统选择正确的驱动路径
    @property
    def CHROME_DRIVER_PATH(self) -> str:
        system = platform.system().lower()
        if system == 'windows':
            driver_name = 'chromedriver.exe'
            driver_dir = 'windows'
        elif system == 'darwin':  # macOS
            driver_name = 'chromedriver'
            driver_dir = 'mac'
        else:  # Linux and others
            driver_name = 'chromedriver'
            driver_dir = 'linux'
        
        # 构建相对于项目根目录的驱动路径
        return str(self.BASE_DIR / 'drivers' / driver_dir / driver_name)
        
    class Config:
        env_file = ".env"

settings = Settings()