from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
from app.config import settings
from app.db.crud import boss_cookie_crud
from app.models.database import get_db
from sqlalchemy.orm import Session
import time
import json
import logging

logger = logging.getLogger(__name__)

class BossService:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.service = Service(settings.CHROME_DRIVER_PATH)
        self.options = ChromeOptions()
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = uc.Chrome(service=self.service, options=self.options)
        
    def _save_cookies(self, db: Session):
        cookies = self.driver.get_cookies()
        boss_cookie_crud.create(db, obj_in={
            'user_id': self.user_id,
            'cookies': json.dumps(cookies),
            'expires_at': datetime.utcnow() + timedelta(days=7)
        })
        logger.info(f'Saved cookies for user {self.user_id}')

    def login(self, db: Session):
        try:
            self.driver.get(settings.BOSS_LOGIN_URL)
            self.driver.find_element(By.CLASS_NAME, 'wx-login-btn').click()
            logger.info('Initiated WeChat login process')
        except Exception as e:
            logger.error(f'Login initiation failed: {str(e)}')
            raise

    def check_login_status(self, db: Session):
        cookies = self.driver.get_cookies()
        if any(c['name'] == 'wt2' for c in cookies):
            self._save_cookies(db)
            return True
        return False

    def execute(self, db: Session):
        try:
            cookies_record = boss_cookie_crud.get_by_user(db, self.user_id)
            if cookies_record:
                self._load_cookies(cookies_record.cookies)
                return self._start_scraping(db)
            return {'status': 'error', 'message': 'No valid cookies found'}
        except Exception as e:
            logger.error(f'Scraping failed: {str(e)}')
            raise