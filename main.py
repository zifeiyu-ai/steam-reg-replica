import os
import queue
import sys
import threading
import time
import webbrowser

from PySide2.QtCore import Qt, Signal, QTimer
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QTextEdit, QFileDialog, QGroupBox, QMessageBox,
)

import config_utils
from utils import parse_email_line
from rec import rec


class LogSignal(QWidget):
    log_signal = Signal(str)


class CodeSignal(QWidget):
    code_signal = Signal(str, str)


class mainui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.email_queue = queue.Queue()
        self.ip_list = []
        self.threads = []
        self.isstop = False
        self.start_time = None
        self.success_count = 0
        self.fail_count = 0
        self.log_widget = LogSignal()
        self.log_widget.log_signal.connect(self._append_log)
        self.code_widget = CodeSignal()
        self.code_widget.code_signal.connect(self._on_code_fetched)
        self.config = config_utils.load_config()
        self._init_ui()
        self._connect_init()
        self._config_init()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._run_timer)

    def _init_ui(self):
        self.setWindowTitle('Steam 注册机（复刻版）')
        self.setMinimumSize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        param_group = QGroupBox('参数设置')
        grid = QGridLayout(param_group)

        grid.addWidget(QLabel('邮箱连接方式:'), 0, 0)
        self.mail_combo = QComboBox()
        self.mail_combo.addItems(['IMAP', 'POP3', 'Graph API'])
        grid.addWidget(self.mail_combo, 0, 1)

        grid.addWidget(QLabel('IP来源:'), 0, 2)
        self.ip_combo = QComboBox()
        self.ip_combo.addItems(['IP列表文件', 'API'])
        grid.addWidget(self.ip_combo, 0, 3)

        grid.addWidget(QLabel('打码key:'), 1, 0)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText('输入打码平台 API Key')
        grid.addWidget(self.key_edit, 1, 1, 1, 3)

        grid.addWidget(QLabel('账号格式:'), 2, 0)
        self.account_fmt_edit = QLineEdit('8')
        grid.addWidget(self.account_fmt_edit, 2, 1)

        grid.addWidget(QLabel('密码格式:'), 2, 2)
        self.password_fmt_edit = QLineEdit('12')
        grid.addWidget(self.password_fmt_edit, 2, 3)

        grid.addWidget(QLabel('线程数量:'), 3, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setMinimum(1)
        self.thread_spin.setMaximum(100)
        self.thread_spin.setValue(1)
        grid.addWidget(self.thread_spin, 3, 1)

        grid.addWidget(QLabel('打码后端:'), 3, 2)
        self.captcha_combo = QComboBox()
        self.captcha_combo.addItems(['captcha-run', 'CaptchaLy', '自定义服务器'])
        grid.addWidget(self.captcha_combo, 3, 3)

        grid.addWidget(QLabel('代理区域:'), 4, 0)
        self.region_combo = QComboBox()
        self.region_combo.addItems([
            '不限', '美国(US)', '香港(HK)', '日本(JP)', '韩国(KR)',
            '新加坡(SG)', '英国(GB)', '德国(DE)', '加拿大(CA)', '澳大利亚(AU)',
        ])
        grid.addWidget(self.region_combo, 4, 1)

        grid.addWidget(QLabel('IP列表/API:'), 5, 0)
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText('导入IP列表文件或填写API地址')
        grid.addWidget(self.ip_edit, 5, 1, 1, 2)
        self.ip_btn = QPushButton('导入IP')
        grid.addWidget(self.ip_btn, 5, 3)

        layout.addWidget(param_group)

        action_group = QGroupBox('操作')
        action_layout = QHBoxLayout(action_group)

        self.mail_btn = QPushButton('导入邮箱')
        self.yxjc_btn = QPushButton('开始邮箱检测')
        self.wmemail_btn = QPushButton('微软邮箱批发(点击进入)')
        self.capreg_btn = QPushButton('打码平台注册')
        self.proxy_btn = QPushButton('推荐代理IP')
        self.start_btn = QPushButton('开始')
        self.stop_btn = QPushButton('停止')
        self.start_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        self.stop_btn.setStyleSheet('background-color: #f44336; color: white; font-weight: bold;')

        action_layout.addWidget(self.mail_btn)
        action_layout.addWidget(self.yxjc_btn)
        action_layout.addWidget(self.wmemail_btn)
        action_layout.addWidget(self.capreg_btn)
        action_layout.addWidget(self.proxy_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.stop_btn)

        layout.addWidget(action_group)

        info_group = QGroupBox('状态')
        info_layout = QHBoxLayout(info_group)
        self.email_count_label = QLabel('邮箱数量: 0')
        self.runtime_label = QLabel('运行时间: 00:00:00')
        self.success_label = QLabel('成功: 0')
        self.fail_label = QLabel('失败: 0')
        info_layout.addWidget(self.email_count_label)
        info_layout.addWidget(self.runtime_label)
        info_layout.addWidget(self.success_label)
        info_layout.addWidget(self.fail_label)
        info_layout.addStretch()
        layout.addWidget(info_group)

        code_group = QGroupBox('Steam 登录取码')
        code_layout = QVBoxLayout(code_group)

        code_layout.addWidget(QLabel('粘贴邮箱（每行一个，格式: 邮箱----密码----client_id----token）:'))
        self.mailbox_text = QTextEdit()
        self.mailbox_text.setMaximumHeight(80)
        self.mailbox_text.setPlaceholderText(
            'ffmddcoga@outlook.com----bjir7350----9e5f94bc-...----M.C505...'
        )
        code_layout.addWidget(self.mailbox_text)

        code_btn_layout = QHBoxLayout()
        self.import_mailbox_btn = QPushButton('导入邮箱')
        self.import_mailbox_btn.clicked.connect(self._import_mailbox)
        code_btn_layout.addWidget(self.import_mailbox_btn)

        self.account_combo = QComboBox()
        code_btn_layout.addWidget(self.account_combo, stretch=1)

        self.fetch_code_btn = QPushButton('拉取验证码')
        self.fetch_code_btn.clicked.connect(self._fetch_login_code)
        code_btn_layout.addWidget(self.fetch_code_btn)

        self.copy_code_btn = QPushButton('复制验证码')
        self.copy_code_btn.clicked.connect(self._copy_code)
        code_btn_layout.addWidget(self.copy_code_btn)
        code_layout.addLayout(code_btn_layout)

        code_result_layout = QHBoxLayout()
        code_result_layout.addWidget(QLabel('验证码:'))
        self.code_edit = QLineEdit()
        self.code_edit.setReadOnly(True)
        code_result_layout.addWidget(self.code_edit, stretch=1)
        self.code_status_label = QLabel('状态: 等待取码...')
        code_result_layout.addWidget(self.code_status_label)
        code_layout.addLayout(code_result_layout)

        layout.addWidget(code_group)

        log_group = QGroupBox('日志输出')
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, stretch=1)

    def _connect_init(self):
        self.mail_btn.clicked.connect(self._mail_init)
        self.ip_btn.clicked.connect(self._ip_open)
        self.yxjc_btn.clicked.connect(self._yxjc_all)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        self.wmemail_btn.clicked.connect(self._wmemail)
        self.capreg_btn.clicked.connect(self._capreg)
        self.proxy_btn.clicked.connect(self._proxy_open)

    def _config_init(self):
        maildz = int(config_utils.get(self.config, 'maildz', '0') or '0')
        self.mail_combo.setCurrentIndex(maildz)
        key = config_utils.get(self.config, 'key', '')
        self.key_edit.setText(key)
        account_fmt = config_utils.get(self.config, 'account_fmt', '8')
        self.account_fmt_edit.setText(account_fmt)
        password_fmt = config_utils.get(self.config, 'password_fmt', '12')
        self.password_fmt_edit.setText(password_fmt)
        thread_count = int(config_utils.get(self.config, 'thread_count', '1') or '1')
        self.thread_spin.setValue(thread_count)
        ip_source = int(config_utils.get(self.config, 'ip_source', '0') or '0')
        self.ip_combo.setCurrentIndex(ip_source)
        captcha_backend = config_utils.get(self.config, 'captcha_backend', '0') or '0'
        self.captcha_combo.setCurrentIndex(int(captcha_backend) if captcha_backend.isdigit() else 0)
        region = int(config_utils.get(self.config, 'region', '0') or '0')
        self.region_combo.setCurrentIndex(region)

    def _wrte_init(self):
        config_utils.set(self.config, 'maildz', self.mail_combo.currentIndex())
        config_utils.set(self.config, 'key', self.key_edit.text())
        config_utils.set(self.config, 'account_fmt', self.account_fmt_edit.text())
        config_utils.set(self.config, 'password_fmt', self.password_fmt_edit.text())
        config_utils.set(self.config, 'thread_count', self.thread_spin.value())
        config_utils.set(self.config, 'ip_source', self.ip_combo.currentIndex())
        config_utils.set(self.config, 'captcha_backend', self.captcha_combo.currentIndex())
        config_utils.set(self.config, 'region', self.region_combo.currentIndex())
        config_utils.save_config(self.config)

    def _log(self, msg):
        self.log_widget.log_signal.emit(msg)

    def _append_log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.append(f'[{timestamp}] {msg}')

    def _mail_init(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '导入邮箱', '', '文本文件 (*.txt)'
        )
        if not file_path:
            return
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                info = parse_email_line(line)
                if info:
                    self.email_queue.put(info)
                    count += 1
        self.email_count_label.setText(f'邮箱数量: {count}')
        self._log(f'邮箱导入成功 数量:{count}')

    def _ip_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '导入IP列表', '', '文本文件 (*.txt)'
        )
        if not file_path:
            return
        self.ip_list.clear()
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    self.ip_list.append(line)
        self.ip_edit.setText(file_path)
        self._log(f'IP列表导入成功 数量:{len(self.ip_list)}')

    def _mail_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '打开邮箱文件', '', '文本文件 (*.txt)'
        )
        if file_path:
            os.startfile(file_path)

    def _yxjc_all(self):
        if self.email_queue.qsize() == 0:
            QMessageBox.warning(self, '提示', '请先导入邮箱')
            return
        mail_type = self.mail_combo.currentIndex()
        total = self.email_queue.qsize()
        self._log(f'开始邮箱检测 共{total}个')
        temp_list = []
        while not self.email_queue.empty():
            temp_list.append(self.email_queue.get())
        valid = 0
        for info in temp_list:
            r = rec(info, self.config, log_callback=self._log, mail_type=mail_type)
            if r.yxjc():
                self.email_queue.put(info)
                valid += 1
            else:
                self._log(f'{info["email"]} 邮箱检测失败,不可用')
        self.email_count_label.setText(f'邮箱数量: {self.email_queue.qsize()}')
        self._log(f'邮箱检测完成 可用:{valid} 不可用:{total - valid}')

    def _start(self):
        if self.email_queue.qsize() == 0:
            QMessageBox.warning(self, '提示', '请先导入邮箱')
            return
        captcha_key = self.key_edit.text().strip() or config_utils.get(self.config, 'key', '')
        self._log(f'开始运行 邮箱数:{self.email_queue.qsize()} key:{captcha_key[:8]}... mail_type:{self.mail_combo.currentIndex()}')

        self.isstop = False
        self.success_count = 0
        self.fail_count = 0
        self.start_time = time.time()
        self._timer.start(1000)
        self._wrte_init()

        thread_count = self.thread_spin.value()
        mail_type = self.mail_combo.currentIndex()
        account_fmt = int(self.account_fmt_edit.text() or '8')
        password_fmt = int(self.password_fmt_edit.text() or '12')
        captcha_idx = self.captcha_combo.currentIndex()
        captcha_backend = ['caprun', 'captchaly', 'custom'][captcha_idx]
        ip_source = self.ip_edit.text() if not self.ip_list else None

        self._log(f'开始注册 线程数:{thread_count} 邮箱数:{self.email_queue.qsize()}')
        self.threads.clear()
        for i in range(thread_count):
            t = threading.Thread(
                target=self._run,
                args=(mail_type, captcha_key, account_fmt, password_fmt, captcha_backend, ip_source),
                daemon=True,
            )
            self.threads.append(t)
            t.start()

    def _run(self, mail_type, captcha_key, account_fmt, password_fmt, captcha_backend, ip_api):
        try:
            while not self.isstop and not self.email_queue.empty():
                try:
                    email_info = self.email_queue.get_nowait()
                except queue.Empty:
                    break
                if self.isstop:
                    break
                proxy = None
                region_idx = self.region_combo.currentIndex()
                if region_idx > 0 and self.ip_list:
                    region_codes = ['', 'US', 'HK', 'JP', 'KR', 'SG', 'GB', 'DE', 'CA', 'AU']
                    region_code = region_codes[region_idx]
                    filtered_ips = [ip for ip in self.ip_list if region_code in ip]
                    ip_pool = filtered_ips if filtered_ips else self.ip_list
                else:
                    ip_pool = self.ip_list
                if ip_pool:
                    idx = hash(email_info['email']) % len(ip_pool)
                    proxy = ip_pool[idx]
                elif ip_api:
                    try:
                        from curl_cffi import requests
                        resp = requests.get(ip_api, timeout=10)
                        proxy = resp.text.strip()
                    except Exception:
                        pass
                self._log(f'开始处理 {email_info["email"]}')
                r = rec(
                    email_info, self.config, proxy=proxy, log_callback=self._log,
                    mail_type=mail_type, captcha_key=captcha_key,
                    account_fmt=account_fmt, password_fmt=password_fmt,
                    captcha_backend=captcha_backend,
                )
                result = r.run()
                if result:
                    self.success_count += 1
                else:
                    self.fail_count += 1
                self.email_count_label.setText(f'邮箱数量: {self.email_queue.qsize()}')
                self.success_label.setText(f'成功: {self.success_count}')
                self.fail_label.setText(f'失败: {self.fail_count}')
            self._log('所有任务处理完成')
        except Exception as e:
            self._log(f'运行异常: {e}')
            import traceback
            self._log(traceback.format_exc())

    def _stop(self):
        self.isstop = True
        self._timer.stop()
        self._log('任务停止')

    def _run_timer(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.runtime_label.setText(f'运行时间: {h:02d}:{m:02d}:{s:02d}')

    def _wmemail(self):
        webbrowser.open('https://wmemail.com/')

    def _capreg(self):
        webbrowser.open('https://captcha.run/sso?inviter=09dfa9d2-bd9e-42ee-86eb-20f9d22b99c7')

    def _proxy_open(self):
        webbrowser.open('https://www.haiwaidaili.net/register?Invitation_code=112')

    def _import_mailbox(self):
        text = self.mailbox_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, '提示', '请先粘贴邮箱数据')
            return
        self.account_combo.clear()
        count = 0
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split('----')
            if len(parts) < 4:
                continue
            email_addr = parts[0].strip()
            password = parts[1].strip()
            client_id = parts[2].strip()
            refresh_token = parts[3].strip()
            if '@' not in email_addr:
                continue
            display = email_addr
            data = {
                'email': email_addr,
                'password': password,
                'client_id': client_id,
                'refresh_token': refresh_token,
            }
            self.account_combo.addItem(display, data)
            count += 1
        self.code_status_label.setText(f'状态: 已导入 {count} 个邮箱')
        self._log(f'登录取码邮箱导入成功 数量:{count}')

    def _fetch_login_code(self):
        if self.account_combo.count() == 0:
            QMessageBox.warning(self, '提示', '请先导入邮箱')
            return
        data = self.account_combo.currentData()
        if not data:
            return
        self.fetch_code_btn.setEnabled(False)
        self.code_edit.clear()
        self.code_status_label.setText('状态: 正在拉取...')
        t = threading.Thread(target=self._fetch_code_thread, args=(data,), daemon=True)
        t.start()

    def _fetch_code_thread(self, data):
        try:
            from getmail import fetch_steam_login_code
            code = fetch_steam_login_code(
                data['email'], data['refresh_token'], data.get('client_id')
            )
            if code:
                self.code_widget.code_signal.emit(code, f'状态: 验证码 {code}')
            else:
                self.code_widget.code_signal.emit('', '状态: 未找到验证码')
        except Exception as e:
            self.code_widget.code_signal.emit('', f'状态: 拉取失败: {e}')

    def _on_code_fetched(self, code, msg):
        self.code_edit.setText(code)
        self.code_status_label.setText(msg)
        self.fetch_code_btn.setEnabled(True)
        if code:
            self._log(f'登录取码成功: {code}')

    def _copy_code(self):
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, '提示', '暂无验证码')
            return
        QApplication.clipboard().setText(code)
        self.code_status_label.setText('状态: 已复制到剪贴板')

    def _llreg(self):
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output.txt')
        if os.path.exists(output_path):
            os.startfile(output_path)
        else:
            QMessageBox.information(self, '提示', '暂无注册结果')

    def closeEvent(self, event):
        self._wrte_init()
        self.isstop = True
        self._timer.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = mainui()
    window.show()
    sys.exit(app.exec_())
