import base64
import email
import html
import imaplib
import poplib
import re
import time
from email.parser import Parser
from urllib.parse import urlencode

from curl_cffi import requests

VERIFICATION_LINK_PATTERN = re.compile(
    r'https://store\.steampowered\.com/account/newaccountverification\?stoken=[a-f0-9]+&creationid=\d+'
)

GRAPH_CLIENT_ID = '9e5f417e-11ce-4f0e-8e7c-35b725498f3c'
GRAPH_TOKEN_URL = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
GRAPH_MESSAGES_URL = 'https://graph.microsoft.com/v1.0/me/messages'
GRAPH_SCOPE = 'https://graph.microsoft.com/Mail.Read'


class pyimap:
    def __init__(self, email_addr, password, use_ssl=True, imap_server=None, port=None):
        self.email_addr = email_addr
        self.password = password
        self.use_ssl = use_ssl
        self.imap_server = imap_server or self._guess_server(email_addr)
        self.port = port or (993 if use_ssl else 143)
        self.conn = None

    def _guess_server(self, email_addr):
        domain = email_addr.split('@')[-1].lower()
        if 'outlook' in domain or 'hotmail' in domain or 'live' in domain or 'msn' in domain:
            return 'outlook.office365.com'
        if 'gmail' in domain:
            return 'imap.gmail.com'
        if 'yahoo' in domain:
            return 'imap.mail.yahoo.com'
        return f'imap.{domain}'

    def login(self):
        try:
            if self.use_ssl:
                self.conn = imaplib.IMAP4_SSL(self.imap_server, self.port)
            else:
                self.conn = imaplib.IMAP4(self.imap_server, self.port)
            self.conn.login(self.email_addr, self.password)
            return True
        except Exception:
            return False

    def login_xoauth2(self, access_token):
        try:
            if self.use_ssl:
                self.conn = imaplib.IMAP4_SSL(self.imap_server, self.port)
            else:
                self.conn = imaplib.IMAP4(self.imap_server, self.port)
            auth_str = self._generate_auth_string(access_token)
            self.conn.authenticate('XOAUTH2', lambda x: auth_str)
            return True
        except Exception:
            return False

    @staticmethod
    def _generate_auth_string(access_token):
        return f'user={access_token}\x01auth=Bearer {access_token}\x01\x01'

    @staticmethod
    def get_accesstoken(email_addr, refresh_token, client_id=None):
        try:
            data = {
                'client_id': client_id or GRAPH_CLIENT_ID,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'scope': GRAPH_SCOPE,
            }
            resp = requests.post(GRAPH_TOKEN_URL, data=data, timeout=10)
            return resp.json().get('access_token')
        except Exception:
            return None

    def get_body(self, mail_data):
        msg = email.message_from_bytes(mail_data)
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get('Content-Disposition', ''))
                if 'attachment' in cdisp:
                    continue
                if ctype == 'text/plain' or ctype == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        return body

    def get_ret(self, mail_data):
        body = self.get_body(mail_data)
        return VERIFICATION_LINK_PATTERN.search(body)

    def getsteamreg(self, timeout=60):
        if not self.conn:
            if not self.login():
                return ''
        start = time.time()
        while time.time() - start < timeout:
            for folder in ['INBOX', 'Junk']:
                try:
                    self.conn.select(folder, readonly=True)
                    typ, data = self.conn.search(None, 'ALL')
                    if typ != 'OK':
                        continue
                    for num in reversed(data[0].split()):
                        typ, msg_data = self.conn.fetch(num, '(RFC822)')
                        if typ != 'OK':
                            continue
                        match = self.get_ret(msg_data[0][1])
                        if match:
                            self.close()
                            return match.group()
                except Exception:
                    continue
            time.sleep(5)
        return ''

    def test(self):
        try:
            if self.login():
                self.close()
                return True
            return False
        except Exception:
            return False

    def close(self):
        try:
            if self.conn:
                self.conn.close()
                self.conn.logout()
        except Exception:
            pass
        finally:
            self.conn = None


class pypop:
    def __init__(self, email_addr, password, use_ssl=True, pop_server=None, port=None):
        self.email_addr = email_addr
        self.password = password
        self.use_ssl = use_ssl
        self.pop_server = pop_server or self._guess_server(email_addr)
        self.port = port or (995 if use_ssl else 110)
        self.conn = None

    def _guess_server(self, email_addr):
        domain = email_addr.split('@')[-1].lower()
        if 'outlook' in domain or 'hotmail' in domain or 'live' in domain or 'msn' in domain:
            return 'outlook.office365.com'
        if 'gmail' in domain:
            return 'pop.gmail.com'
        return f'pop.{domain}'

    def login(self):
        try:
            if self.use_ssl:
                self.conn = poplib.POP3_SSL(self.pop_server, self.port)
            else:
                self.conn = poplib.POP3(self.pop_server, self.port)
            self.conn.user(self.email_addr)
            self.conn.pass_(self.password)
            return True
        except Exception:
            return False

    def get_body(self, lines):
        msg_data = b'\n'.join(lines)
        parser = Parser()
        msg = parser.parsestr(msg_data.decode('utf-8', errors='ignore'))
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get('Content-Disposition', ''))
                if 'attachment' in cdisp:
                    continue
                if ctype in ('text/plain', 'text/html'):
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        return body

    def get_ret(self, lines):
        body = self.get_body(lines)
        return VERIFICATION_LINK_PATTERN.search(body)

    def getsteamreg(self, timeout=60):
        if not self.conn:
            if not self.login():
                return ''
        start = time.time()
        while time.time() - start < timeout:
            try:
                count = len(self.conn.list()[1])
                for i in range(count, 0, -1):
                    resp = self.conn.retr(i)
                    lines = resp[1]
                    match = self.get_ret(lines)
                    if match:
                        self.close()
                        return match.group()
            except Exception:
                pass
            time.sleep(5)
        return ''

    def test(self):
        try:
            if self.login():
                self.close()
                return True
            return False
        except Exception:
            return False

    def close(self):
        try:
            if self.conn:
                self.conn.quit()
        except Exception:
            pass
        finally:
            self.conn = None


class wrgraph:
    def __init__(self, email_addr, refresh_token, client_id=None):
        self.email_addr = email_addr
        self.refresh_token = refresh_token
        self.client_id = client_id or GRAPH_CLIENT_ID
        self.access_token = None
        self.client = requests.Session()

    def get_accesstoken(self):
        for attempt in range(3):
            try:
                data = {
                    'client_id': self.client_id,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'scope': GRAPH_SCOPE,
                }
                resp = self.client.post(GRAPH_TOKEN_URL, data=data, timeout=15)
                self.access_token = resp.json().get('access_token')
                return self.access_token
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return None

    def getsteamreg(self, timeout=60):
        if not self.access_token:
            if not self.get_accesstoken():
                return ''
        start = time.time()
        while time.time() - start < timeout:
            for attempt in range(3):
                try:
                    url = (
                        f'{GRAPH_MESSAGES_URL}'
                        f'?$top=1&$orderby=receivedDateTime desc'
                    )
                    headers = {'Authorization': f'Bearer {self.access_token}'}
                    resp = self.client.get(url, headers=headers, timeout=15)
                    data = resp.json()
                    messages = data.get('value', [])
                    if messages:
                        body_content = messages[0].get('body', {}).get('content', '')
                        body_content = html.unescape(body_content)
                        match = VERIFICATION_LINK_PATTERN.search(body_content)
                        if match:
                            return match.group()
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(2)
            time.sleep(5)
        return ''

    def test(self):
        if not self.access_token:
            if not self.get_accesstoken():
                return False
        for attempt in range(3):
            try:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                resp = self.client.get(
                    f'{GRAPH_MESSAGES_URL}?$top=1',
                    headers=headers,
                    timeout=15,
                )
                return resp.status_code == 200
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return False

    def get_login_code(self):
        if not self.access_token:
            if not self.get_accesstoken():
                return ''
        for attempt in range(3):
            try:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                resp = self.client.get(
                    f'{GRAPH_MESSAGES_URL}?$top=5&$orderby=receivedDateTime desc'
                    f'&$select=subject,from,bodyPreview,body,receivedDateTime',
                    headers=headers,
                    timeout=15,
                )
                data = resp.json()
                messages = data.get('value', [])
                for msg in messages:
                    sender = msg.get('from', {}).get('emailAddress', {}).get('address', '')
                    subject = msg.get('subject', '')
                    if 'steampowered.com' not in sender.lower():
                        continue
                    subject_lower = subject.lower()
                    if not any(kw in subject_lower for kw in [
                        '新电脑', '新设备', 'new computer', 'new device', 'steam guard', '登录'
                    ]):
                        continue
                    body_content = msg.get('body', {}).get('content', '')
                    body_content = html.unescape(body_content)
                    clean_body = re.sub(r'<[^>]+>', ' ', body_content)
                    clean_body = re.sub(r'\s+', ' ', clean_body).strip()
                    match = re.search(r'请求来自\s*\S+\s*([A-Z0-9]{5})\b', clean_body)
                    if match:
                        return match.group(1)
                    match = re.search(r'\b([A-Z0-9]{5})\b', clean_body)
                    if match:
                        return match.group(1)
                return ''
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return ''


def fetch_steam_login_code(email_addr, refresh_token, client_id=None):
    graph = wrgraph(email_addr, refresh_token, client_id)
    return graph.get_login_code()
