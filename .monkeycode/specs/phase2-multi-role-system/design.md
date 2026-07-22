# Phase 2 技术设计文档 -- 多角色考勤管理系统 V3.0

- 项目目录: `attendance-v3/`
- 版本: v3.0.0
- 日期: 2026-07-17
- 状态: 草稿

---

## 1. 架构概览

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Browser (Vue 3 SPA)                          │
│  Vue Router ─┬─ LoginView                                            │
│              ├─ MyAttendanceView   (employee / all)                  │
│              ├─ DeptAttendanceView (deptadmin)                       │
│              ├─ AllAttendanceView  (hradmin)                         │
│              ├─ ImportView         (hradmin)                         │
│              ├─ ExportView         (hradmin)                         │
│              ├─ SettingsView       (hradmin)                         │
│              └─ UserManageView     (hradmin)                         │
├──────────────────────────────────────────────────────────────────────┤
│  Vite Dev Proxy  /api → http://127.0.0.1:8001                        │
├──────────────────────────────────────────────────────────────────────┤
│                    Python Backend (8001)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐         │
│  │  middleware  │  │  handlers   │  │  database.py          │         │
│  │  JWT verify  │──│  auth.py    │──│  SQLite (CRUD)        │         │
│  │  CORS        │  │  users.py   │  │  init_tables()        │         │
│  │  Logging     │  │  attendance │  └──────────┬───────────┘         │
│  └─────────────┘  │  export.py  │             │                     │
│                    └─────────────┘   ┌────────┴───────────┐         │
│                                      │  data/attendance.db │         │
│                                      └────────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘
```

前后端分离架构：
- 前端 Vite + Vue 3 SPA，端口 5173（开发）/ 打包为静态资源
- 后端 Python http.server 模块化拆分，端口 8001
- 开发时 Vite proxy 转发 `/api` 到后端；生产时后端提供静态文件 + API
- 数据持久化到 SQLite（`data/attendance.db`）

---

## 2. 后端设计

### 2.1 目录结构

```
attendance-v3/
├── server/
│   ├── server.py          # 主入口，路由分发
│   ├── database.py        # SQLite 连接、建表、CRUD
│   ├── middleware.py      # JWT 校验装饰器、CORS 头
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── auth.py        # 登录/登出/改密
│   │   ├── users.py       # 用户 CRUD
│   │   ├── attendance.py  # 考勤数据 CRUD + 工作流
│   │   └── export.py      # XLSX 导出 (复用 v2.0 openpyxl 逻辑)
│   └── data/
│       └── .gitkeep
├── requirements.txt
└── Dockerfile
```

### 2.2 database.py -- SQLite 管理

```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'attendance.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_tables():
    """启动时执行，CREATE TABLE IF NOT EXISTS"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (...);
        CREATE TABLE IF NOT EXISTS punch_records (...);
        -- ... 其余12张表
        CREATE TABLE IF NOT EXISTS operation_logs (...);
    """)
    conn.commit()
    conn.close()
```

#### 数据库表

| 表名 | 关键字段 | 说明 |
|------|---------|------|
| `users` | id, username(unique), password_hash, name, department, role, enabled, locked_until, created_at | 用户账号 |
| `punch_records` | id, employee_no, name, department, date, period, sign_in, sign_out, late_minutes, early_minutes, absent, overtime_hours, schedule_start, schedule_end, raw_file_id, created_at | 打卡记录 |
| `leave_records` | id, applicant, department, leave_type, start_date, end_date, leave_days, leave_hours, reason, raw_file_id | 请假 |
| `overtime_records` | id, applicant, department, start_time, end_time, overtime_hours, content, raw_file_id | 加班 |
| `travel_records` | id, applicant, department, start_date, end_date, destination, reason, raw_file_id | 出差 |
| `miss_punch_records` | id, applicant, department, miss_date, miss_person, miss_time, card_time, reason, raw_file_id | 漏打卡 |
| `schedules` | id, employee_no, name, department, year, month, work_days(json), raw_file_id | 排班 |
| `attendance_results` | id, employee_no, name, department, date, month, status, sign_in, sign_out, late_minutes, early_minutes, overtime_hours, work_hours, leave_type, absent, review_status, reviewed_by, reviewed_at, source_punch_ids(json), source_leave_ids(json), source_travel_ids(json), source_miss_ids(json), source_overtime_ids(json) | 考勤结果 |
| `carry_over` | id, employee_no, name, month, overtime_balance | 结余 |
| `holidays` | id, date, name, is_workday, is_holiday | 假期 |
| `settings` | key, value(json) | 系统配置 |
| `export_templates` | id, name, is_default, fields(json) | 导出模板 |
| `employees` | id, employee_no(unique), name, department | 员工名册 |
| `raw_files` | id, file_name, file_type, import_time | 导入历史 |
| `operation_logs` | id, operator, action, target, detail(json), created_at | 操作日志 |

#### review_status 状态流转

```
pending_review ──→ confirmed ──→ submitted ──→ locked
      │                  │
      └── disputed ──────┘  (员工申诉后由管理员重新确认)
```

### 2.3 middleware.py -- JWT + CORS

```python
import jwt
import os
from functools import wraps

SECRET_KEY = os.environ.get('JWT_SECRET', 'attendance-v3-default-key')

def generate_token(user_id, username, role, department):
    payload = {
        'uid': user_id,
        'username': username,
        'role': role,       # 'employee' | 'deptadmin' | 'hradmin'
        'department': department,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

def require_role(*roles):
    """装饰器：校验 token 和角色"""
    ...
```

### 2.4 handlers/auth.py -- API 端点

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/login` | 登录，返回 token | 无 |
| POST | `/api/auth/change-password` | 修改密码 | Bearer |

**POST /api/auth/login**
```json
// Request
{ "username": "zhangsan", "password": "123456" }
// Response OK
{ "code": 0, "data": { "token": "eyJ...", "user": { "id": 1, "name": "张三", "role": "employee", "department": "研发部" } } }
// Response Error
{ "code": 1, "message": "账号或密码错误" }
```

### 2.5 handlers/users.py -- API 端点

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/users` | 用户列表 | hradmin |
| POST | `/api/users` | 创建用户 | hradmin |
| PUT | `/api/users/<id>` | 编辑用户 | hradmin |
| PATCH | `/api/users/<id>/status` | 启用/禁用 | hradmin |

### 2.6 handlers/attendance.py -- API 端点

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/attendance/my` | 本人当月考勤 | 需登录 |
| GET | `/api/attendance/dept` | 本部门考勤 | deptadmin+ |
| GET | `/api/attendance/all` | 全公司考勤 | hradmin |
| POST | `/api/attendance/calculate` | 触发计算 | hradmin |
| PATCH | `/api/attendance/<id>/review` | 确认/标记争议 | deptadmin+ |
| PATCH | `/api/attendance/dept/submit` | 提交部门汇总 | deptadmin |
| PATCH | `/api/attendance/lock` | 锁定期末月 | hradmin |
| GET | `/api/attendance/summary` | 汇总面板 | hradmin |

### 2.7 handlers/export.py -- 复用 v2.0 导出逻辑

从 `attendanceapp/export_server.py` 迁移 `build_calendar_report()` 和 `build_flat_report()` 函数，保持完全一致的行为。

### 2.8 server.py -- 主入口

```python
def __init__(self):
    init_tables()          # 建表
    ensure_admin_user()    # 确保 admin 账号存在

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route('/health', health_handler)
        route('/api/users', users_handler.list)
        route('/api/attendance/my', attendance_handler.my)
        ...

    def do_POST(self):
        route('/api/auth/login', auth_handler.login)
        route('/api/users', users_handler.create)
        route('/api/attendance/calculate', attendance_handler.calculate)
        route('/api/export/flat', export_handler.flat)
        route('/api/export/calendar', export_handler.calendar)
        ...
```

统一响应辅助方法：
```python
def _send_json(self, code, data=None, message=None):
    body = {'code': code}
    if data is not None: body['data'] = data
    if message is not None: body['message'] = message
    self.send_response(200 if code == 0 else 400)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.end_headers()
    self.wfile.write(json.dumps(body, ensure_ascii=False).encode())
```

---

## 3. 前端设计

### 3.1 目录结构

```
attendance-v3/client/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.js              # createApp + use(router) + mount
│   ├── App.vue              # 根组件 (router-view + 侧边栏布局)
│   ├── router/
│   │   └── index.js         # Vue Router 路由 + beforeEach 守卫
│   ├── views/
│   │   ├── LoginView.vue
│   │   ├── MyAttendanceView.vue      # 员工：个人考勤
│   │   ├── DeptAttendanceView.vue    # 考勤管理员：部门考勤
│   │   ├── AllAttendanceView.vue     # 人事：全公司考勤 + 汇总面板
│   │   ├── ImportView.vue            # 数据导入
│   │   ├── ExportView.vue            # 导出中心
│   │   ├── SettingsView.vue          # 系统设置
│   │   └── UserManageView.vue        # 用户管理
│   ├── components/
│   │   ├── AppSidebar.vue            # 侧边栏导航
│   │   ├── AttendanceTable.vue       # 考勤列表复用组件
│   │   ├── AttendanceCalendar.vue    # 日历视图复用组件
│   │   └── ReviewPanel.vue           # 确认/申诉面板
│   ├── shared/
│   │   ├── api.js                    # axios/fetch 封装 + token 拦截
│   │   ├── rules.js                  # 考勤规则引擎 (从 v2.0 迁移)
│   │   ├── excel.js                  # Excel 解析 (SheetJS，从 v2.0 迁移)
│   │   └── matcher.js                # 数据匹配 (从 v2.0 迁移)
│   └── assets/
│       └── bigsur.css                # Big Sur 设计系统 (从 v2.0 复制)
```

### 3.2 Vue Router 路由表

```js
const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/my', component: MyAttendanceView, meta: { roles: ['employee', 'deptadmin', 'hradmin'] } },
  { path: '/dept', component: DeptAttendanceView, meta: { roles: ['deptadmin', 'hradmin'] } },
  { path: '/all', component: AllAttendanceView, meta: { roles: ['hradmin'] } },
  { path: '/import', component: ImportView, meta: { roles: ['hradmin'] } },
  { path: '/export', component: ExportView, meta: { roles: ['hradmin'] } },
  { path: '/settings', component: SettingsView, meta: { roles: ['hradmin'] } },
  { path: '/users', component: UserManageView, meta: { roles: ['hradmin'] } },
];
```

**beforeEach 守卫**:
1. 无 token → 跳转 `/login`（除 `/login` 外）
2. 有 token → 解码获取 role
3. role 不在 `route.meta.roles` → 重定向到角色默认页面

### 3.3 App.vue 布局

```
┌─────────────────────────────────────────────────────────────┐
│ AppSidebar                                    [user name]   │
│  (根据角色动态渲染菜单项)                                    │
├─────────────────────────────────────────────────────────────┤
│ <router-view />                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 api.js -- HTTP 封装

```js
const API_BASE = '/api';

async function request(path, options = {}) {
    const token = sessionStorage.getItem('token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
    };
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
        sessionStorage.removeItem('token');
        router.push('/login');
        throw new Error('Unauthorized');
    }
    const body = await res.json();
    if (body.code !== 0) throw new Error(body.message);
    return body.data;
}

export const api = {
    login: (u, p) => request('/auth/login', { method: 'POST', body: JSON.stringify({ username: u, password: p }) }),
    getMyAttendance: (month) => request(`/attendance/my?month=${month}`),
    // ...
};
```

### 3.5 侧边栏角色菜单

| 角色 | 菜单项 |
|------|--------|
| employee | 我的考勤 |
| deptadmin | 我的考勤、部门考勤 |
| hradmin | 我的考勤、部门考勤、全公司考勤、数据导入、导出中心、系统设置、用户管理 |

---

## 4. 数据迁移方案

提供 `migrate.py` 脚本：

```
浏览器端
  ↓ 手动执行: 打开迁移页面 → 导出 IndexedDB 全量 JSON → 下载
服务端
  ↓ POST /api/migrate { tables: { punch_records: [...], leave_records: [...], ... } }
  ↓ 逐表写入 SQLite
  ↓ 返回迁移报告 { imported_tables: {...}, errors: [...] }
```

---

## 5. 部署方案

### 5.1 开发环境

```bash
# 后端
cd attendance-v3 && pip install -r requirements.txt
PORT=8001 python3 server/server.py &

# 前端
cd attendance-v3/client && npm install && npm run dev
# Vite proxy /api → http://127.0.0.1:8001
```

### 5.2 Docker 生产部署

```bash
docker build -t attendance-v3 .
docker run -d -p 8000:8000 -v attendance-data:/app/server/data attendance-v3
```

生产模式下后端同时提供前端静态资源 + API：

```
server.py
  ├── /api/*  → API 处理
  └── /*      → 静态文件 (Vite build dist/)
```

---

## 6. 依赖清单

### requirements.txt

```
openpyxl==3.1.5
PyJWT==2.8.0
bcrypt==4.1.2
```

### package.json

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "xlsx": "^0.18.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.4.0"
  }
}
```

Dexie.js 不再使用（数据存储已从 IndexedDB 迁移到 SQLite），SheetJS (`xlsx`) 仅用于前端 Excel 文件解析。

---

## 7. 与 v2.0 的关键差异

| 方面 | v2.0 (attendanceapp/) | v3.0 (attendance-v3/) |
|------|----------------------|----------------------|
| 数据存储 | 浏览器 IndexedDB (Dexie.js) | 服务端 SQLite |
| 认证 | 单账号 localStorage | JWT + bcrypt + 多用户 |
| 角色 | 无 | 三级 (employee/deptadmin/hradmin) |
| 前端架构 | 多 HTML 纯静态 | Vite + Vue Router SPA |
| 模块加载 | `<script src>` | ES Module import |
| 后端 | 单一 export_server.py | 模块化 handlers 拆分 |
| 工作流 | 无 | pending→confirmed→submitted→locked |
| 操作审计 | 无 | operation_logs 表 |

---

## 8. 实施顺序

| 阶段 | 内容 | 依赖 |
|------|------|------|
| S1 | 项目骨架创建：Vite 初始化 + Python server.py 入口 + database.py 建表 | 无 |
| S2 | 认证体系：users 表 + bcrypt + JWT + middleware + LoginView | S1 |
| S3 | 用户管理：users CRUD + UserManageView | S2 |
| S4 | 数据导入：punch/leave/overtime/travel/miss_punch/schedules 表 + ImportView | S3 |
| S5 | 考勤计算：rules.js 迁移 + API + 列表/日历视图 | S4 |
| S6 | 工作流：review_status 流转 + 确认/申诉/提交/锁定 | S5 |
| S7 | 导出中心：ExportView + 复用 v2.0 openpyxl 导出逻辑 | S5 |
| S8 | 系统设置 + 假期管理 | S3 |
| S9 | 数据迁移工具 | S5 |
| S10 | Docker + CI/CD + 文档 | S8 |

---

## 9. 关键设计决策

1. **SQLite 而非 MySQL/PostgreSQL**：单文件零配置，适合中小团队服务部署，Python 标准库自带 sqlite3 模块
2. **保持 http.server 而非 Flask/FastAPI**：与 v2.0 技术栈一致，降低学习曲线，减少外部依赖
3. **JWT 而非 Session**：无状态，前后端分离天然适配，无需额外 session 存储
4. **sessionStorage 存 token**：关闭浏览器即失效，在办公场景中强制每日登录更安全
5. **rules.js 从 IndexedDB 改为 server API**：规则引擎逻辑保留在前端计算（响应快），但数据源改为从 API 获取
6. **Dexie.js 移除**：数据不再存浏览器端，不需要 IndexedDB 封装库
