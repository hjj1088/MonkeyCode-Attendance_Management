# 系统架构

## 概述

考勤管理系统是一个**前后端分离**的考勤数据处理工具。前端运行在浏览器端负责数据导入、规则计算、查询浏览；后端由 Python 导出服务 (`export_server.py`) 负责生成带样式的 XLSX 报表。系统处理企业考勤数据的完整生命周期：导入 Excel -> 规则计算 -> 查询浏览 -> 导出报表。

v2.0 进行了 macOS Big Sur 风格重设计，引入统一的 `bigsur.css` 设计系统替代 Tailwind CDN，新增侧边栏导航 (`layout.js`) 和模块兼容桥接层 (`init.js`)。

## 技术栈

| 层级 | 技术 | 版本/方式 | 用途 |
|------|------|-----------|------|
| UI 框架 | Vue.js | 3.x (本地文件) | 响应式界面，Options API 组件化开发 |
| CSS 框架 | bigsur.css | 本地文件 (472行) | macOS Big Sur + 中国风设计系统，无 CDN 依赖 |
| 图标 | Lucide SVG | 内嵌 | 侧边栏导航和登录页图标 |
| 数据存储 | Dexie.js | 4.0.8 (本地文件) | IndexedDB 封装，SQL-like 查询 |
| Excel 导入 | SheetJS (xlsx) | 0.20.3 (本地文件) | Excel 解析、单元格颜色读取 |
| Excel 导出 | Python openpyxl | 3.1.5 (pip) | XLSX 生成，支持单元格样式（字体颜色、填充色） |
| 后端服务 | Python http.server | 标准库 | HTTP API + 静态文件服务，单进程 |
| 认证 | localStorage | 浏览器原生 | 简单的用户名/密码认证 |
| 部署 | Python 单进程 / Docker | 标准库 / Dockerfile + GitHub Actions CI/CD | `export_server.py` 同时提供静态文件与 API 端点 |

前端依赖全部本地化（`shared/` 目录），无需 npm/pnpm 构建步骤，无 CDN 依赖。Python 依赖 `openpyxl` 需通过 `pip install openpyxl` 安装。

## 项目结构

```
attendanceapp/
├── index.html            # 登录页入口（宣纸白渐变 + 毛玻璃卡片）
├── login.html            # 登录页（与 index.html 内容相同）
├── attendance.html       # 考勤计算页（列表/日历双视图 + 详情弹窗 + 部门/状态/姓名筛选）
├── import.html           # 数据导入页（拖拽上传 + 自动识别类型 + 预览弹窗 + 导入日志）
├── export.html           # 导出中心（模板管理 + 平铺/日历导出 + 实时预览）
├── settings.html         # 系统设置（考勤规则 + 容错规则 + 假期管理 + 数据库重置）
├── export_server.py      # Python 导出服务（HTTP API + 静态文件，openpyxl 生成 XLSX）
├── requirements.txt      # Python 依赖声明
├── Dockerfile            # Docker 容器化部署
└── shared/               # 共享模块（全部本地文件）
    ├── bigsur.css        # Big Sur 设计系统（CSS 变量 + 组件类 + 毛玻璃效果）
    ├── layout.js         # 侧边栏导航框架（AppLayout，v2.0 新增）
    ├── init.js           # 模块兼容桥接层（AttendanceDB/AttendanceRules/AttendanceMatcher，v2.0 新增）
    ├── auth.js           # 认证模块
    ├── db.js             # 数据库模块
    ├── rules.js          # 规则引擎模块
    ├── excel.js          # Excel 处理模块（SheetJS 导入 + API 导出）
    ├── matcher.js        # 数据匹配模块
    ├── dexie.min.js      # Dexie.js 本地文件 (230KB)
    ├── vue.min.js        # Vue.js 3 本地文件 (131KB)
    └── xlsx.min.js       # SheetJS 本地文件 (882KB)
```

## 模块依赖关系

```
index.html / login.html
    +-- bigsur.css
    +-- dexie.min.js
    +-- auth.js

attendance.html
    +-- bigsur.css + dexie.min.js + vue.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> rules.js

import.html
    +-- bigsur.css + dexie.min.js + vue.min.js + xlsx.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> excel.js -> matcher.js

export.html
    +-- bigsur.css + dexie.min.js + vue.min.js + xlsx.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> excel.js

settings.html
    +-- bigsur.css + dexie.min.js + vue.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js

init.js (独立，向后兼容桥接)
    +-- db.js (DB, Store)

export_server.py (独立进程，HTTP API + 静态文件)
```

模块间调用关系：
- `auth.js` 不依赖其他模块
- `db.js` 不依赖其他模块
- `layout.js` 依赖 `auth.js`
- `excel.js` 依赖 `db.js` (导出时需要查询 DB)
- `matcher.js` 依赖 `db.js`
- `rules.js` 依赖 `db.js`
- `init.js` 依赖 `db.js`

## 数据流

```
+------------------------------------------------------------------+
|                        数据生命周期                                |
+---------+   +---------+   +----------+   +----------+   +------+
| Excel   |   | IndexedDB|   | 规则引擎  |   | 考勤结果  |   |Excel |
| 文件    |-->| 原始数据  |-->| 计算处理  |-->| 存储+查询 |-->|导出  |
| 上传    |   |          |   |          |   |          |   |      |
+---------+   +---------+   +----------+   +----------+   +------+
                  |                              |
                  v                              v
             排班表/假期                    模板编辑
             OA 申请                       预览/导出
```

详细数据流：

1. **导入阶段** (`import.html`)：
   - 用户拖拽 Excel -> `Excel.parseExcelFile()` 解析
   - `Excel.identifyFileType()` 自动识别类型
   - `Excel.parseRecords()` 标准化字段
   - 预览弹窗展示前10条数据
   - `Store.bulkPut()` 写入对应 IndexedDB 表
   - punch 类型额外调用 `Matcher.syncEmployees()` 同步员工表
   - schedule 类型按员工展开后再写入

2. **计算阶段** (`attendance.html`)：
   - 用户选择月份或自动检测有数据月份 -> `RulesEngine.calculateMonth()`
   - 按员工+日期遍历，结合排班表、假期、OA 数据
   - 计算迟到、早退、加班、旷工状态、实际工作时长
   - 容错规则豁免（迟到次数<=阈值 且 累计时长<=阈值）
   - 加班结余计算 `prevBalance + monthOvertime - 调休消耗`
   - 结果写入 `attendance_results` 表，每条含 `workHours`、`sourcePunchIds`、`sourceLeaveIds` 等来源ID

3. **导出阶段** (`export.html`)：
   - 用户编辑导出模板字段（19个可选字段，含工作时长）
   - Flat 模式：前端准备 records + template -> POST `/api/export/flat` -> Python openpyxl 生成 XLSX（含条件格式迟到/早退红色标记）
   - 月报模式：前端读取 results + schedules + holidays -> POST `/api/export/calendar` -> Python 生成日历格式 XLSX（按部门分组、上午/下午双行、直接样式+2条全局 FormulaRule 双重条件格式着色）

## 页面导航

```
index.html / login.html (登录页)
    |
    +--> attendance.html (考勤计算，登录后默认跳转)
    +--> import.html (数据导入)
    +--> export.html (导出中心)
    +--> settings.html (系统设置)
```

所有功能页通过 `Auth.requireAuth()` 守卫，未登录自动跳转回 `index.html`。侧边栏导航通过 `AppLayout.init()` 统一管理，含4个导航项和动态问候语。

## 设计系统 (bigsur.css)

v2.0 使用自定义 `shared/bigsur.css` 替代 Tailwind CDN，定义了中国风色彩 + macOS Big Sur 毛玻璃风格：

| 色彩 | CSS 变量 | 色值 | 用途 |
|------|---------|------|------|
| 宣纸白 | `--paper` | #FAF8F5 | 页面背景 |
| 墨色 | `--ink` | #2C2416 | 标题文字 |
| 朱砂红 | `--vermillion` | #C43D3D | 主色调（按钮/强调/错误） |
| 金色 | `--gold` | #C9A96E | 侧边栏图标/装饰 |
| 翠玉绿 | `--jade` | #2D7D46 | 正常状态/成功 |
| 靛蓝 | `--indigo` | #3B5998 | 请假状态/信息 |
| 檀木棕 | `--sandal` | #8B5E3C | 早退/出差状态 |

核心组件类：`.card`、`.btn-primary`（朱砂红）、`.btn-secondary`、`.badge-*`（6种状态）、`.tabs`、`.form-input`。侧边栏和登录卡片使用毛玻璃效果（`backdrop-filter: blur()`）。

## 部署方式

### Python 单进程

```bash
pip install openpyxl
PORT=8001 python3 attendanceapp/export_server.py
```

### Docker 容器

```bash
docker run -d -p 8000:8000 ghcr.io/hjj1088/monkeycode-attendance_management:latest

# 验证运行版本
curl http://localhost:8000/health
# {"status":"ok","version":"ed71a7b...","build_time":"2026-07-17T01:20:50Z",...}

# 查看访问日志（含客户端 IP）
docker logs <container_id>
```

GitHub Actions 自动构建：推送代码到 `main` 分支后自动构建镜像并发布到 GitHub Container Registry（`.github/workflows/docker-publish.yml`）。构建时注入 `GIT_SHA` 和 `BUILD_TIME` 到 `version.py`，启动横幅和 `/health` 端点可验证镜像版本。

## 9 种考勤状态

| 状态 | 含义 | 判定条件 |
|------|------|----------|
| normal | 正常出勤 | 有打卡记录且无异常（或被容错豁免） |
| rest | 休息日 | 排班表标记为休息 |
| abnormal | 迟到 | 签到时间晚于上班时间+阈值 |
| leave | 请假 | 有对应日期的 leave_records |
| travel | 出差 | 有对应日期的 travel_records |
| absent | 旷工 | 上班日无打卡无OA |
| overtime | 加班 | 休息日有打卡+加班OA |
| suspect_ot | 疑似加班 | 休息日有打卡但无加班OA |
| no_sign_in / no_sign_out | 未打卡 | 上班日只有签到无签退，或反之 |

## 数据库表 (IndexedDB)

共 13 张表，详见 [INTERFACES.md](./INTERFACES.md#数据库-schema)。

## 兼容桥接层 (init.js)

v2.0 新增 `shared/init.js` 兼容桥接层，为旧版 API 提供映射：

- `window.AttendanceDB` -> Proxy 代理 `punch_records`/`leave_records` 表（旧版名为 `punches`/`leaves`）
- `window.AttendanceRules` -> 适配旧的 `get()`/`save()` API 到新的 `settings` 表
- `window.AttendanceMatcher` -> 提供简化的规则引擎 `match()` 方法

## 与 v1.0 的主要变更

| 方面 | v1.0 (attendance/) | v2.0 (attendanceapp/) |
|------|-------|-------|
| CSS | Tailwind CDN + 内联样式 | bigsur.css 自定义设计系统 |
| 导航 | 顶部 `<a>` 链接 | 侧边栏 AppLayout + 移动端汉堡菜单 |
| 图标 | 无 | Lucide SVG 内嵌 |
| CDN 依赖 | Tailwind CSS CDN | 无（全部本地化） |
| 导出 | 浏览器端 SheetJS | Python openpyxl（带样式） |
| 设计风格 | 通用工具类 | macOS Big Sur 毛玻璃 + 中国风色彩 |
| 部署 | 纯手动启动 | 支持 Docker 容器化 + GitHub Actions CI/CD |
| 页面布局 | 单栏 `max-w-7xl` | 侧边栏 + 主内容区 `app-shell` |
| 登录页 | 顶部导航式 | 居中毛玻璃卡片 |
| 导出条件格式 | 无 | 直接单元格样式 + 全局2条 FormulaRule（日历）/按列规则（平铺）双重保障 |
| 加班追溯 | OA 加班记录无法按日期匹配 | 解析"加班起止时间"字段，startTime 正确填充 |

## 版本

当前版本：**v2.0.2**（Big Sur 重设计 + 条件格式修复 + Docker CI/CD + 日志/版本体系增强）。原始稳定版 v1.0.28 保留于 `attendance/` 目录。

业务逻辑核心（`auth.js`、`db.js`、`matcher.js`）与 v1.0 完全一致，`rules.js` 新增了调休抵扣、`missPerson` 支持、`workHours` 计算和 `sourceOvertimeIds` 字段。

---

# V3.1 架构（数据层迁移）

> 本节描述 **v3.1**（`attendance-v3/` 目录）相对 v2.0 的架构变化。V3.1 保留 v2.0 全部前端代码（HTML 页面、Vue 应用、业务逻辑、Excel 解析、规则引擎、UI 样式）不变，**仅替换数据层**：将 IndexedDB/Dexie 的 `Store` 对象替换为 HTTP REST API 调用，后端使用 Python `http.server` + SQLite 存储。

## 概述

V3.1 将 V2.0 的纯前端架构（IndexedDB 本地存储）改为**前后端分离架构**：

- **前端**：`attendance-v3/client/`，与 V2.0 逐文件对应，唯一实质变化是 `shared/db.js` → `shared/api-store.js`（Store 接口签名保持完全一致）
- **后端**：`attendance-v3/server/`，Python 标准库 `http.server` + SQLite，无第三方 Web 框架
- **数据持久化**：浏览器 IndexedDB → 后端 SQLite 文件 `server/data/attendance.db`

```
V2.0（纯前端）                    V3.1（前后端分离）
┌─────────────────┐              ┌──────────────────────┐
│ 前端页面         │              │ 前端页面              │
│ IndexedDB(Dexie)│    变为       │ api-store.js (fetch) │
│ 本地存储        │  ──────────►  │          │ REST      │
└─────────────────┘              └──────────▼───────────┘
                                            │ /api/store/*
                                            ▼
                              ┌──────────────────────┐
                              │ Python http.server   │
                              │ + SQLite (attendance.db)│
                              └──────────────────────┘
```

## 技术栈（V3.1）

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端页面 | Vue.js 3 (Options API) + bigsur.css | 与 V2.0 完全一致 |
| 前端数据层 | `api-store.js`（fetch 封装） | 替代 V2.0 的 `db.js`（Dexie） |
| 前端认证 | `auth.js`（sessionStorage + JWT） | 替代 V2.0 的 localStorage 布尔标志 |
| 后端服务 | Python `http.server`（标准库） | HTTP API + 静态文件服务，单进程 |
| 数据存储 | SQLite（`sqlite3` 标准库） | 13 张表，字段名与 V2.0 IndexedDB 完全一致（camelCase） |
| 认证 | JWT（手写 HMAC-SHA256，HS256，24h 过期） | Bearer token 鉴权 |
| Excel 导出 | Python `openpyxl` | 与 V2.0 `export_server.py` 相同的 XLSX 生成逻辑 |

## 项目结构（V3.1）

```
attendance-v3/
├── client/                     # 前端（自 V2.0 复制，仅数据层替换）
│   ├── index.html              # 登录页
│   ├── login.html              # 登录页（副本）
│   ├── attendance.html         # 考勤计算页
│   ├── import.html             # 数据导入页
│   ├── export.html             # 导出中心
│   ├── settings.html           # 系统设置页
│   └── shared/
│       ├── api-store.js        # ★ 数据访问层（替代 db.js）
│       ├── auth.js             # 认证模块（JWT 版）
│       ├── rules.js            # 规则引擎（数据调用改为 Store API）
│       ├── excel.js            # Excel 处理
│       ├── matcher.js          # 数据匹配（与 V2.0 逐字节相同）
│       ├── layout.js           # 侧边栏导航（与 V2.0 相同）
│       ├── init.js             # 兼容桥接层（改为 Store API 薄封装）
│       └── vue.min.js / xlsx.min.js / bigsur.css
├── server/                     # ★ 后端（新增）
│   ├── server.py               # HTTP 服务 + 路由 + JWT + 通用 store CRUD + 静态托管
│   ├── database.py             # SQLite 连接 + 13 表 DDL + 默认数据初始化
│   ├── middleware.py           # PyJWT 认证模块（备用，未接入 server.py）
│   ├── data/attendance.db      # SQLite 数据文件（运行时生成）
│   └── handlers/
│       ├── export.py           # ★ 导出处理器（唯一被 server.py 挂载）
│       ├── auth.py / attendance.py / rules.py / system.py / users.py / migrate.py
│                               # 第二套 handler（未接入路由，见下方说明）
└── tests/                      # 单元测试
```

## 后端路由（V3.1，server.py）

| 方法 | 路径 | 功能 | 认证 |
|------|------|------|------|
| GET | `/api/auth/login-check` | 校验 token 有效性 | 否 |
| POST | `/api/auth/login` | 登录（仅 admin，SHA256 比对）→ 返回 JWT | 否 |
| GET | `/api/store/{table}` | 获取全表（可选 `?index=&value=` 过滤） | 是 |
| GET | `/api/store/{table}/range` | 范围查询 `?index=&lower=&upper=` | 是 |
| GET | `/api/store/{table}/{key}` | 按主键查询 | 是 |
| POST | `/api/store/{table}` | 插入/更新单条（upsert） | 是 |
| POST | `/api/store/{table}/bulk` | 批量插入 | 是 |
| POST | `/api/store/reset` | 清空 13 张表并重建默认设置 | 是 |
| DELETE | `/api/store/{table}` | 清空整表 | 是 |
| DELETE | `/api/store/{table}/{key}` | 按主键删除 | 是 |
| POST | `/api/export/flat` | 平铺导出 XLSX | 是 |
| POST | `/api/export/calendar` | 日历导出 XLSX | 是 |
| OPTIONS | 任意 | CORS 预检 | 否 |

非 `/api` 路径由 `_serve_static()` 托管 `client/` 静态文件，路径穿越有防护，文件不存在时 302 跳转 `index.html`。

## 模块依赖关系（V3.1）

```
client 页面 (index/login/attendance/import/export/settings)
    +-- auth.js (JWT 登录)
    +-- layout.js (侧边栏)
    +-- api-store.js (fetch → /api/store/*)  ← 替代 db.js
    +-- rules.js / excel.js / matcher.js     ← 逻辑不变，数据访问走 api-store.js

api-store.js ── fetch ──► server.py (/api/*) ──► database.py (SQLite)
                          └──► handlers/export.py (openpyxl XLSX)
```

`server.py` 直接导入 `handlers/export.py`；其余 6 个 handler（auth/attendance/rules/system/users/migrate）与 `middleware.py` 属于**第二套未接入的代码**（V3.2 多角色系统前置），当前没有任何 URL 路由指向它们。

## 数据流（V3.1）

1. **导入阶段**：前端 `Excel.parseExcelFile()` 解析 Excel → `Store.bulkPut()` → `fetch POST /api/store/{table}/bulk` → SQLite 写入
2. **计算阶段**：前端 `RulesEngine.calculateMonth()` → 通过 `Store.getByIndex/getByRange/getAll` 拉取排班/打卡/OA 数据 → 浏览器内存计算 → `Store.clearTable + bulkPut('attendance_results')` 回写
3. **导出阶段**：前端读取 `attendance_results`/`schedules`/`holidays` → `POST /api/export/flat|calendar` → Python openpyxl 生成 XLSX → 二进制下载

## 与 v2.0 的主要变更

| 方面 | v2.0 (attendanceapp/) | v3.1 (attendance-v3/) |
|------|------|------|
| 数据存储 | IndexedDB（Dexie.js 4.0.8） | SQLite（`server/data/attendance.db`） |
| 前端数据层 | `shared/db.js`（Store 封装 Dexie） | `shared/api-store.js`（Store 封装 fetch） |
| 认证 | localStorage 布尔标志 + 前端硬编码账号 | sessionStorage JWT + 后端 `POST /api/auth/login` |
| 导出服务 | 独立进程 `export_server.py`（端口 8000，无鉴权） | 合并进 `server.py` 的 `/api/export/*`（需 Bearer token） |
| 服务端口 | 8000 | 8001 |
| 复合索引查询 | Dexie `[employeeNo+year+month]` 等原生复合键 | 单列索引 + JS 内存 `filter/find` |
| 默认配置初始化 | `db.js startDB()` 前端执行 | `database.py _init_settings()` 后端执行 |
| 物理持久化 | 浏览器本地（换浏览器丢失） | 后端文件（服务端持久化） |

**前端零改动的关键**：`api-store.js` 保持 V2.0 `Store` 对象所有方法签名（`getAll/bulkPut/clearTable/getByIndex/getByRange/getByKey/put/deleteByKey/resetAllData`）不变，业务代码仅 4 处复合索引查询改为单索引 + 内存过滤（见 `rules.js`、`attendance.html`）。

## V3.1 已知情况（如实记录）

1. **未接入的 handler**：`handlers/auth.py`、`attendance.py`、`rules.py`、`system.py`、`users.py`、`migrate.py` 及 `middleware.py` 存在但未挂载到任何路由；它们依赖的 `users` 表、`operation_logs` 表、snake_case 字段在 `database.py` 的 13 张 camelCase 表中不存在，属于另一套（V3.2 多角色系统）的未完成代码。
2. **两套认证并存**：`server.py` 手写 HMAC JWT（硬编码 secret、admin/admin123 SHA256）与 `middleware.py` 的 PyJWT 认证互不兼容，后者未使用。
3. **测试与实现脱节**：`tests/` 中部分测试引用 `database.init_tables()`、15 张表等，与当前 `init_db()`、13 张表实现不符，测试无法通过。
4. **login.html 遗留问题**：V3.1 的 `login.html` 第 74 行仍按 V2.0 同步风格调用异步 `Auth.login()`，登录不可用；实际入口是 `index.html`（已迁移为 `.then()` 风格）。

---

# V3.2 架构（多角色 + 前端重建）

> 本节描述 **v3.2** 相对 v3.1 的架构变化。V3.1 中"未接入的第二套代码"（多角色 handler 与 middleware）在 V3.2 全部挂载启用；前端从 V2.0 静态 HTML 页面重建为 **Vite + Vue 3 SPA**；数据库新增 `users`/`operation_logs` 表并升级 `attendance_results` 审核字段。

## 概述

V3.2 的目标是**多角色考勤系统**（需求阶段 R1-R9）：

- **多角色权限**：`hradmin`（人事管理员）/ `deptadmin`（部门管理员）/ `employee`（员工），前端路由守卫 + 后端接口双重鉴权
- **审核工作流**：考勤结果单向流转 `pending_review → confirmed/disputed → submitted → locked`
- **前端重建**：`client/src` 全新 Vite + Vue 3 SPA，功能复刻 V3.1（页面行为以 `v31-replica-reference.md` 为基线）
- **计算引擎前置化**：考勤计算逻辑保留在前端 `shared/rules.js`（ES Module），后端 `/api/attendance/calculate` 负责落库

```
V3.1（前后端分离 + 静态 HTML）          V3.2（多角色 + SPA）
┌──────────────────────┐              ┌────────────────────────────┐
│ client/*.html (V2.0) │              │ client/ Vite+Vue3 SPA       │
│ api-store.js         │     变为      │  src/views + src/shared     │
│   │ fetch /api/*     │  ──────────► │  router 守卫(角色)          │
└──────────┬───────────┘              └────────────┬───────────────┘
           ▼                                      │ proxy /api (8002→8001)
┌──────────────────────┐                          ▼
│ server.py 手写 JWT    │     ┌────────────────────────────┐
│ 部分 handler 未接入   │  │ middleware.py(PyJWT)统一认证 │
│                      │   │ handlers/{auth,users,system, │
└──────────────────────┘   │ rules,attendance,export,     │
                            │ migrate} 全量挂载            │
                            └────────────────────────────┘
```

## 技术栈（V3.2）

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端框架 | Vite 5 + Vue 3.5（Composition API `<script setup>`） | SPA 应用 |
| 前端路由 | vue-router 4（`beforeEach` 守卫 + role 校验） | 页面导航 |
| 前端 Excel | SheetJS（`public/lib/xlsx.min.js` 全局挂载） | 解析与导出 |
| 前端构建 | `npm run build` → `client/dist` | 生产构建 |
| 后端认证 | `middleware.py` PyJWT（HS256，24h） | 唯一认证基础（替代 V3.1 手写 HMAC） |
| 数据存储 | SQLite，15 张表（camelCase 字段） | 持久化 |
| 导出 | Python `openpyxl`（`handlers/export.py`） | XLSX 生成 |

## 项目结构（V3.2）

```
attendance-v3/
├── client/                      # 前端 SPA
│   ├── vite.config.js           # dev 8002、proxy /api→127.0.0.1:8001、allowedHosts
│   ├── index.html               # 挂载 /lib/xlsx.min.js + src/main.js
│   ├── public/lib/xlsx.min.js   # SheetJS 全局脚本
│   └── src/
│       ├── main.js / App.vue    # 入口 + 顶层布局（topbar + 侧栏 + router-view）
│       ├── router/index.js      # 路由表 + 登录/角色守卫 + 默认页
│       ├── assets/bigsur.css    # 设计系统样式（与 V3.1 相同）
│       ├── shared/              # ES Module 共享层（替代 V3.1 shared/*.js）
│       │   ├── api.js           # fetch 封装（Bearer、401 清 token 跳登录）
│       │   ├── store.js         # Store 接口 → /api/store/*
│       │   ├── auth.js / constants.js / excel.js / matcher.js
│       │   └── rules.js         # 考勤规则引擎（calculateMonth 全量迁移）
│       ├── components/          # AppSidebar / AttendanceTable / AttendanceCalendar
│       └── views/               # Login/SetupWizard/Settings/RulesSettings/
│                                #   UserManage/Import/Attendance/MyAttendance/Export
├── server/
│   ├── server.py                # 路由 + store CRUD + 静态托管（单文件/端口 8001）
│   ├── middleware.py            # PyJWT 生成/校验（generate_token/verify_token）
│   ├── database.py              # 15 表 DDL + _migrate（V3.1 库升级）+ init_system
│   └── handlers/
│       ├── auth.py              # login / change-password / 锁定逻辑
│       ├── users.py             # 用户 CRUD / 启禁用 / 重置密码
│       ├── system.py            # version/status/config/admin-password/seed/reset
│       ├── rules.py             # attendance_config / tolerance / holidays / work-schedule
│       ├── attendance.py        # import / calculate / my / all / review / dept/submit / lock
│       ├── export.py            # build_flat_report / build_calendar_report
│       └── migrate.py           # V2.0 JSON 迁移（含失败回滚）
└── tests/                       # 104 项测试（pytest + Node 驱动前端 rules）
```

## 多角色与权限模型

| 角色 | 默认页 | 数据范围 | 主要权限 |
|------|--------|----------|----------|
| `hradmin` | `/attendance` | 全部 | 用户管理、规则/系统设置、全量考勤、审核/提交/锁定、seed/reset、迁移 |
| `deptadmin` | `/attendance` | 本部门 | 查看本部门考勤、审核（确认/申诉）、提交本部门 |
| `employee` | `/my` | 本人 | 查看本人考勤（`/api/attendance/my`） |

后端鉴权辅助：`middleware._require_hradmin / _require_any_user`；员工访问 `/api/attendance/all`、`/api/users` 等返回 403。

## 审核工作流

```
pending_review ──确认──► confirmed ──部门/人事提交──► submitted ──锁定──► locked
      ▲                    │  ▲
      └────────申诉────────┘  └──────────再次确认──────────┘
```

- 状态机定义在 `handlers/attendance.py handle_attendance_review` 的 `valid_transitions`
- `submitted` / `locked` 为终态，不可再变更；锁定要求该月全部记录已 `submitted`
- 变更记录写入 `operation_logs`

## 后端路由（V3.2 全量）

| 方法 | 路径 | 功能 | 角色 |
|------|------|------|------|
| POST | `/api/auth/login` | 登录（含 5 次失败锁 30 分钟）→ JWT | 公开 |
| POST | `/api/auth/change-password` | 修改本人密码 | 登录 |
| GET | `/api/auth/login-check` | token 有效性 | 登录 |
| GET | `/api/users` / POST `/api/users` | 用户列表 / 新建 | hradmin |
| PATCH | `/api/users/{id}/status` | 启/禁用 | hradmin |
| POST | `/api/users/reset-password` | 重置密码 | hradmin |
| GET | `/api/system/version` `/status` `/config` | 系统信息 | 登录/hradmin |
| POST | `/api/system/seed-test-data` `/reset-data` | 测试数据 / 数据重置 | hradmin |
| PUT | `/api/rules/config` `/tolerance`、GET/POST/DELETE `/api/rules/holidays` | 规则配置 | hradmin |
| POST | `/api/attendance/import` | Excel 数据导入（6 类型） | 登录 |
| POST | `/api/attendance/calculate` | 存储前端计算结果 | 登录 |
| GET | `/api/attendance/my` `/all` `/summary` | 本人/全部/汇总 | 角色 |
| PATCH | `/api/attendance/{id}/review` | 审核（确认/申诉） | deptadmin/hradmin |
| PATCH | `/api/attendance/dept/submit` | 部门提交 | deptadmin/hradmin |
| PATCH | `/api/attendance/lock` | 锁定整月 | hradmin |
| POST | `/api/export/flat` `/calendar` | XLSX 导出 | 登录 |
| POST | `/api/migrate` | V2.0 JSON 迁移（失败回滚） | hradmin |
| GET/POST/DELETE | `/api/store/*` | 通用表 CRUD（含表名映射） | 登录 |

`/api/store/*` 提供 **V3.1 前端表名映射**：`punch→punch_records`、`leave→leave_records`、`overtime→overtime_records`、`travel→travel_records`、`miss_punch→miss_punch_records`、`schedule→schedules`。

## 数据流（V3.2）

1. **导入**：前端 `Excel.parseExcelFile()` 解析 → `Store` → `POST /api/attendance/import` → 后端按类型落库（punch 导入前清空整表、`_sync_employees` 建立名册、记录 `settings.last_punch_month`、schedule 需先有名册）
2. **计算**：前端 `RulesEngine.calculateMonth()`（`shared/rules.js`）拉取数据、浏览器内计算 → `POST /api/attendance/calculate`（body 含 results + carry_over）→ 后端删除该月旧结果后批量落库
3. **审核**：`PATCH /api/attendance/{id}/review`（确认/申诉）→ `dept/submit`（部门提交）→ `lock`（人事锁定）
4. **导出**：前端读 `attendance_results` → `POST /api/export/flat|calendar` → openpyxl XLSX 下载

### 考勤视图默认月份（`detectDataMonth`）

`AttendanceView.vue` 与旧版 `attendance.html` 的 `detectDataMonth()` 决定考勤计算页初始月份，优先级：

1. `settings.last_punch_month`（最新打卡导入月份，优先）
2. `raw_files` 最新 punch 文件名的 `/(\d{4})\s*年\s*(\d{1,2})\s*月/` 正则匹配（历史库回退）
3. `punch_records` 中最后一条记录月份
4. 当前月份（无任何打卡数据时）

修改月份后 `watch(currentMonth)` → `loadResults()` 重新加载（结果为空且该月有打卡时自动触发 `runCalculation`）。

## 与 v3.1 的主要变更

| 方面 | v3.1 | v3.2 |
|------|------|------|
| 前端 | V2.0 静态 HTML（`*.html` + `shared/*.js`） | Vite + Vue3 SPA（`client/src`） |
| 认证 | `server.py` 手写 HMAC JWT | `middleware.py` PyJWT 统一（`verify_token`） |
| handler | 仅 `export.py` 挂载，其余未接入 | 7 个 handler + middleware 全量挂载 |
| 角色 | 仅 admin | hradmin / deptadmin / employee |
| 审核 | 无 | pending→confirmed→submitted→locked + operation_logs |
| 数据库 | 13 张表 | +users / operation_logs；attendance_results +id/review 三字段 |
| 计算落库 | `Store.clearTable + bulkPut` | `POST /api/attendance/calculate`（删除该月旧结果） |
| 前端 dev | 后端直出静态页 | Vite dev 8002 + proxy `/api`→8001 |
| 测试 | 部分与实现脱节 | 104 项全通过（含 Node 驱动前端 rules） |

## V3.2 已知情况（如实记录）

1. **计算在前端**：考勤判定逻辑位于前端 `client/src/shared/rules.js`，后端 `/api/attendance/calculate` 仅存储。测试通过 esbuild bundle 在 Node 中驱动该逻辑。
2. **gitee 远程推送受限**：远程凭证仅 origin（GitHub）可用，gitee push 报 `Incorrect username or password`。
3. **V3.1 静态页面不再由前端入口服务**：`client/` 目录下的 V3.1 `*.html` 页面保留但已非入口；生产/预览入口为 Vite 构建产物。
