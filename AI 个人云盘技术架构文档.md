# AI 个人云盘技术架构文档

## 1. 文档概述

- **项目名称**：AI 个人云盘 (AI Personal Cloud Drive)
- **文档类型**：技术架构设计
- **对应需求**：AI 个人云盘项目需求文档 (PRD)
- **当前阶段**：PoC 已跑通，进入正式架构设计与开发阶段

## 2. 架构总览

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────┐
│                    客户端 (浏览器)                         │
│               PC / 手机 / 平板 — Web GUI                 │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS (IPv6 公网)
┌──────────────────────▼──────────────────────────────────┐
│                Nginx 反向代理网关                          │
│    SSL 终止 (Let's Encrypt) ｜ 限流 ｜ 请求过滤 ｜ 静态缓存  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│             Backend API 服务 (FastAPI)                    │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ 文件管理  │ 用户认证  │ DDNS服务  │ AI 服务          │  │
│  │ CRUD /   │ JWT 登录 │ IPv6 检测 │ 智能分类 / RAG / │  │
│  │ 上传下载  │ 权限控制  │ DNS 更新  │ 语义搜索          │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
└──────┬────────────────┬─────────────────┬───────────────┘
       │                │                 │
┌──────▼──────┐  ┌──────▼───────┐  ┌─────▼──────────┐
│  本地文件系统 │  │    SQLite     │  │  Chroma 向量库  │
│  (磁盘存储)  │  │  (元数据/日志) │  │  (语义索引)     │
└─────────────┘  └──────────────┘  └────────────────┘
```

### 2.2 网络拓扑

```
[手机热点]                          [本地电脑]
   │                                   │
   ├─ 公网 IPv6 ◄── AAAA 记录 ──┐      │
   │                            │      │
   ├─ 端口转发 (443 → Nginx)    │      │
   │                            ▼      │
   │                      [腾讯云 DNS]  │
   │                            ▲      │
   │                      DDNS 脚本定期更新
   │                            │      │
   └────────── 数据流 ──────────┘      │
                                       │
                               [Nginx :443]
                                    │
                               [FastAPI :8000]
                                    │
                               [本地磁盘]
```

## 3. 技术选型

### 3.1 技术栈总览

| 层级 | 技术 | 版本/说明 | 选型理由 |
|------|------|-----------|----------|
| **前端** | React + TypeScript | React 18+, Vite 构建 | 需自定义 AI 交互界面，纯静态方案无法满足 RAG 对话、语义搜索等 AI 特性 |
| **UI 组件库** | Ant Design | 5.x | 成熟的中后台组件库，表格/表单/上传组件开箱即用 |
| **后端框架** | Python FastAPI | 0.100+ | 异步高性能，Python 生态天然兼容 AI/ML 库（Ollama、Chroma、transformers），且 PoC 阶段已使用 Python |
| **ASGI 服务器** | Uvicorn | 配合 FastAPI | 支持 HTTP/2、WebSocket，性能优于 Gunicorn |
| **网关** | Nginx | 1.24+ | SSL 终止、静态资源缓存、限流、反向代理，业界标准方案 |
| **数据库** | SQLite（MVP） | → PostgreSQL（扩展阶段） | MVP 阶段零部署成本；个人云盘用户量小，SQLite 完全够用 |
| **向量数据库** | Chroma | Python 原生 | 轻量级、本地运行、无需独立进程，契合个人部署场景 |
| **AI 运行时** | Ollama | Qwen-1.5B / Llama3-8B | 本地 CPU 推理、REST API 调用，社区活跃 |
| **DDNS** | Python 脚本 | 集成于 FastAPI | 调用腾讯云 DNSPod API，与后端同语言统一管理 |
| **SSL 证书** | Let's Encrypt + Certbot | 自动续签 | 免费、自动化、被广泛验证 |
| **进程守护** | NSSM (Win) / systemd (Linux) | | 满足开机自启 + 崩溃自动重启需求 |

### 3.2 不采用方案说明

| 候选方案 | 不采用原因 |
|----------|------------|
| File Browser（开源文件管理器） | 自带 Web UI 无法嵌入 RAG 对话、语义搜索等 AI 交互界面，定制成本高于自研 |
| Go / Gin 后端 | Go 生态在 AI/ML 领域薄弱，需额外维护 Python 侧 AI 服务，增加跨进程通信复杂度 |
| MySQL | 个人场景下 SQLite 性能已足够，引入独立数据库进程增加运维负担 |
| Java / Spring Boot | 启动慢、内存占用高，不适合本地轻量级部署 |

## 4. 模块设计

### 4.1 后端模块

#### 4.1.1 文件管理模块 (`file_manager`)

```
职责：文件 CRUD、上传下载、批量操作、哈希校验、目录树管理
```

- **上传流程**：前端计算文件 SHA-256 → 分片上传至 FastAPI → 后端合并后二次校验 → 写入磁盘 → 记录元数据
- **下载流程**：读取文件 → 流式返回 → 前端校验哈希
- **批量下载**：后端按选中文件列表打包为 `.zip` → 流式返回
- **异常处理**：上传中断产生 `.tmp` 文件，定时清理任务每 30 分钟扫描并移除

#### 4.1.2 认证模块 (`auth`)

```
职责：JWT 签发与校验、登录限流、Session 管理
```

- 采用 JWT（Access Token + Refresh Token）
- 登录接口添加失败次数限制（5 次/分钟/IP）
- 所有 API（除登录页静态资源）强制校验 Authorization Header
- 密码使用 bcrypt 哈希存储

#### 4.1.3 DDNS 模块 (`ddns`)

```
职责：定时检测公网 IPv6 地址 → 对比缓存 → 变化时调用 DNSPod API 更新 AAAA 记录
```

- 检测频率：每 3 分钟
- 检测方式：通过网卡获取 IPv6 地址 + 外部 API（如 `api6.ipify.org`）双重确认
- 更新目标：腾讯云 DNSPod API，更新 `files.balabalashowtime.icu` 的 AAAA 记录
- 生命周期：随 FastAPI 启动时作为后台任务 (asyncio.Task) 拉起

#### 4.1.4 日志模块 (`logger`)

```
职责：统一日志记录、按天滚动切分、自动清理
```

- 日志格式：`[时间戳] [客户端IPv6] [操作: UPLOAD/DOWNLOAD/DELETE/LOGIN] [文件路径] [状态码] [大小] [耗时ms]`
- 使用 Python `logging` + `TimedRotatingFileHandler`
- 保留策略：本地保留 30 天，超过自动删除

#### 4.1.5 AI 模块 (`ai_service`) — 高级阶段

```
职责：文件智能分类、RAG 文档对话、语义搜索
```

- **智能分类**：上传完成后触发异步任务，根据文件类型调用视觉模型（图片）或文本模型（文档），生成标签写入元数据库
- **RAG 对话**：用户选择文档 → 后端调用 Chroma 做文档切片+向量化 → 用户提问 → 检索相关片段 → Ollama 生成回答
- **语义搜索**：用户输入自然语言 → Embedding 模型向量化 → Chroma 相似度检索 → 返回匹配文件列表

### 4.2 前端模块

#### 4.2.1 路由设计

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录页 | 公网访问的唯一入口 |
| `/` | 文件管理主页 | 目录树 + 文件列表 + 工具栏 |
| `/share` | 分享管理 | 查看已创建的分享链接 |
| `/ai/chat` | AI 文档对话 | 选择文件 → 输入问题 → 获取回答 |
| `/ai/search` | AI 语义搜索 | 自然语言搜索文件 |

#### 4.2.2 组件树

```
App
├── LoginPage
├── MainLayout
│   ├── Sidebar (目录树)
│   ├── FileToolbar (新建、上传、批量操作)
│   ├── FileTable (文件列表 + 多选)
│   ├── FilePreview (图片/文档预览)
│   └── UploadProgress (上传进度浮层)
├── AIChatPage
│   ├── FileSelector (选择对话文档)
│   └── ChatPanel (对话界面)
└── AISearchPage
    ├── SearchInput
    └── SearchResultList
```

## 5. 数据设计

### 5.1 数据库表（SQLite）

**users** — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| username | TEXT UNIQUE | 用户名 |
| password_hash | TEXT | bcrypt 哈希 |
| created_at | TIMESTAMP | 创建时间 |

**file_metadata** — 文件元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| filename | TEXT | 文件名 |
| relative_path | TEXT | 相对于存储根目录的路径 |
| size | INTEGER | 文件大小 (bytes) |
| sha256 | TEXT | SHA-256 校验值 |
| mime_type | TEXT | MIME 类型 |
| is_dir | BOOLEAN | 是否目录 |
| parent_id | INTEGER FK | 父目录 ID |
| ai_tags | TEXT (JSON) | AI 自动打的标签列表 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**operation_logs** — 操作日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| client_ip | TEXT | 客户端 IPv6 |
| operation | TEXT | UPLOAD / DOWNLOAD / DELETE / LOGIN |
| file_path | TEXT | 操作文件路径 |
| status_code | INTEGER | HTTP 状态码 |
| file_size | INTEGER | 文件大小 |
| duration_ms | INTEGER | 耗时(毫秒) |
| created_at | TIMESTAMP | 日志时间 |

### 5.2 文件存储结构

```
D:\CloudDrive\              ← 云盘存储根目录
├── .meta\                  ← 元数据（SQLite 数据库文件）
├── Documents\              ← 用户创建的文件夹
├── Photos\
│   ├── 2025\
│   └── 2026\
├── Videos\
└── Others\
```

### 5.3 Chroma 向量存储（高级阶段）

- 每个文件切片生成一个向量 + 元数据（文件路径、标签）
- 存储路径：`D:\CloudDrive\.chroma\`
- Embedding 模型：使用 Ollama 运行的 `nomic-embed-text` 或 `bge-m3`

## 6. 接口设计

### 6.1 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 6.2 文件管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files` | 获取目录文件列表（支持分页） |
| GET | `/api/files/tree` | 获取完整目录树 |
| POST | `/api/files/upload` | 上传文件（支持分片） |
| GET | `/api/files/download` | 下载单个文件 |
| POST | `/api/files/download/batch` | 批量下载（返回 zip） |
| POST | `/api/files/mkdir` | 新建文件夹 |
| PUT | `/api/files/rename` | 重命名 |
| DELETE | `/api/files` | 删除文件/文件夹 |
| GET | `/api/files/preview` | 获取文件预览信息 |
| GET | `/api/files/checksum` | 获取文件 SHA-256 |

### 6.3 AI 接口（高级阶段）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/classify` | 触发文件智能分类 |
| POST | `/api/ai/chat` | RAG 文档对话（SSE 流式返回） |
| POST | `/api/ai/search` | 语义搜索文件 |
| GET | `/api/ai/tags` | 获取所有已用标签 |

### 6.4 DDNS 接口（内部 + 管理）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ddns/status` | 查看当前 IPv6 地址及最后更新状态 |
| POST | `/api/ddns/force-update` | 手动触发 DNS 更新 |

## 7. 安全设计

### 7.1 传输安全

- 全站 HTTPS，HSTS 头强制浏览器使用加密连接
- Nginx 仅监听 443 端口，80 端口不开放或仅用于 Certbot 验证
- TLS 1.2+，禁用老旧加密套件

### 7.2 认证与授权

- JWT Token 有效期：Access Token 2 小时，Refresh Token 7 天
- 登录页为唯一无需认证的页面
- 所有 `/api/` 路径强制验证 JWT

### 7.3 文件安全

- **上传白名单**：仅允许常见文档/图片/视频/压缩包格式，拒绝 `.exe` `.sh` `.bat` `.dll` `.so` 等可执行文件
- **文件大小限制**：单文件上限 10GB（Nginx `client_max_body_size` + FastAPI 双重校验）
- **文件名过滤**：过滤路径遍历字符（`../`、`..\`），防止目录穿越攻击

### 7.4 Nginx 安全配置

- 限制请求速率（`limit_req`）：登录接口 5 次/分钟
- 限制并发连接数（`limit_conn`）：单 IP 最大 20 并发
- 隐藏 Nginx 版本号（`server_tokens off`）
- 过滤常见攻击路径（SQL 注入、XSS 特征）

## 8. 部署方案

### 8.1 Windows 环境

```
C:\CloudDrive\                    ← 项目根目录
├── nginx\                        ← Nginx 目录
│   ├── conf\
│   │   └── cloud-drive.conf
│   └── logs\
├── backend\                      ← FastAPI 代码
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── frontend\                     ← React 构建产物
│   └── dist\
├── ssl\                          ← Let's Encrypt 证书
│   ├── fullchain.pem
│   └── privkey.pem
├── data\                         ← 用户文件存储
├── start.bat                     ← 启动脚本
└── install-service.bat           ← 注册 Windows Service (NSSM)
```

- **Nginx** 通过 NSSM 注册为 Windows Service，开机自启
- **FastAPI** 通过 NSSM 注册为 Windows Service，依赖 Nginx 服务
- **Certbot** 通过 Windows 任务计划程序每周执行续签

### 8.2 Linux 环境（未来可选）

```
/etc/systemd/system/
├── cloud-drive-api.service       ← FastAPI systemd 配置
└── cloud-drive-nginx.service     ← Nginx systemd 配置
```

```ini
# cloud-drive-api.service
[Unit]
Description=AI Personal Cloud Drive Backend
After=network.target

[Service]
Type=simple
User=cloud
WorkingDirectory=/opt/clouddrive
ExecStart=/opt/clouddrive/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 9. 开发路线图

### 第一阶段：MVP 基础可用（当前 → 2 周）

| 优先级 | 任务 | 产出 |
|--------|------|------|
| P0 | DDNS 自动化脚本 | IPv6 地址变化时自动更新 DNS |
| P0 | Nginx + HTTPS | 全站加密访问 |
| P1 | FastAPI 文件管理 API | 替代 uploadserver，实现上传下载 + 哈希校验 |
| P1 | JWT 认证系统 | 强密码登录保护 |
| P1 | 前端基础文件管理 | 目录浏览、上传下载、重命名删除 |
| P2 | 日志系统 | 按天滚动、标准格式 |

### 第二阶段：体验完善（2 → 4 周）

| 优先级 | 任务 | 产出 |
|--------|------|------|
| P1 | 批量操作 | 多选删除、批量下载打包 zip |
| P1 | 文件预览 | 图片、PDF、文本在线预览 |
| P1 | 分享链接 | 生成带过期时间的临时分享链接 |
| P2 | 开机自启 | Windows Service 封装 |

### 第三阶段：AI 能力（4 → 8 周）

| 优先级 | 任务 | 产出 |
|--------|------|------|
| P1 | 智能分类与标签 | 上传后自动识别并打标签 |
| P1 | 语义搜索 | 自然语言搜索文件 |
| P2 | RAG 文档对话 | 与云盘文件对话问答 |

## 10. 风险与应对

| 风险 | 等级 | 应对措施 |
|------|------|----------|
| 手机热点 IPv6 不稳定 | 高 | DDNS 检测频率 3 分钟；断网时前端显示离线提示；可考虑备用内网穿透方案（frp） |
| 公网扫描攻击 | 高 | 强制 HTTPS + JWT；Nginx 限流限并发；文件上传白名单；定期审计 Nginx access log |
| Windows 开机自启失效 | 中 | NSSM 提供崩溃自动重启；启动脚本加入心跳检测 |
| Let's Encrypt 证书续签失败 | 中 | 提前 15 天发送续签提醒；续签失败后证书仍有效 75 天，留有缓冲期 |
| 手机流量超限 | 低 | 校园卡流量充足；可选在后台添加流量统计面板 |
