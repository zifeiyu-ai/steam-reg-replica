import time
from curl_cffi import requests


STEAM_SITEKEY = 'e18a349a-46c2-46a0-87b8-74be79345c92'
STEAM_REFERER = 'https://store.steampowered.com/join/'


class CaptchaSolver:
    def __init__(self, log_callback=None):
        self.log = log_callback or (lambda msg: None)

    def createtask(self, sitekey):
        raise NotImplementedError

    def gettask(self):
        raise NotImplementedError

    def solve(self, sitekey):
        if not self.createtask(sitekey):
            return ''
        return self.gettask()


class CapRunSolver(CaptchaSolver):
    def __init__(self, key, log_callback=None):
        super().__init__(log_callback)
        self.key = key
        self.client = requests.Session(impersonate='chrome')
        self.headers = {'Authorization': f'Bearer {key}'}
        self.taskid = None

    def createtask(self, sitekey):
        data = {
            'captchaType': 'HCaptchaSteam',
            'siteReferer': STEAM_REFERER,
            'siteKey': sitekey,
        }
        for attempt in range(3):
            try:
                resp = self.client.post(
                    'https://api.captcha-run.com/v2/tasks',
                    headers=self.headers,
                    json=data,
                    timeout=15,
                )
                body = resp.json()
                if resp.status_code not in (200, 201):
                    self.log(f'打码创建任务HTTP {resp.status_code}: {body}')
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    return False
                self.taskid = body.get('taskId')
                if not self.taskid:
                    self.log(f'打码创建任务无taskId: {body}')
                    return False
                self.log(f'打码任务已创建 taskId={self.taskid}')
                return True
            except Exception as e:
                self.log(f'打码创建任务异常({attempt+1}/3): {e}')
                if attempt < 2:
                    time.sleep(3)
        return False

    def gettask(self):
        start = time.time()
        url = f'https://api.captcha-run.com/v2/tasks/{self.taskid}'
        while time.time() - start <= 180:
            try:
                resp = self.client.get(url, headers=self.headers, timeout=15)
                data = resp.json()
                status = data.get('status', '')
                if status == 'Success':
                    token = data.get('response', {}).get('token', '')
                    self.log(f'打码成功 耗时{int(time.time()-start)}秒')
                    return token
                if status == 'Fail':
                    self.log(f'打码任务失败: {data}')
                    return ''
                time.sleep(3)
            except Exception as e:
                self.log(f'打码查询异常: {e}')
                time.sleep(3)
        self.log('打码超时 180秒')
        return ''


class CaptchaLySolver(CaptchaSolver):
    def __init__(self, key, proxy=None):
        self.key = key
        self.proxy = proxy
        self.client = requests.Session()

    def createtask(self, sitekey):
        proxy_param = self.proxy or ''
        url = (
            f'https://v1.captchaly.com/hcaptcha-enterprise'
            f'?sitekey={sitekey}'
            f'&url=https://store.steampowered.com/join'
            f'&proxy={proxy_param}'
        )
        headers = {'x-api-key': self.key}
        try:
            resp = self.client.get(url, headers=headers, timeout=180)
            self._token = resp.json().get('token', '')
            return bool(self._token)
        except Exception:
            return False

    def gettask(self):
        return getattr(self, '_token', '')


class CustomServerSolver(CaptchaSolver):
    SERVER_URL = 'http://192.158.229.140:31081'

    def __init__(self, key):
        self.key = key
        self.headers = {'x-api-key': key}
        self.client = requests.Session()
        self.taskid = None

    def createtask(self, sitekey):
        data = {
            'captchaType': 'HCaptchaSteam',
            'siteReferer': STEAM_REFERER,
            'siteKey': sitekey,
        }
        try:
            resp = self.client.post(
                f'{self.SERVER_URL}/task/submit',
                headers=self.headers,
                json=data,
            )
            self.taskid = resp.json().get('task_id')
            return self.taskid is not None
        except Exception:
            return False

    def gettask(self):
        start = time.time()
        url = f'{self.SERVER_URL}/task/result/{self.taskid}'
        while time.time() - start <= 180:
            try:
                resp = self.client.get(url, headers=self.headers)
                data = resp.json()
                status = data.get('status', '')
                if status == 'SUCCESS':
                    return data.get('token', '')
                if status == 'FAIL':
                    return ''
                time.sleep(1)
            except Exception:
                time.sleep(1)
        return ''


def create_solver(backend_type, key, proxy=None, log_callback=None):
    if backend_type == 'caprun':
        return CapRunSolver(key, log_callback)
    elif backend_type == 'captchaly':
        return CaptchaLySolver(key, proxy)
    elif backend_type == 'custom':
        return CustomServerSolver(key)
    else:
        return CapRunSolver(key, log_callback)
