from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    CHROME_DRIVER_PATH: str = 'D:/tools/chromedriver/chromedriver.exe'
    BOSS_LOGIN_TIMEOUT: int = 60
    BOSS_COOKIE_DB: str = 'boss_cookies.db'
    BOSS_LOGIN_URL: str = 'https://www.zhipin.com/web/user/?ka=header-login'
    BOSS_CHAT_URL: str = 'https://www.zhipin.com/web/chat/index'

    class Config:
        env_file = ".env"

settings = Settings()