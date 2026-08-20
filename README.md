# MonkeyCode 考勤管理系统

前后端分离的企业考勤数据处理工具，支持 Excel 导入、自动规则计算、查询浏览、带样式 XLSX 导出。系统历经 4 个版本演进：V1.0 → V2.0 → V3.1 → V3.2，当前最新为 **V3.2**（Vite + Vue 3 SPA，多角色 + 审核工作流）。

## 功能

- **Excel 导入**：拖拽上传打卡记录、请假/出差/加班 OA、排班表，自动识别文件类型并标准化字段
- **规则引擎**：9 种考勤状态判定（正常/迟到/早退/请假/出差/加班/疑似加班/缺勤/未打卡），支持容错豁免、加班结余计算、实际工作时长
- **考勤查询**：列表/日历双视图，部门/状态/姓名多维度筛选，详情弹窗追溯打卡与 OA 数据
- **导出中心**：平铺列表 + 日历月报两种格式，19 种可选字段模板，迟到/早退条件格式自动标红
- **系统设置**：考勤规则配置、容错规则、假期管理、数据库重置/导出
- **多角色（V3.2）**：hradmin / deptadmin / employee 三级权限，部门数据隔离
- **审核工作流（V3.2）**：pending_review → confirmed/disputed → submitted → locked 状态流转，操作审计

## 版本说明

| 版本 | 目录 | 架构 | 数据存储 | 前端 | 认证 | 端口 |
|------|------|------|----------|------|------|------|
| **V1.0** | `attendance/` | 纯前端 | IndexedDB（Dexie） | Vue 3 + Tailwind CDN | localStorage 布尔标志 | 8000 |
| **V2.0** | `attendanceapp/` | 纯前端 + Python 导出服务 | IndexedDB（Dexie） | Vue 3 + bigsur.css 设计系统 | localStorage 布尔标志 | 8000 |
| **V3.1** | `attendance-v3/` | 前后端分离（数据层迁移） | SQLite（`server/data/attendance.db`） | 沿用 V2.0 HTML 页面，数据层换 `api-store.js` | sessionStorage + JWT | 8001 |
| **V3.2** | `attendance-v3/` | 前后端分离 + 多角色 SPA | SQLite（15 张表，含 users/operation_logs） | Vite + Vue 3 SPA（`client/src`） | PyJWT（middleware） | dev 8002 → proxy 8001 |

### 各版本定位

- **V1.0**：原始稳定版（v1.0.28），保留在 `attendance/` 目录
- **V2.0**：macOS Big Sur 风格重设计（`bigsur.css` 设计系统），新增侧边栏导航、Docker 容器化 + GitHub Actions CI/CD
- **V3.1**：数据层从浏览器 IndexedDB 迁移到服务端 SQLite + REST API，解决数据持久化问题（换浏览器不丢数据），前端业务代码零改动
- **V3.2**：前端重建为 Vite + Vue 3 SPA，新增多角色权限模型与审核工作流，后端 7 个 handler 全量挂载，104 项测试全通过

## 技术栈

| 层级 | V2.0（attendanceapp/） | V3.2（attendance-v3/） |
|------|------|------|
| 前端框架 | Vue.js 3.x (Options API) + bigsur.css | Vite 5 + Vue 3.5（`<script setup>`） + vue-router 4 |
| 前端数据层 | Dexie.js（IndexedDB） | `shared/store.js` → REST API |
| 数据库 | IndexedDB（13 张表） | SQLite（15 张表，camelCase 字段） |
| Excel 导入 | SheetJS 0.20.3 | SheetJS（`public/lib/xlsx.min.js`） |
| Excel 导出 | Python openpyxl 3.1.5 | Python openpyxl（`handlers/export.py`） |
| 后端服务 | Python http.server | Python http.server + PyJWT（`middleware.py`）+ bcrypt |
| 认证 | localStorage 布尔标志 | JWT（HS256，24h），登录失败 5 次锁定 30 分钟 |
| 部署 | Docker + GitHub Actions → GHCR | Vite 构建 + server.py 静态托管 |

## 快速开始

### V3.2（当前版本）

```bash
# 后端（8001）
cd attendance-v3
pip install -r requirements.txt
python3 server/server.py

# 前端（开发模式，8002）
cd attendance-v3/client
npm install
npm run dev        # 访问 http://localhost:8002，proxy 转发 /api 到 8001
```

生产构建：

```bash
cd attendance-v3/client
npm run build      # 产物在 client/dist，由 server.py 静态托管
```

初始账号：`admin` / `admin123`（角色 hradmin，首次登录强制改密）。调用 `POST /api/system/seed-test-data` 可生成测试数据：技术部/销售部/行政部各 5 名员工 + 部门管理员（`dept_*`，角色 deptadmin），密码统一 `test123`。

### V2.0（旧版）

```bash
pip install openpyxl
python3 attendanceapp/export_server.py
```

访问 `http://localhost:8000`，使用 `admin` / `admin123` 登录。

Docker 部署：

```bash
docker run -d -p 8000:8000 ghcr.io/hjj1088/monkeycode-attendance_management:latest
```

## 项目结构

```
attendance/              # V1.0 原始稳定版（纯前端 + Dexie）
attendanceapp/           # V2.0 Big Sur 重设计（含 Dockerfile、CI）
attendance-v3/           # V3.1/V3.2 当前版本
├── client/
│   ├── index.html               # SPA 入口（挂载 xlsx + main.js）
│   ├── vite.config.js           # dev 8002、proxy /api→127.0.0.1:8001、allowedHosts
│   ├── attendance.html          # 旧版考勤计算页（保留，V3.1 兼容入口）
│   ├── import.html / export.html / settings.html / login.html
│   ├── dist/                    # Vite 生产构建产物
│   └── src/
│       ├── main.js / App.vue    # 入口 + 顶层布局
│       ├── router/index.js      # 路由表 + 登录/角色守卫
│       ├── assets/bigsur.css    # 设计系统样式
│       ├── shared/              # api.js / store.js / auth.js / rules.js / excel.js / matcher.js
│       ├── components/          # AppSidebar / AttendanceTable / AttendanceCalendar
│       └── views/               # Login / SetupWizard / Settings / RulesSettings /
│                                #   UserManage / Import / Attendance / MyAttendance / Export
├── server/
│   ├── server.py                # 路由 + store CRUD + 静态托管（端口 8001）
│   ├── middleware.py            # PyJWT 生成/校验（generate_token / verify_token）
│   ├── database.py              # 15 表 DDL + V3.1 库升级迁移 + init_system
│   ├── handlers/                # auth / users / system / rules / attendance / export / migrate
│   └── data/attendance.db       # SQLite 数据文件（运行时生成）
└── tests/                       # 104 项测试（pytest + Node 驱动前端 rules）
```

## 数据流

```
Excel 上传 -> 后端 SQLite 落库（punch 导入记录 last_punch_month）
    -> 前端规则引擎计算（浏览器内） -> POST /api/attendance/calculate 落库
    -> 审核流转（confirm -> submit -> lock） -> openpyxl XLSX 导出
```

## API（V3.2）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 登录（含 5 次失败锁 30 分钟）→ JWT |
| `/api/store/{table}` | GET/POST/PATCH/DELETE | 通用表 CRUD（含短表名映射） |
| `/api/attendance/import` | POST | Excel 数据导入（6 类型） |
| `/api/attendance/calculate` | POST | 存储前端计算结果 |
| `/api/attendance/my` `all` `summary` | GET | 本人/全部/汇总（按角色隔离） |
| `/api/attendance/{id}/review` | PATCH | 审核（确认/申诉） |
| `/api/attendance/dept/submit` `lock` | PATCH | 部门提交 / 锁定整月 |
| `/api/export/flat` `calendar` | POST | XLSX 导出 |
| `/api/users` | GET/POST/PATCH | 用户管理（hradmin） |
| `/api/system/seed-test-data` `reset-data` | POST | 测试数据 / 数据重置（hradmin） |
| `/api/rules/*` | GET/PUT | 考勤规则、容错规则、假期管理 |
| `/api/migrate` | POST | V2.0 JSON 迁移（失败回滚） |

完整接口文档见 `.monkeycode/docs/INTERFACES.md`。

## 文档

完整技术文档：`.monkeycode/docs/`

- [ARCHITECTURE.md](.monkeycode/docs/ARCHITECTURE.md) — 系统架构（含 V1.0 → V3.2 演进）
- [INTERFACES.md](.monkeycode/docs/INTERFACES.md) — 接口/数据库 Schema
- [DEVELOPER_GUIDE.md](.monkeycode/docs/DEVELOPER_GUIDE.md) — 开发者指南
- [专有概念/V3.2-多角色与审核工作流.md](.monkeycode/docs/专有概念/V3.2-多角色与审核工作流.md) — 多角色权限与审核状态机

## License

MIT
