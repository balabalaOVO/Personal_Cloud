# AI 个人云盘 — 开发会话记录

> 本文档记录了项目从零到 MVP 的完整开发过程，供后续 AI 对话快速恢复上下文。

## 1. 项目快照（2026-06-22）

### 当前状态

MVP 已实现，核心功能可运行。后端 FastAPI + 前端 React，无需 Nginx 即可对外服务。

### 启动命令

```bash
cd backend && python -m uvicorn main:app --host :: --port 8000
```

### 访问地址

| 方式 | 地址 | 延迟 |
|------|------|------|
| 本地 | `http://127.0.0.1:8000` | 0 |
| **iPhone mDNS** | `http://clouddrive.local:8000` | 0，局域网直连 |
| PC 公网 IPv6 | `http://[2409:...]:8000` | 0 |
| 域名 | `http://files.balabalashowtime.icu:8000` | DNS TTL 10 分钟后生效 |
| Android | `http://<LAN_IP>:8000`（启动页显示） | 0 |

### 默认登录

用户名 `admin`，密码 `admin123`

---

## 2. 项目文件结构

```
D:\A_VSCode_Projects\AIPersonalCloudDrive\
├── AI 个人云盘项目需求文档 (PRD).md       ← 需求背景
├── AI 个人云盘技术架构文档.md              ← 技术方案
├── AI 个人云盘 MVP 文档.md                 ← MVP 范围定义
├── AI 个人云盘开发会话记录.md              ← 本文档
│
├── backend\
│   ├── .env                                ← 敏感配置（已填入 Cloudflare 凭据）
│   ├── .env.example                        ← 配置模板
│   ├── main.py                             ← FastAPI 入口（lifespan、路由、静态文件）
│   ├── config.py                           ← 全部配置项（从 .env 读取）
│   ├── requirements.txt                    ← Python 依赖
│   │
│   ├── models\
│   │   └── database.py                     ← SQLite 初始化 + 默认管理员
│   │
│   ├── routers\
│   │   ├── auth.py                         ← POST /api/auth/login, /refresh
│   │   ├── files.py                        ← 文件 CRUD + 下载 token + 上传
│   │   └── ddns.py                         ← GET /api/ddns/status
│   │
│   ├── services\
│   │   ├── auth_service.py                 ← JWT 签发/校验、bcrypt 密码、IP 限流
│   │   ├── file_service.py                 ← 文件操作 + SHA-256 + 路径防护
│   │   ├── ddns_service.py                 ← Cloudflare DDNS（IPv6 检测 + API 更新）
│   │   ├── mdns_service.py                 ← mDNS 局域网发现（zeroconf）
│   │   └── log_service.py                  ← TimedRotatingFileHandler 日志
│   │
│   └── middleware\
│       └── auth_middleware.py               ← JWT 依赖注入 + 客户端 IP
│
├── frontend\
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── dist\                                ← 生产构建（FastAPI 直接挂载）
│   └── src\
│       ├── main.tsx                         ← 入口（antd ConfigProvider + Router）
│       ├── App.tsx                          ← 路由（/login, /files）
│       ├── api\
│       │   ├── client.ts                    ← Axios 封装 + 自动 refresh token
│       │   ├── auth.ts                      ← 登录 API
│       │   └── files.ts                     ← 文件 API + 下载 token 直链
│       ├── pages\
│       │   ├── LoginPage.tsx                ← 登录页
│       │   └── FilePage.tsx                 ← 文件主页（面包屑 + 工具栏 + 表格）
│       ├── components\
│       │   ├── Navbar.tsx                   ← 顶栏（品牌 + 用户菜单）
│       │   ├── FileTable.tsx                ← 文件表格（排序/重命名/删除/下载）
│       │   └── UploadModal.tsx              ← 上传弹窗（进度/速度/SHA-256 校验）
│       ├── utils\
│       │   └── hash.ts                      ← SHA-256（Web Crypto API）
│       └── styles\
│           └── global.css
│
├── nginx\
│   └── conf\
│       └── cloud-drive.conf                 ← Nginx 配置（MVP 阶段不使用）
│
├── data\                                    ← 用户文件存储（运行时创建）
├── logs\                                    ← 应用日志（运行时创建）
├── start.bat                                ← 一键启动开发环境
└── install-service.bat                      ← NSSM Windows Service 安装
```

---

## 3. 关键技术决策

| 决策 | 原因 |
|------|------|
| 后端绑定 `::` 而非 `127.0.0.1` | 必须监听所有接口，手机热点 IPv6 流量才能到达 |
| FastAPI 直接挂载前端静态文件 | MVP 阶段去掉 Nginx 依赖，一个进程搞定 |
| 下载用 token URL 直链，不用 fetch+blob | Chrome Safe Browsing 会导致大文件下载延迟几十秒 |
| 上传 SHA-256 选文件时不计算，上传时才算 | 大文件选文件时算哈希会 OOM，UI 卡死 |
| DDNS 从腾讯云 DNSPod 改为 Cloudflare | 用户实际 DNS 服务商是 Cloudflare |
| 新增 mDNS 局域网发现 | 手机通过域名访问有 DNS 延迟，mDNS 零延迟局域网直连 |
| TTL 曾设 120 导致 Cloudflare 免费版报错 | 免费版最低 TTL 600，已修复（`.env` 中 `DDNS_TTL=600`） |

---

## 4. 已解决的 Bug

| Bug | 根因 | 修复 |
|-----|------|------|
| 公网无法访问 | `HOST=127.0.0.1` 只监听本地 | 改为 `HOST=::` |
| DDNS 不自愈 | 只检测本地 IP 变化，不验证远程记录 | 增加每 6 轮远程验证（条件 B） |
| DNS 更新失败不报错 | `update_dns_record()` 不检查 API 返回的 Error 字段 | Cloudflare 重写版已修复，检查 `cf_is_success()` |
| TTL=120 报错 | 腾讯云/Cloudflare 免费版最低 TTL 600 | 改回 600 |
| 下载延迟（Chrome 最长） | fetch().blob() 整个文件进内存 → Safe Browsing | 改为下载 token URL 直链 |
| 上传大文件失败 | 选文件时 computeSHA256 读整个文件进内存 | 移到上传时才算，>500MB 跳过前端哈希 |

---

## 5. 环境变量（backend/.env）

```ini
CLOUD_DRIVE_HOST=::
CLOUD_DRIVE_PORT=8000
CLOUD_DRIVE_JWT_SECRET=change-me-to-a-random-string-at-least-32-chars
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
DDNS_DOMAIN=files.balabalashowtime.icu
DDNS_CHECK_INTERVAL=60
DDNS_TTL=600
CLOUDFLARE_API_TOKEN=<已配置>
CLOUDFLARE_ZONE_ID=<已配置>
```

---

## 6. API 接口一览

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/refresh` | 刷新 Token |

### 文件管理（需 JWT）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files?path=/&page=1&size=50&sort=name` | 文件列表 |
| POST | `/api/files/upload` | 上传（FormData: file, path, sha256） |
| POST | `/api/files/download-token` | 获取 30s 下载 token |
| GET | `/api/files/download?path=...&token=...` | 下载（支持 token query param） |
| POST | `/api/files/mkdir` | 新建文件夹 |
| PUT | `/api/files/rename` | 重命名 |
| DELETE | `/api/files` | 删除（软删除到 .trash） |

### 状态（无需认证）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/public-status` | 公开状态（IPv6、DDNS、mDNS） |
| GET | `/api/ddns/status` | DDNS 状态（需 JWT） |

---

## 7. 下一步计划（MVP 之后）

优先级从高到低：

- [ ] 前端页面显示 LAN/mDNS 访问地址
- [ ] PWA 支持（添加到手机主屏幕）
- [ ] 目录树导航（双击进入子目录，面包屑返回）
- [ ] 文件预览（图片、PDF）
- [ ] 批量打包下载 zip
- [ ] AI 智能分类与标签
- [ ] RAG 文档对话
- [ ] 语义搜索

---

## 8. 恢复对话提示

下次 AI 对话时，可以直接说：

> "读取 AI 个人云盘开发会话记录.md，继续开发。当前要做的是：[具体任务]"

或者更简单：

> "继续开发 AI 个人云盘，先读开发会话记录了解背景，然后[具体任务]"
