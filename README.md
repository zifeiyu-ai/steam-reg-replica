# Steam 注册机

基于 Python + PySide2 的 Steam 账号自动注册工具，支持批量邮箱导入、多线程注册、Steam 登录验证码一键拉取。

## 功能特性

- **GUI 界面** — PySide2 构建，参数可视化配置，实时日志输出
- **批量注册** — 支持多线程并发，导入邮箱列表即可自动跑完整注册流程
- **邮箱协议** — 支持 Microsoft Graph API / IMAP / POP3 三种方式收取 Steam 验证邮件
- **打码集成** — 对接 captcha-run 平台，使用 curl_cffi 模拟 Chrome TLS 指纹绕过 CloudFlare
- **自动重试** — 打码失败自动重新获取验证码挑战，最多重试 5 次
- **登录取码** — 注册成功后，在 GUI 直接拉取 Steam 登录验证码，无需手动查邮箱
- **代理区域** — 支持代理 IP 区域选择（美国/香港/日本/韩国等）
- **会话关联** — 正确使用 creationid + stoken 关联验证会话，提高注册成功率

## 注册流程

```
访问 Steam /join 页面（建立 session cookie）
        ↓
获取 hCaptcha 验证码挑战（refreshcaptcha）
        ↓
调用 captcha-run 打码平台解算 hCaptcha
        ↓   ← 失败则重试（最多5次）
发送验证邮件（ajaxverifyemail）
        ↓
通过 Graph API / IMAP / POP3 收取验证邮件
        ↓
提取 stoken + creationid
        ↓
访问验证链接（newaccountverification）
        ↓
创建 Steam 账号（createaccount）
        ↓
写入 output.txt
```

## 环境要求

- Python 3.8+
- Windows 10/11

## 安装

```bash
git clone https://github.com/zifeiyu-ai/steam-reg-replica.git
cd steam-reg-replica
pip install -r requirements.txt
```

## 使用

```bash
python main.py
```

### GUI 操作步骤

1. **填写打码 key** — 在"打码key"输入框填入 captcha-run API Key
2. **选择邮箱连接方式** — Outlook 邮箱选 Graph API
3. **导入邮箱** — 点击"导入邮箱"按钮，选择 txt 文件
   - 文件格式：每行一个，`邮箱----密码----client_id----refresh_token`
4. **点击"开始"** — 自动执行注册流程，日志区实时显示进度

### Steam 登录取码

注册成功后，用注册的账号登录 Steam 时：

1. 在"Steam 登录取码"区域粘贴邮箱（同上格式）
2. 点击"导入邮箱" → 选择账号
3. 点击"拉取验证码" → 验证码自动填入
4. 点击"复制验证码" → 粘贴到 Steam 登录页

## 邮箱格式

```
邮箱地址----邮箱密码----client_id----refresh_token
```

示例：
```
example@outlook.com----password123----9e5f94bc-e8a4-4e73-b8be-63364c29d753----M.C536_SN1.0.U.MsaArtifacts...
```

- `client_id` — Microsoft 应用注册的客户端 ID
- `refresh_token` — Microsoft OAuth2 刷新令牌（用于 Graph API 获取邮件）

## 项目结构

```
steam-reg-replica/
├── main.py              # GUI 主窗口（PySide2）
├── rec.py               # 注册流程编排
├── steam_api.py         # Steam API 交互
├── getmail.py           # 邮箱收取（Graph API / IMAP / POP3）
├── captcha_solver.py    # 打码平台集成（captcha-run）
├── config_utils.py      # 配置读写（ConfigParser）
├── utils.py             # 工具函数（随机账号/密码生成、邮箱解析）
├── requirements.txt     # Python 依赖
└── .gitignore
```

## 配置说明

运行后自动生成 `config.ini`：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `key` | captcha-run API Key | 空 |
| `maildz` | 邮箱连接方式 (0=IMAP, 1=POP3, 2=Graph API) | 2 |
| `account_fmt` | 账号名长度 | 8 |
| `password_fmt` | 密码长度 | 12 |
| `thread_count` | 线程数 | 1 |
| `captcha_backend` | 打码后端 (0=captcha-run) | 0 |
| `region` | 代理区域 (0=不限) | 0 |

## 输出

注册结果写入 `output.txt`：

```
邮箱----账号名----密码----steam_refresh_token
```

## 技术要点

- **Chrome TLS 指纹模拟** — `curl_cffi` 的 `impersonate='chrome'` 绕过 CloudFlare 和 Steam 反爬
- **会话 cookie 关联** — 先 GET `/join` 页面建立 session，后续 API 请求复用同一会话
- **creationid 传递** — 验证邮件中的 `creationid` 直接作为 `createaccount` 的 `creation_sessionid`
- **Graph API scope** — 使用 `https://graph.microsoft.com/Mail.Read` 替代 `.default`

## License

MIT
