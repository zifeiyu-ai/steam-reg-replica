import os
import random
import threading
import time

from captcha_solver import create_solver, STEAM_SITEKEY
from steam_api import SteamAPI
from getmail import pyimap, pypop, wrgraph
from utils import generate_random_string, generate_random_string2


class rec:
    def __init__(self, email_info, config, proxy=None, log_callback=None,
                 mail_type=0, captcha_key='', account_fmt=8, password_fmt=12,
                 captcha_backend='caprun'):
        self.email_info = email_info
        self.email = email_info['email']
        self.email_password = email_info.get('password', '')
        self.refresh_token = email_info.get('refresh_token', '')
        self.client_id = email_info.get('client_id', '')
        self.config = config
        self.proxy = proxy
        self.log = log_callback or (lambda msg: None)
        self.mail_type = mail_type
        self.captcha_key = captcha_key
        self.account_fmt = account_fmt
        self.password_fmt = password_fmt
        self.captcha_backend = captcha_backend
        self.isstop = False
        self._thread = None
        self.account_name = ''
        self.account_password = ''

    def setcs(self, mail_type=None, captcha_key=None, account_fmt=None,
              password_fmt=None, captcha_backend=None, proxy=None):
        if mail_type is not None:
            self.mail_type = mail_type
        if captcha_key is not None:
            self.captcha_key = captcha_key
        if account_fmt is not None:
            self.account_fmt = account_fmt
        if password_fmt is not None:
            self.password_fmt = password_fmt
        if captcha_backend is not None:
            self.captcha_backend = captcha_backend
        if proxy is not None:
            self.proxy = proxy

    def ipinit(self):
        if not self.proxy:
            self.log('未使用代理IP, 直连模式')
            return True
        self.log(f'代理IP: {self.proxy}')
        return True

    def getip(self):
        return self.ipinit()

    def randuser(self):
        self.account_name = generate_random_string(self.account_fmt)
        self.account_password = generate_random_string2(self.password_fmt)
        return self.account_name, self.account_password

    def gettoken(self, sitekey=None):
        sitekey = sitekey or STEAM_SITEKEY
        solver = create_solver(self.captcha_backend, self.captcha_key, self.proxy, log_callback=self.log)
        token = solver.solve(sitekey)
        if token:
            self.log(f'{self.email} 打码成功')
        else:
            self.log(f'{self.email} 打码失败')
        return token

    def getmail(self, timeout=60):
        try:
            if self.mail_type == 0:
                conn = pyimap(self.email, self.email_password)
            elif self.mail_type == 1:
                conn = pypop(self.email, self.email_password)
            elif self.mail_type == 2:
                if not self.refresh_token:
                    self.log(f'{self.email} 无refresh_token, 无法使用Graph API')
                    return ''
                conn = wrgraph(self.email, self.refresh_token, self.client_id or None)
            else:
                return ''
            link = conn.getsteamreg(timeout=timeout)
            if link:
                self.log(f'{self.email} 收取验证邮件成功')
            else:
                self.log(f'{self.email} 获取注册邮件失败')
            try:
                conn.close()
            except Exception:
                pass
            return link
        except Exception as e:
            self.log(f'{self.email} 收取邮件异常: {e}')
            return ''

    def yxjc(self):
        try:
            if self.mail_type == 0:
                conn = pyimap(self.email, self.email_password)
            elif self.mail_type == 1:
                conn = pypop(self.email, self.email_password)
            elif self.mail_type == 2:
                if not self.refresh_token:
                    return False
                conn = wrgraph(self.email, self.refresh_token, self.client_id or None)
            else:
                return False
            result = conn.test()
            try:
                conn.close()
            except Exception:
                pass
            if result:
                self.log(f'{self.email} 邮箱检测成功')
            else:
                self.log(f'{self.email} 邮箱检测失败,不可用')
            return result
        except Exception as e:
            self.log(f'{self.email} 邮箱检测异常: {e}')
            return False

    def createuser(self, accountname, password, creation_sessionid, stoken=None):
        with SteamAPI(self.proxy) as st:
            success, result = st.createuser(accountname, password, creation_sessionid, stoken=stoken)
            if success:
                self.log(f'{self.email} 注册成功')
            else:
                self.log(f'{self.email} 注册失败')
            return success, result

    def verifyaccount(self, stoken, creationid):
        with SteamAPI(self.proxy) as st:
            return st.verifyaccount(stoken, creationid)

    def run(self):
        self.log(f'{self.email} 开始注册流程')
        if self.isstop:
            self.log(f'{self.email} 任务停止')
            return False

        if not self.getip():
            self.log(f'{self.email} 无可用代理IP')
            return False

        if not self.yxjc():
            return False

        if self.isstop:
            self.log(f'{self.email} 任务停止')
            return False

        with SteamAPI(self.proxy) as st:
            self.log(f'{self.email} 访问注册页面建立会话...')
            st.visit_join_page()

            max_captcha_retries = 5
            captcha_ok = False
            for attempt in range(max_captcha_retries):
                if self.isstop:
                    self.log(f'{self.email} 任务停止')
                    return False

                if not st.getrefreshcaptcha():
                    self.log(f'{self.email} 获取验证码挑战失败')
                    return False
                self.log(f'{self.email} 获取验证码成功 gid={st.gid} (第{attempt+1}次)')

                token = self.gettoken(st.sitekey)
                if not token:
                    self.log(f'{self.email} 打码失败 (第{attempt+1}/{max_captcha_retries}次)')
                    if attempt < max_captcha_retries - 1:
                        self.log(f'{self.email} 重新获取验证码挑战重试...')
                        time.sleep(2)
                        continue
                    self.log(f'{self.email} 打码重试次数用尽')
                    return False
                captcha_ok = True
                break

            mail_ok, mail_result = st.sendmail(token, self.email)
            if not mail_ok:
                self.log(f'{self.email} 发送验证邮件失败: {mail_result}')
                return False
            self.log(f'{self.email} 验证邮件已发送')

            if self.isstop:
                self.log(f'{self.email} 任务停止')
                return False

            link = self.getmail(timeout=60)
            if not link:
                return False

            from steam_api import SteamAPI as _SA
            import re
            match = re.search(r'stoken=([a-f0-9]+)&creationid=(\d+)', link)
            if not match:
                self.log(f'{self.email} 提取验证链接参数失败')
                return False
            stoken = match.group(1)
            creationid = match.group(2)

            self.log(f'{self.email} 访问验证链接 creationid={creationid}')
            if not st.verifyaccount(stoken, creationid):
                self.log(f'{self.email} 账号验证失败')
                return False

            if self.isstop:
                self.log(f'{self.email} 任务停止')
                return False

            self.randuser()
            success, result = st.createuser(
                self.account_name, self.account_password,
                creation_sessionid=creationid,
                stoken=stoken,
            )
            if success:
                refresh_token = result.get('refresh_token', '')
                self.log(f'{self.email} 注册成功! 账号:{self.account_name} 密码:{self.account_password}')
                self.writetxt(success=True, refresh_token=refresh_token)
                return True
            else:
                self.log(f'{self.email} 注册失败: {result}')
                self.writetxt(success=False)
                return False

    def writetxt(self, success=True, refresh_token=''):
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output.txt')
        mode = 'a' if os.path.exists(output_path) else 'w'
        with open(output_path, mode, encoding='utf-8') as f:
            if success:
                line = f'{self.email}----{self.account_name}----{self.account_password}'
                if refresh_token:
                    line += f'----{refresh_token}'
                f.write(line + '\n')
            else:
                f.write(f'{self.email}----失败\n')

    def start(self):
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self):
        self.isstop = True
