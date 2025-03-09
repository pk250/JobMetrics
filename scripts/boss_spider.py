import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
import time
import json
import undetected_chromedriver as uc
import requests

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 修正项目根目录路径
sys.path.insert(0, project_root)

# 导入配置，必须在设置sys.path之后
from app.core.config import settings

print(f'当前工作目录：{os.getcwd()}')
print(f'当前Python路径：{sys.path}')

# 环境变量API配置
API_BASE_URL = "http://localhost:8000"  # 根据实际部署情况调整
ENVIRONMENT_NAME = "BOSS直聘环境"
COOKIE_KEY = "BOSS_COOKIES"
USER_ID = 1  # 默认用户ID，根据实际情况调整

class Boss:
    def __init__(self):
        try:
            # 使用undetected_chromedriver自动下载匹配的驱动
            self.options = ChromeOptions()
            # self.options.add_argument('--headless')
            self.options.add_argument('--no-sandbox')
            # 禁用弹窗阻止
            self.options.add_argument('--disable-popup-blocking')
            self.options.add_argument('--disable-blink-features=AutomationControlled')
            
            # 尝试使用undetected_chromedriver的自动下载功能
            try:
                print("尝试使用undetected_chromedriver自动下载匹配的驱动...")
                self.driver = uc.Chrome(options=self.options)
                print("成功初始化Chrome驱动")
            except Exception as uc_error:
                print(f"使用undetected_chromedriver初始化失败: {str(uc_error)}")
                # 尝试使用标准selenium方式初始化
                print("尝试使用标准selenium方式初始化...")
                print(f"Chrome驱动路径: {settings.CHROME_DRIVER_PATH}")
                self.service = Service(settings.CHROME_DRIVER_PATH)
                self.driver = webdriver.Chrome(service=self.service, options=self.options)
                print("成功使用标准selenium方式初始化Chrome驱动")
                
            self.cookies = None
        except Exception as e:
            print(f"初始化Chrome驱动失败: {str(e)}")
            print("\n可能的解决方案:")
            print("1. 确保已安装Chrome浏览器")
            print("2. 更新Chrome浏览器到最新版本")
            print("3. 手动下载与您Chrome版本匹配的ChromeDriver并放置在drivers目录中")
            print("4. 尝试使用--no-sandbox参数启动浏览器")
            raise

    def login(self):
        self.driver.get('https://www.zhipin.com/web/user/?ka=header-login')
        self.driver.find_element(By.CLASS_NAME, 'wx-login-btn').click()

    def is_login(self):
        self.cookies = self.driver.get_cookies()
        for cookie in self.cookies:
            if cookie['name'] == 'wt2':
                return True
        return False

    def start(self, *args, **kwargs):
        if not self.cookies:
            print("没有可用的cookies")
            return False
        
        self.driver.get("https://www.zhipin.com/")
        try:
            for cookie in self.cookies:
                if 'name' in cookie and 'value' in cookie:
                    self.driver.add_cookie(cookie)
        except Exception as e:
            print(f"添加cookie时出错: {str(e)}")
        
        self.driver.get("https://www.zhipin.com/web/chat/index")
        time.sleep(10)
        
        if not self.is_login():
            print("cookies失效")
            return

    def save_cookies(self):
        # 保存cookies到环境变量API
        try:
            cookies_json = json.dumps(self.cookies)
            
            # 1. 获取或创建环境
            env_id = self._get_or_create_environment()
            if not env_id:
                print("无法获取或创建环境，使用备用方式保存cookies")
                # 备用：保存到环境变量
                os.environ['BOSS_COOKIES'] = cookies_json
                print("已保存cookies到环境变量(备用方式)")
                return
            
            # 2. 保存或更新环境变量
            success = self._save_environment_variable(env_id, COOKIE_KEY, cookies_json, is_secret=True)
            if success:
                print(f"已成功保存cookies到环境变量API，环境ID: {env_id}")
            else:
                # 备用：保存到环境变量
                os.environ['BOSS_COOKIES'] = cookies_json
                print("保存到API失败，已保存cookies到环境变量(备用方式)")
        except Exception as e:
            print(f"保存cookies时出错: {str(e)}")
            # 备用：保存到环境变量
            try:
                os.environ['BOSS_COOKIES'] = cookies_json
                print("已保存cookies到环境变量(备用方式)")
            except Exception as e2:
                print(f"备用保存也失败: {str(e2)}")

    def get_cookies(self):
        try:
            # 1. 尝试从API获取cookies
            env_id = self._get_environment_id()
            if env_id:
                cookies_json = self._get_environment_variable(env_id, COOKIE_KEY)
                if cookies_json:
                    print("从环境变量API获取cookies成功")
                    return json.loads(cookies_json)
            
            # 2. 如果API获取失败，尝试从环境变量获取
            cookies_env = os.environ.get('BOSS_COOKIES')
            if cookies_env:
                try:
                    print("从环境变量中获取cookies")
                    return json.loads(cookies_env)
                except json.JSONDecodeError as e:
                    print(f"解析环境变量中的cookies失败: {str(e)}")
        except Exception as e:
            print(f"获取cookies时出错: {str(e)}")
        
        return None

    def _get_or_create_environment(self):
        """获取或创建环境，返回环境ID"""
        try:
            # 1. 尝试获取已存在的环境
            env_id = self._get_environment_id()
            if env_id:
                return env_id
            
            # 2. 如果环境不存在，创建新环境
            url = f"{API_BASE_URL}/api/environments/"
            payload = {
                "name": ENVIRONMENT_NAME,
                "description": "BOSS直聘爬虫的环境变量",
                "user_id": USER_ID
            }
            response = requests.post(url, json=payload)
            
            if response.status_code == 201:
                return response.json().get("id")
            else:
                print(f"创建环境失败: {response.text}")
                return None
        except Exception as e:
            print(f"获取或创建环境时出错: {str(e)}")
            return None

    def _get_environment_id(self):
        """获取环境ID"""
        try:
            url = f"{API_BASE_URL}/api/environments/user/{USER_ID}"
            response = requests.get(url)
            
            if response.status_code == 200:
                environments = response.json()
                for env in environments:
                    if env.get("name") == ENVIRONMENT_NAME:
                        return env.get("id")
            return None
        except Exception as e:
            print(f"获取环境ID时出错: {str(e)}")
            return None

    def _save_environment_variable(self, env_id, key, value, is_secret=False):
        """保存环境变量"""
        try:
            # 1. 检查变量是否已存在
            url = f"{API_BASE_URL}/api/environments/{env_id}/variables"
            response = requests.get(url)
            
            variable_id = None
            if response.status_code == 200:
                variables = response.json()
                for var in variables:
                    if var.get("key") == key:
                        variable_id = var.get("id")
                        break
            
            # 2. 更新或创建变量
            if variable_id:
                # 更新已存在的变量
                url = f"{API_BASE_URL}/api/environments/variables/{variable_id}"
                payload = {
                    "value": value,
                    "is_secret": is_secret
                }
                response = requests.put(url, json=payload)
                return response.status_code == 200
            else:
                # 创建新变量
                url = f"{API_BASE_URL}/api/environments/variables"
                payload = {
                    "key": key,
                    "value": value,
                    "is_secret": is_secret,
                    "environment_id": env_id
                }
                response = requests.post(url, json=payload)
                return response.status_code == 201
        except Exception as e:
            print(f"保存环境变量时出错: {str(e)}")
            return False

    def _get_environment_variable(self, env_id, key):
        """获取环境变量值"""
        try:
            url = f"{API_BASE_URL}/api/environments/{env_id}/variables"
            response = requests.get(url)
            
            if response.status_code == 200:
                variables = response.json()
                for var in variables:
                    if var.get("key") == key:
                        return var.get("value")
            return None
        except Exception as e:
            print(f"获取环境变量时出错: {str(e)}")
            return None

    def stop(self):
        if self.driver:
            self.driver.quit()

def main():
    start_time = time.time()
    print("爬虫开始运行")
    
    try:
        boss = Boss()
        boss.cookies = boss.get_cookies()
        success = False
        
        if boss.cookies:
            print("使用已保存的cookies登录")
            success = boss.start()
        else:
            print("需要重新登录")
            boss.login()
            
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                if boss.is_login():
                    boss.save_cookies()
                    success = True
                    break
                time.sleep(1)
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"爬虫运行完成，耗时: {duration:.2f}秒")
        return 0 if success else 1
    except Exception as e:
        print(f"爬虫运行失败: {str(e)}")
        print("这可能是由于Chrome浏览器版本与驱动不匹配或未安装Chrome浏览器导致的。")
        print("请确保已安装Chrome浏览器，或更新Chrome浏览器到最新版本。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)