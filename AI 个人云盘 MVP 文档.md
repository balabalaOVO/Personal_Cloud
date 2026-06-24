# AI 个人云盘 MVP 文档

## 1. 文档概述

- **项目名称**：AI 个人云盘 (AI Personal Cloud Drive)
- **文档类型**：MVP（最小可行产品）定义
- **MVP 目标**：用最短时间交付一套可在公网安全访问、具备核心文件管理能力的私有云盘，替换当前简陋的 `python -m uploadserver` 方案
- **MVP 周期**：约 2 周
- **不包含**：AI 智能分类、RAG 对话、语义搜索等高级特性（留待后续迭代）

## 2. MVP 范围定义

### 2.1 一句话描述

> 通过手机热点 IPv6 + 域名 + HTTPS，在任何地方用浏览器安全地上传和下载本地电脑上的文件。

### 2.2 核心用户故事

| 编号 | 用户故事 | 验收条件 |
|------|----------|----------|
| US-01 | 作为用户，我可以通过域名在任何外网设备上打开云盘网页 | 手机/平板/PC 通过 `https://files.balabalashowtime.icu` 可访问云盘 |
| US-02 | 作为用户，我无需手动更新 DNS，IP 变化后域名自动生效 | 手机热点重连后，3 分钟内域名自动指向新 IPv6 |
| US-03 | 作为用户，我可以通过网页直接上传和下载文件 | 点击上传按钮选择文件上传；点击文件名触发下载 |
| US-04 | 作为用户，我可以确认上传的文件没有损坏 | 上传完成后前端展示 SHA-256 校验结果 |
| US-05 | 作为用户，我需要登录才能使用云盘，防止陌生访问 | 未登录状态下无法访问任何文件接口 |
| US-06 | 作为用户，电脑开机后服务自动运行，无需手动敲命令 | 重启电脑后，云盘服务自动拉起 |

### 2.3 MVP 范围边界

| 包含（In Scope） | 不包含（Out of Scope） |
|---|---|
| DDNS 自动更新 IPv6 | AI 智能分类与标签 |
| HTTPS 全站加密 | RAG 文档对话 |
| 文件上传 / 下载 / 删除 / 重命名 | 语义搜索 |
| 新建文件夹 | 批量打包下载 zip |
| 前端 SHA-256 哈希校验 | 文件移动 / 剪切 |
| JWT 强密码登录 | 文件分享链接 |
| 操作日志记录 | 文件预览（图片/PDF） |
| Windows 开机自启 | 目录树双击导航 |
| 上传文件类型白名单 | 多语言 / 暗黑模式 |

## 3. MVP 功能清单

### 3.1 DDNS 动态域名解析

- **功能说明**：定时检测本地网卡公网 IPv6 地址，变化时自动更新腾讯云 DNSPod AAAA 记录
- **实现要点**：
  - 每 3 分钟检测一次
  - 同时通过本地网卡和外部 API（`https://api6.ipify.org`）获取 IPv6，交叉验证
  - 调用腾讯云 DNSPod API (`RecordModify`) 更新记录
  - 作为 FastAPI 后台任务 (asyncio.Task) 随服务启动
- **验收标准**：
  - [x] 热点断开重连导致 IPv6 变化后，3 分钟内 `nslookup files.balabalashowtime.icu` 返回新地址
  - [x] 提供 `/api/ddns/status` 查看当前 IPv6 及最后更新时间

### 3.2 HTTPS 安全传输

- **功能说明**：通过 Nginx + Let's Encrypt 证书实现全站 HTTPS
- **实现要点**：
  - Nginx 监听 443 端口，配置 SSL 证书
  - HTTP (80) 仅用于 Certbot 域名验证，验证完成后关闭或强制跳转
  - 反向代理 `/api/` 请求到本地 FastAPI (127.0.0.1:8000)
  - 反向代理 `/` 到前端静态文件
- **验收标准**：
  - [x] 浏览器访问显示绿色锁图标，证书有效
  - [x] HTTP 请求自动跳转 HTTPS
  - [x] SSL Labs 评分 ≥ A

### 3.3 用户认证系统

- **功能说明**：基于 JWT 的登录认证，所有 API 请求强制校验 Token
- **实现要点**：
  - 登录接口 `POST /api/auth/login`，返回 Access Token + Refresh Token
  - Access Token 有效期 2 小时，Refresh Token 有效期 7 天
  - 密码 bcrypt 哈希存储
  - 登录失败 5 次 / 分钟 / IP 后临时拒绝
  - 前端登录页为全站唯一免认证页面
- **验收标准**：
  - [x] 未登录访问任意 `/api/` 接口返回 401
  - [x] 正确用户名密码登录成功，跳转文件主页
  - [x] 错误密码登录 5 次后提示"操作过于频繁"
  - [x] Token 过期后自动跳转登录页

### 3.4 文件管理核心

- **功能说明**：提供文件列表、上传、下载、删除、重命名、新建文件夹等基础操作
- **实现要点**：
  - 文件列表 API 支持分页，返回文件名、大小、修改时间、类型
  - 上传时前端计算 SHA-256 → 分片上传 → 后端合并后二次校验 → 返回校验结果
  - 下载时流式返回文件内容
  - 删除为软删除（先移入回收站目录），前端提示确认
  - 新建文件夹、重命名操作写入日志
- **验收标准**：
  - [x] 主页展示文件列表（文件名、大小、修改时间）
  - [x] 上传文件后，前端展示前后 SHA-256 一致
  - [x] 上传中断产生的 `.tmp` 文件 30 分钟内被自动清理
  - [x] 点击文件名触发下载
  - [x] 删除操作弹出二次确认弹窗
  - [x] 禁止上传 `.exe` `.sh` `.bat` `.dll` 等可执行文件类型

### 3.5 前端 Web GUI

- **功能说明**：提供基本的文件管理网页界面
- **页面清单**：
  - **登录页**：居中卡片式登录表单，项目名称 + Logo
  - **文件主页**：顶部工具栏（上传按钮、新建文件夹按钮） + 文件列表表格 + 分页
- **交互要点**：
  - 上传进度条（百分比 + 速度）
  - 文件列表支持按名称、大小、时间排序
  - 重命名：行内编辑，回车确认
  - 删除：弹窗二次确认
  - 移动端自适应布局（表格转为卡片列表）
- **验收标准**：
  - [x] 登录页表单美观可用
  - [x] 文件列表正确展示
  - [x] 上传进度条实时更新
  - [x] 手机竖屏访问布局正常

### 3.6 日志系统

- **功能说明**：记录所有文件操作，按天滚动，保留 30 天
- **日志格式**：
  ```
  [2026-06-17 14:32:05] [240e:xxx:xxx:xxx] [UPLOAD] [/Documents/report.pdf] [200] [2.3MB] [4521ms]
  ```
- **实现要点**：
  - Python `logging` + `TimedRotatingFileHandler`，每天 00:00 切分
  - 记录字段：时间戳、客户端 IPv6、操作类型、文件路径、状态码、文件大小、耗时
  - 超过 30 天的日志文件自动删除
- **验收标准**：
  - [x] 上传/下载/删除操作均产生日志记录
  - [x] 日志文件按天命名（如 `cloud-drive-2026-06-17.log`）
  - [x] 31 天前的日志文件被自动清理

### 3.7 服务自启动

- **功能说明**：电脑开机后自动拉起 Nginx + FastAPI，无需手动操作
- **Windows 实现**：
  - Nginx：使用 NSSM 注册为 Windows Service
  - FastAPI：使用 NSSM 注册为 Windows Service，设置依赖 Nginx 服务
  - Certbot 续签：Windows 任务计划程序，每周执行一次
- **验收标准**：
  - [x] 重启电脑后，浏览器访问云盘正常
  - [x] 服务崩溃后自动重启（NSSM 配置 `AppExit` 为 Restart）

## 4. MVP 接口清单

### 4.1 认证

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| POST | `/api/auth/login` | `{username, password}` | `{access_token, refresh_token}` | 登录 |
| POST | `/api/auth/refresh` | `{refresh_token}` | `{access_token}` | 刷新 Token |

### 4.2 文件管理

| 方法 | 路径 | 参数 | 响应 | 说明 |
|------|------|------|------|------|
| GET | `/api/files` | `?path=/&page=1&size=50&sort=name` | `{items[], total}` | 文件列表 |
| POST | `/api/files/upload` | FormData (file, path, sha256) | `{filename, sha256_match}` | 上传 |
| GET | `/api/files/download` | `?path=/xxx.pdf` | 文件流 | 下载 |
| POST | `/api/files/mkdir` | `{path, name}` | `{success}` | 新建文件夹 |
| PUT | `/api/files/rename` | `{path, new_name}` | `{success}` | 重命名 |
| DELETE | `/api/files` | `{path}` | `{success}` | 删除 |

### 4.3 DDNS 状态

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| GET | `/api/ddns/status` | `{ipv6, last_update, last_check}` | 查看 DDNS 状态 |

## 5. 数据库设计

MVP 阶段使用 SQLite，单文件存储于 `data/clouddrive.db`。

### 5.1 表结构

```sql
-- 用户表 (MVP 仅单用户，但预留扩展)
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作日志表
CREATE TABLE operation_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ip   TEXT,
    operation   TEXT NOT NULL,          -- UPLOAD / DOWNLOAD / DELETE / RENAME / MKDIR / LOGIN
    file_path   TEXT,
    status_code INTEGER,
    file_size   INTEGER,
    duration_ms INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. 目录结构

```
D:\CloudDrive\                          ← 项目根目录
├── nginx\
│   ├── conf\
│   │   └── cloud-drive.conf            ← Nginx 配置（SSL + 反代）
│   ├── html\                           ← 前端静态文件
│   └── logs\                           ← Nginx 日志
├── backend\
│   ├── main.py                         ← FastAPI 入口
│   ├── config.py                       ← 配置文件
│   ├── requirements.txt
│   ├── routers\
│   │   ├── auth.py                     ← 认证路由
│   │   ├── files.py                    ← 文件管理路由
│   │   └── ddns.py                     ← DDNS 状态路由
│   ├── services\
│   │   ├── auth_service.py             ← 认证逻辑
│   │   ├── file_service.py             ← 文件操作逻辑
│   │   ├── ddns_service.py             ← DDNS 核心逻辑
│   │   └── log_service.py              ← 日志服务
│   └── models\
│       └── database.py                 ← 数据库初始化 + ORM
├── frontend\                           ← React 源码
│   ├── src\
│   │   ├── pages\
│   │   │   ├── LoginPage.tsx
│   │   │   └── FilePage.tsx
│   │   ├── components\
│   │   │   ├── FileTable.tsx
│   │   │   ├── UploadModal.tsx
│   │   │   └── Navbar.tsx
│   │   ├── api\                        ← API 请求封装
│   │   ├── utils\                      ← SHA-256 计算等工具
│   │   └── App.tsx
│   └── package.json
├── ssl\                                ← Let's Encrypt 证书
├── data\                               ← 用户文件存储（云盘实际内容）
├── logs\                               ← 应用日志
├── install-service.bat                 ← 安装 Windows Service
└── start.bat                           ← 开发环境启动脚本
```

## 7. 开发任务拆解

### 第 1 天：基础设施搭建

| 任务 | 预估工时 | 产出 |
|------|----------|------|
| 初始化 React + Vite 项目骨架 | 2h | 项目跑通，路由框架就绪 |
| 初始化 FastAPI 项目骨架 | 2h | `main.py` + 配置加载 + Uvicorn 启动 |
| Nginx 安装 + 基础配置 | 1h | HTTP 反代跑通 |
| SQLite 数据库初始化 | 1h | users 表 + operation_logs 表创建 |

### 第 2-3 天：DDNS + HTTPS

| 任务 | 预估工时 | 产出 |
|------|----------|------|
| DDNS 服务开发（IPv6 检测 + DNSPod API） | 3h | 自动更新 AAAA 记录 |
| Let's Encrypt 证书申请 + Nginx SSL 配置 | 2h | HTTPS 全站可用 |
| Certbot 自动续签脚本 | 1h | 每周自动检查续签 |

### 第 4-5 天：认证 + 文件 API

| 任务 | 预估工时 | 产出 |
|------|----------|------|
| 用户注册/登录 API + JWT 中间件 | 3h | Token 签发与校验 |
| 文件列表 + 上传 + 下载 API | 4h | 核心文件操作 |
| 哈希校验逻辑（前后端） | 2h | SHA-256 比对 |
| 删除 + 重命名 + 新建文件夹 API | 2h | 完整 CRUD |

### 第 6 天：前端开发

| 任务 | 预估工时 | 产出 |
|------|----------|------|
| 登录页 UI | 2h | 登录表单 + Token 存储 |
| 文件主页 UI（表格 + 工具栏） | 3h | 文件列表展示 |
| 上传进度组件 + 调通 API | 2h | 完整上传流程 |
| 下载 + 删除 + 重命名交互 | 2h | 完整前端操作 |

### 第 7 天：日志 + 自启 + 联调

| 任务 | 预估工时 | 产出 |
|------|----------|------|
| 日志模块开发 | 1h | TimedRotatingFileHandler |
| NSSM 服务注册 + 启动脚本 | 2h | 开机自启 |
| 全流程联调 + 边界测试 | 3h | 功能正常 |
| 文档更新 + 部署记录 | 1h | 可复现的部署步骤 |

## 8. MVP 验收检查清单

### 功能验收

- [ ] 通过 `https://files.balabalashowtime.icu` 在外网设备（手机 4G/5G）可正常访问
- [ ] 登录页输入正确用户名密码后成功进入文件主页
- [ ] 上传一个 100MB 文件，下载后文件 SHA-256 与原文件一致
- [ ] 上传被拒绝的文件类型（如 `.exe`），前端收到错误提示
- [ ] 新建文件夹 → 进入文件夹 → 上传文件 → 重命名 → 删除，全流程无报错
- [ ] 文件上传到一半取消，30 分钟内 `.tmp` 文件被清理
- [ ] DDNS：手机热点断开重连后，3 分钟内域名解析到新 IPv6
- [ ] 浏览器地址栏显示 HTTPS 锁图标
- [ ] 未登录直接访问 `/api/files` 返回 401
- [ ] 重启电脑后，3 分钟内云盘可正常访问

### 安全验收

- [ ] SSL Labs 检测评分 ≥ A
- [ ] 登录接口连续 5 次错误密码后被限流
- [ ] 尝试上传 `.sh` 文件被拒绝
- [ ] API 日志中不含密码明文

### 性能验收

- [ ] 文件列表 1000 个文件加载时间 < 1 秒
- [ ] 上传带宽可跑满手机热点上行速率
- [ ] 单文件 2GB 上传不中断（断点续传暂不要求的底线测试）

## 9. MVP 不做的事（防范围蔓延）

以下功能明确排除在 MVP 之外，避免开发周期失控：

- ❌ AI 智能分类、RAG 对话、语义搜索
- ❌ 批量打包下载 zip
- ❌ 文件分享链接（带过期时间）
- ❌ 文件移动 / 剪切到其他目录
- ❌ 图片 / PDF 在线预览
- ❌ 多用户管理
- ❌ 断点续传
- ❌ 暗黑模式
- ❌ 国际化 / 多语言
- ❌ Docker 部署
- ❌ 流量统计面板
- ❌ 手机 App（PWA 可在后续迭代中快速加上）
