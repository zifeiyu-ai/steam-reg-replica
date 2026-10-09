import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EMAIL_LINE = 'wbmxfinx@outlook.com----mekxm85658----9e5f94bc-e8a4-4e73-b8be-63364c29d753----M.C501_BL2.0.U.MsaArtifacts.-CmMK2!Nkz27AzxpqoYEbh0rtMf1cddUvTnLF9eOsJInr7M0E8Q4R!qkvCknfQRx9OByOlZuyKqhcrWCvO6kpAZhpoAlKbFq0MkHREFL3!UiIadgtGZU41nl9U0qisx3wWCZTJVTa7D5d6KoHBeHMeuz4sGpzBe8OMY1BGVM7GkXpBZxCAMxuL4aaG2tUPewYMEzxmP9K7ECY5nGNBlgTRW*1Q2jfxGudp2JyA33e*q!iMr*DUEy4xfZeiiZ4xeqlnLAaDMfBl2yeIS!34Md!US8zIhnTOB3BcwHa2f3t5DKKfKEeQaaCZpdvS6Atpqnk6V6i!iVOg1hxVCLdwoUBLGliRDFzaaN26SGlaEer*z4a'

CAPTCHA_KEY = 'bc8e2da9-87c1-4647-b79b-4ed646f926cc'
PROXY = None

from utils import parse_email_line
from getmail import wrgraph
from steam_api import SteamAPI
from captcha_solver import CapRunSolver, STEAM_SITEKEY
from rec import rec
import config_utils


def log(msg):
    timestamp = time.strftime('%H:%M:%S')
    print(f'[{timestamp}] {msg}')


def test_parse():
    log('=== 步骤1: 解析邮箱格式 ===')
    info = parse_email_line(EMAIL_LINE)
    if not info:
        log('  失败: 解析返回None')
        return False
    log(f'  邮箱: {info["email"]}')
    log(f'  密码: {info["password"]}')
    log(f'  client_id: {info.get("client_id", "无")}')
    log(f'  refresh_token: {info.get("refresh_token", "无")[:50]}...')
    return True


def test_graph_email():
    log('=== 步骤2: Graph API 邮箱连通性测试 ===')
    info = parse_email_line(EMAIL_LINE)
    client_id = info.get('client_id')
    refresh_token = info.get('refresh_token')
    if not refresh_token:
        log('  失败: 无refresh_token')
        return False
    conn = wrgraph(info['email'], refresh_token, client_id)
    result = conn.test()
    if result:
        log('  成功: Graph API 连通')
    else:
        log('  失败: Graph API 不通')
        try:
            token = conn.get_accesstoken()
            if not token:
                log('  原因: 无法获取access_token')
            else:
                log(f'  access_token获取成功: {token[:30]}...')
        except Exception as e:
            log(f'  异常: {e}')
    return result


def test_steam_captcha():
    log('=== 步骤3: Steam refreshcaptcha 测试 (无代理) ===')
    st = SteamAPI(proxy=None)
    result = st.getrefreshcaptcha()
    if result:
        log(f'  成功: gid={st.gid}, sitekey={st.sitekey}')
    else:
        log('  失败: 无法获取验证码挑战 (可能需要代理)')
    st.client.close()
    return result


def test_captcha_solver():
    log('=== 步骤4: 打码平台测试 (captcha-run) ===')
    solver = CapRunSolver(CAPTCHA_KEY)
    ok = solver.createtask(STEAM_SITEKEY)
    if not ok:
        log('  失败: 创建打码任务失败 (key可能已失效)')
        return False
    log(f'  任务创建成功: taskId={solver.taskid}')
    log('  等待打码结果 (最多180秒)...')
    token = solver.gettask()
    if token:
        log(f'  成功: token={token[:40]}...')
    else:
        log('  失败: 打码超时或失败')
    return bool(token)


def test_full_flow(proxy=None):
    log('=== 步骤5: 完整注册流程测试 ===')
    info = parse_email_line(EMAIL_LINE)
    config = config_utils.load_config()
    r = rec(
        info, config, proxy=proxy, log_callback=log,
        mail_type=2, captcha_key=CAPTCHA_KEY,
        account_fmt=8, password_fmt=12,
        captcha_backend='caprun',
    )
    try:
        result = r.run()
        log(f'  最终结果: {"成功" if result else "失败"}')
        return result
    except Exception as e:
        log(f'  异常: {e}')
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('  Steam 注册机复刻版 - 端到端测试')
    print('=' * 60 + '\n')

    results = {}
    results['parse'] = test_parse()
    print()
    results['graph'] = test_graph_email()
    print()
    results['steam'] = test_steam_captcha()
    print()
    results['captcha'] = test_captcha_solver()
    print()

    if all(results.values()):
        log('所有基础测试通过，开始完整流程测试...')
        print()
        results['full'] = test_full_flow(proxy=PROXY)
    else:
        log('部分基础测试未通过，跳过完整流程测试')
        log(f'  解析: {"通过" if results["parse"] else "失败"}')
        log(f'  Graph邮箱: {"通过" if results["graph"] else "失败"}')
        log(f'  Steam验证码: {"通过" if results["steam"] else "失败"}')
        log(f'  打码平台: {"通过" if results["captcha"] else "失败"}')

    print('\n' + '=' * 60)
    print('  测试汇总')
    print('=' * 60)
    for name, ok in results.items():
        print(f'  {name:20s} {"通过" if ok else "失败"}')
