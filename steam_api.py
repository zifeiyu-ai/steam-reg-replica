import random
import re

from curl_cffi import requests

STEAM_SITEKEY = 'e18a349a-46c2-46a0-87a8-74be79345c92'

VERIFICATION_LINK_PATTERN = re.compile(
    r'https://store\.steampowered\.com/account/newaccountverification\?stoken=[a-f0-9]+&creationid=\d+'
)


class SteamAPI:
    def __init__(self, proxy=None, impersonate='chrome'):
        self.client = requests.Session(impersonate=impersonate)
        if proxy:
            self.client.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}',
            }
        self.gid = None
        self.sitekey = None
        self.creation_sessionid = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def _default_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://store.steampowered.com',
            'Referer': 'https://store.steampowered.com/join',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

    def visit_join_page(self):
        for attempt in range(3):
            try:
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                              'image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
                    'sec-ch-ua': '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                }
                resp = self.client.get(
                    'https://store.steampowered.com/join',
                    headers=headers,
                    timeout=15,
                )
                return resp.status_code == 200
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(2)
        return False

    def getrefreshcaptcha(self):
        for attempt in range(3):
            try:
                headers = self._default_headers()
                data = {'count': 1, 'hcaptcha': 1}
                resp = self.client.post(
                    'https://store.steampowered.com/join/refreshcaptcha/',
                    timeout=15,
                    data=data,
                    headers=headers,
                )
                result = resp.json()
                self.gid = result['gid']
                self.sitekey = result['sitekey']
                return True
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(2)
        return False

    def sendmail(self, token, email):
        for attempt in range(3):
            try:
                headers = self._default_headers()
                self.creation_sessionid = str(random.getrandbits(64))
                data = {
                    'email': email,
                    'captchagid': self.gid,
                    'captcha_text': token,
                    'elang': 6,
                    'init_id': self.creation_sessionid,
                    'guest': 'false',
                }
                resp = self.client.post(
                    'https://store.steampowered.com/join/ajaxverifyemail',
                    timeout=15,
                    data=data,
                    headers=headers,
                )
                result = resp.json()
                return result.get('success') == 1, result
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(2)
        return False, {}

    def createuser(self, accountname, password, creation_sessionid, stoken=None, count=1):
        for attempt in range(3):
            try:
                headers = self._default_headers()
                data = {
                    'accountname': accountname,
                    'password': password,
                    'count': count,
                    'creation_sessionid': creation_sessionid,
                    'embedded_appid': 0,
                }
                if stoken:
                    data['stoken'] = stoken
                resp = self.client.post(
                    'https://store.steampowered.com/join/createaccount/',
                    timeout=15,
                    data=data,
                    headers=headers,
                )
                result = resp.json()
                success = (
                    result.get('bSuccess') is True
                    or result.get('success') == 1
                    or result.get('eresult') == 1
                )
                return success, result
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(2)
        return False, {}

    def verifyaccount(self, stoken, creationid):
        for attempt in range(3):
            try:
                url = (
                    f'https://store.steampowered.com/account/newaccountverification'
                    f'?stoken={stoken}&creationid={creationid}'
                )
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                              'image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
                    'sec-ch-ua': '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                }
                resp = self.client.get(url, headers=headers, timeout=15)
                return resp.status_code == 200
            except Exception:
                if attempt < 2:
                    import time
                    time.sleep(2)
        return False

    @staticmethod
    def extract_verification_link(text):
        match = VERIFICATION_LINK_PATTERN.search(text)
        if match:
            return match.group()
        return ''
