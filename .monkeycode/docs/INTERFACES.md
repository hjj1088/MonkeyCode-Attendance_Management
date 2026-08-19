# 接口文档

## 数据库 Schema

基于 Dexie.js 的 IndexedDB 数据库 `AttendanceDB`，共 13 张表。

### 表结构

#### raw_files
已导入文件的记录（用于去重）。
```js
'++id, fileType, importTime'
```
| 字段 | 说明 |
|------|------|
| id | 自增主键 |
| fileName | 文件名 |
| fileType | 文件类型 (punch/leave/overtime/travel/miss_punch/schedule) |
| importTime | 导入时间 |

#### punch_records - 打卡记录
```js
'++id, employeeNo, name, date, department'
```
| 字段 | 说明 |
|------|------|
| id | 自增主键 |
| employeeNo | 考勤号 |
| name | 姓名 |
| date | 日期 (YYYY-MM-DD) |
| period | 时段 (上午/下午) |
| scheduleStart | 排班上班时间 |
| scheduleEnd | 排班下班时间 |
| signIn | 签到时间 |
| signOut | 签退时间 |
| lateMinutes | 迟到(分钟) |
| earlyMinutes | 早退(分钟) |
| absent | 是否旷工 |
| overtimeHours | 加班时间 |
| department | 部门 |

#### leave_records - 请假记录
```js
'++id, applicant, startDate, endDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| department | 申请部门 |
| leaveType | 请假类型 (含"调休"关键字触发结余扣减) |
| startDate | 开始日期 |
| endDate | 结束日期 |
| leaveDays | 请假天数 |
| leaveHours | 请假小时数 |
| reason | 请假事由 |

#### overtime_records - 加班记录
```js
'++id, applicant'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| startTime | 加班起止时间原始值（Excel 数值转 YYYY-MM-DD 或文本原样存储，用于日期匹配追溯） |
| endTime | 结束时间 |
| overtimeHours | 加班小时数 |
| content | 加班内容 |

> **v2.0.2 修复**：`startTime` 原为空字符串导致 `calculateMonth` 无法按日期匹配加班 OA。现已改为解析 `加班起止时间` Excel 字段，支持数值和文本两种格式。

#### travel_records - 出差记录
```js
'++id, applicant, startDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| startDate | 开始日期 |
| endDate | 结束日期 |
| destination | 目的地 |
| reason | 出差事由 |

#### miss_punch_records - 漏打卡记录
```js
'++id, applicant, missDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| missDate | 忘记打卡日期 |
| missPerson | 忘打卡人员 |
| missTime | 未打卡时间 |
| cardTime | 当天刷卡时间 |
| reason | 事由 |

#### schedules - 排班表 (按员工展开)
```js
'++id, [employeeNo+year+month], year, month'
```
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| department | 部门 |
| year | 年份 |
| month | 月份 |
| workDays | `{ "01": true, "02": false, ... }` - 每天是否上班 |

#### attendance_results - 考勤计算结果
```js
'[employeeNo+date], employeeNo, date, month, department, status'
```
主关键字为 `[employeeNo+date]` 联合主键，确保每人每天仅一条结果。
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| department | 部门 |
| date | 日期 |
| month | 月份 |
| status | 考勤状态 (normal/rest/abnormal/leave/travel/absent/no_sign_in/no_sign_out) |
| signIn | 签到时间 |
| signOut | 签退时间 |
| lateMinutes | 迟到分钟 |
| earlyMinutes | 早退分钟 |
| overtimeHours | 加班小时 |
| travelHours | 出差小时 |
| workHours | 实际工作时长 (v2.0 新增，由 signIn/signOut 计算，精确到0.01小时) |
| leaveType | 请假类型 |
| isRestDay | 是否排班休息日 (仅由排班表+假期决定) |
| absent | 是否旷工 |
| sourcePunchIds | 关联打卡记录 ID 列表 |
| sourceLeaveIds | 关联请假记录 ID 列表 |
| sourceTravelIds | 关联出差记录 ID 列表 |
| sourceMissIds | 关联漏打卡记录 ID 列表 |
| sourceOvertimeIds | 关联加班记录 ID 列表 |

#### carry_over - 加班结余
```js
'[employeeNo+month], employeeNo, month'
```
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| month | 月份 |
| overtimeBalance | 累计结余小时 (非负) |

#### holidays - 假期管理
```js
'++id, date'
```
| 字段 | 说明 |
|------|------|
| date | 日期 |
| name | 假期名称 |
| isWorkday | 是否调休上班日 |
| isHoliday | 是否休息日 |

#### settings - 系统设置 (key-value)
```js
'key'
```
| key | value |
|-----|-------|
| attendance_config | 考勤规则配置对象 |
| config_updated_at | 配置更新时间戳 |
| last_calc_{YYYY-MM} | 某月份最后计算时间 |
| last_punch_month | 最近一次打卡导入数据的月份（`YYYY-MM`，取导入记录中最早日期） |

#### export_templates - 导出模板
```js
'++id, isDefault'
```

#### employees - 员工列表
```js
'employeeNo, name, department'
```

## Store CRUD API

所有表通过 `Store` 工具对象访问：

| 方法 | 说明 |
|------|------|
| `Store.bulkPut(tableName, records)` | 批量插入/更新，自动 JSON 深拷贝防污染 |
| `Store.clearTable(tableName)` | 清空表 |
| `Store.getAll(tableName)` | 获取全部记录 |
| `Store.getByIndex(tableName, indexName, value)` | 按索引查询 |
| `Store.getByRange(tableName, indexName, lower, upper)` | 按索引范围查询 |
| `Store.getByKey(tableName, key)` | 按主键查询 |
| `Store.put(tableName, record)` | 插入/更新单条 |
| `Store.deleteByKey(tableName, key)` | 按主键删除 |
| `Store.resetAllData()` | 清空所有表并重新初始化 |

> **注意**：Dexie 4.0.8 中 `bulkPut` 会修改传入数组，必须在写入前通过 `JSON.parse(JSON.stringify(value))` 创建深拷贝。

## 文件类型识别规则

`Excel.identifyFileType()` 通过表头关键词匹配识别以下类型：

| 类型 | 必含表头 | 加分表头 |
|------|----------|----------|
| punch (打卡) | 考勤号码, 签到时间 | 签退时间, 迟到时间, 部门, 日期 |
| leave (请假) | 请假类型, 开始日期 | 结束日期, 请假天数, 申请人 |
| overtime (加班) | 加班起止时间 | 申请人, 加班内容 |
| travel (出差) | 出差起止日期 | 申请人, 目的地, 出差事由 |
| miss_punch (漏打卡) | 忘打卡日期 | 申请人, 未打卡时间, 事由 |

排班文件通过 Sheet 名称识别：匹配 `^\\d{1,2}月$` 的 Sheet 名。

## 认证 API

```js
Auth.isLoggedIn()        // 检查是否已登录
Auth.login(user, pass)   // 登录 (默认 admin/admin123)
Auth.logout()            // 登出并跳转到登录页
Auth.requireAuth()       // 页面守卫 (未登录跳转)
```

## Matcher API

```js
Matcher.buildEmployeeMap()           // 从打卡记录构建 { 考勤号 -> {name, dept} }
Matcher.syncEmployees()              // 同步到 employees 表
Matcher.resolveEmployeeNo(name, dept) // 姓名+部门 -> 考勤号
Matcher.matchOAToPunch(records, type) // OA 记录 -> 考勤号匹配
```

## AppLayout API (v2.0 新增)

```js
AppLayout.init()         // 初始化侧边栏导航（4个导航项：导入/考勤/导出/设置）+ 问候语
AppLayout.toggleMenu()   // 移动端侧边栏开关
AppLayout.closeMenu()    // 关闭移动端侧边栏
```

导航项通过 `_detectPage()` 自动高亮当前页面。问候语通过 `_updateGreeting()` 按时间段生成（上午好/下午好/晚上好）。

## 兼容桥接层 API (v2.0 新增)

`shared/init.js` 提供向后兼容的模块映射：

```js
window.AttendanceDB      // Proxy 代理，映射 punches->punch_records, leaves->leave_records
window.AttendanceRules   // 适配旧的 get()/save() API 到新的 settings 表
window.AttendanceMatcher // 提供简化的规则 match() 方法
```

## RulesEngine API

```js
RulesEngine.getConfig()                  // 获取考勤规则配置
RulesEngine.getHolidays()                // 获取全部假期
RulesEngine.calculateMonth(targetMonth)  // 计算指定月考勤
RulesEngine.getMonthResults(targetMonth) // 获取某月考勤结果
RulesEngine.getResultDetail(eno, date)   // 获取某天详情 (含关联源记录)
```

## HTTP 导出 API

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/health` | GET | — | JSON `{status, version, build_time, python, server_time}` |
| `/api/export/flat` | POST | `{records: array, template: {fields: [{label, field}]}, filename: string, startTime: string, endTime: string}` | 二进制 XLSX |
| `/api/export/calendar` | POST | `{targetMonth: "YYYY-MM", fields: array, results: array, schedules: array, holidays: array, startTime: string, endTime: string}` | 二进制 XLSX |
| `/*` | OPTIONS | — | 204, `Access-Control-Allow-Origin: *` (CORS 预检) |

> `GET /health` 为 v2.0.3 新增端点，返回服务版本信息（Git SHA、构建时间、Python 版本）用于验证 Docker 镜像版本。`startTime`/`endTime` 为选填参数，格式 `HH:MM`（如 `08:30`/`17:30`）。传入后用于生成迟到/早退条件格式规则；未传入时自动从排班数据或打卡记录中提取，兜底默认值为 `08:30`/`17:30`。

---

# V3.1 REST API（数据层迁移）

> 本节描述 v3.1（`attendance-v3/`）的后端 REST API。V3.1 将 V2.0 前端 `Store` 对象的所有 IndexedDB 操作映射为 HTTP 端点，`shared/api-store.js` 通过 `fetch` 调用这些端点。

## 通用约定

- **Base URL**：`http://localhost:8001`（V3.1 后端端口）
- **响应格式**：所有 API 返回 JSON `{code: 0, data: ...}`；非 0 的 `code` 表示错误，`message` 携带错误说明
- **认证**：除 `/api/auth/login` 和 `/api/auth/login-check` 外，所有 `/api/*` 请求必须携带 `Authorization: Bearer <token>` 头
- **401 处理**：前端 `api-store.js` 收到 401 时清除凭证并跳转 `index.html`

## 认证 API

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/api/auth/login` | POST | `{username: "admin", password: "admin123"}` | `{code:0, data:{token, username}}` |
| `/api/auth/login-check` | GET | —（Bearer token） | `{code:0}` 或 401 |

JWT 采用 HS256 签名，有效期 24 小时。默认账号 `admin` / `admin123`（后端 SHA256 哈希比对）。token 存入 `sessionStorage`，关闭标签页即失效。

## Store CRUD API（映射 V2.0 Store 方法）

`api-store.js` 的每个方法对应一个 REST 端点：

| Store 方法 | HTTP 端点 | 说明 |
|-----------|-----------|------|
| `Store.getAll(table)` | `GET /api/store/{table}` | 获取全表；可选 `?index=&value=` 过滤 |
| `Store.getByIndex(table, idx, val)` | `GET /api/store/{table}?index=&value=` | 按单列索引查询 |
| `Store.getByRange(table, idx, lower, upper)` | `GET /api/store/{table}/range?index=&lower=&upper=` | 按索引范围查询 |
| `Store.getByKey(table, key)` | `GET /api/store/{table}/{key}` | 按主键查询（settings 按 key，其余按 id） |
| `Store.put(table, record)` | `POST /api/store/{table}` | 单条插入/更新（body `{record}`） |
| `Store.bulkPut(table, records)` | `POST /api/store/{table}/bulk` | 批量插入（body `{records}`，返回 `data.count`） |
| `Store.clearTable(table)` | `DELETE /api/store/{table}` | 清空整表 |
| `Store.deleteByKey(table, key)` | `DELETE /api/store/{table}/{key}` | 按主键删除 |
| `Store.resetAllData()` | `POST /api/store/reset` | 清空 13 张表并重建默认设置 |

### 字段序列化规则（server.py `json_serialize`）

- 对象/数组字段（`workDays`、`fields`、`sourcePunchIds` 等）在 SQLite 中存 TEXT，API 层自动 `json.dumps` / `json.loads`
- 布尔字段（`isWorkday`、`isHoliday`、`absent`）后端存 INTEGER (0/1)，API 层序列化为 `bool`
- `attendance_results` 与 `carry_over` 表无 `id` 主键，按业务键（如 `employeeNo+date`）语义操作

## 导出 API（V3.1）

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/api/export/flat` | POST | `{records, template:{fields:[{label,field}]}, filename, startTime, endTime}` | 二进制 XLSX |
| `/api/export/calendar` | POST | `{targetMonth:"YYYY-MM", fields, results, schedules, holidays, startTime, endTime}` | 二进制 XLSX |

响应头 `Content-Disposition` 使用 `filename*=UTF-8''{urlencoded}`（RFC 5987）以支持中文文件名。逻辑与 V2.0 `export_server.py` 完全一致（`build_flat_report` / `build_calendar_report`，见 [模块/export-server-模块.md](./模块/export-server-模块.md) 与 [模块/V3.1-后端服务-模块.md](./模块/V3.1-后端服务-模块.md)）。

## SQLite 数据库（V3.1）

13 张表结构与 V2.0 IndexedDB 完全一致（字段名 camelCase），详见 [模块/V3.1-后端服务-模块.md](./模块/V3.1-后端服务-模块.md#sqlite-表结构)。差异点：

- IndexedDB 复合主键（如 `[employeeNo+date]`）→ SQLite 无主键 + 单列索引 + 应用层约束
- IndexedDB 复合索引（如 `[employeeNo+year+month]`）→ SQLite 单列索引 + JS 内存过滤
- `settings` 表主键为 `key`；`employees` 表主键为 `employeeNo`
- 默认数据由 `database.py _init_settings()` 初始化（attendance_config + 默认导出模板）

---

# V3.2 REST API（多角色系统）

> 本节描述 v3.2 相对 v3.1 的接口变化。V3.2 启用全部 handler（auth/users/system/rules/attendance/export/migrate）与 `middleware.py` PyJWT 统一认证，并新增多角色、审核工作流、用户管理等端点。

## 通用约定（V3.2）

- **端口**：后端 `http://127.0.0.1:8001`；前端 Vite dev `http://127.0.0.1:8002`（`/api` 代理到 8001）
- **认证**：除 `/api/auth/login`、`/api/auth/login-check`、`/api/system/version` 外，一律 `Authorization: Bearer <token>`（PyJWT，HS256，24h）
- **登录响应**：`{code:0, data:{token, user:{id,username,name,department,role}, need_change_password}}`
- **默认账号**：`admin` / `admin123`（bcrypt），密码仍为默认值时登录返回 `need_change_password: true`，前端引导强制改密
- **登录锁定**：连续 5 次密码错误锁定 30 分钟（`users.login_attempts` / `locked_until`）
- **角色**：`hradmin` / `deptadmin` / `employee`；`middleware.py` 提供 `_require_hradmin` / `_require_any_user` 鉴权

## 新增数据库表

### users（V3.2）

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增 |
| username | TEXT UNIQUE | 登录名 |
| name | TEXT | 姓名 |
| department | TEXT | 部门 |
| role | TEXT | hradmin/deptadmin/employee |
| password_hash | TEXT | bcrypt 哈希 |
| enabled | INTEGER | 1 启用 / 0 禁用 |
| login_attempts | INTEGER | 连续失败次数 |
| locked_until | TEXT | 锁定截止时间 |
| created_at / updated_at | TEXT | 时间戳 |

### operation_logs（V3.2）

| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增 |
| username | TEXT | 操作人 |
| action | TEXT | 动作（review/dept_submit/lock/create_user…） |
| detail | TEXT | JSON 详情 |
| created_at | TEXT | 时间戳 |

### attendance_results 新增列（V3.2）

相对 V3.1 增加 `id`（INTEGER PK）、`review_status`（默认 `pending_review`）、`reviewed_by`、`reviewed_at`、`missTime`。V3.1 库通过 `database.py _migrate()` 自动升级（重命名旧表 + 拷贝 + 重建索引）。

## 用户与认证 API（V3.2）

| 端点 | 方法 | 请求体 | 角色 |
|------|------|--------|------|
| `/api/auth/login` | POST | `{username, password}` | 公开 |
| `/api/auth/change-password` | POST | `{old_password, new_password}` | 登录 |
| `/api/users` | GET/POST | POST `{username,name,department,role,password}` | hradmin |
| `/api/users/{id}/status` | PATCH | `{enabled:0\|1}` | hradmin |
| `/api/users/reset-password` | POST | `{username, new_password}` | hradmin |

## 系统与规则 API（V3.2）

| 端点 | 方法 | 请求体 | 角色 |
|------|------|--------|------|
| `/api/system/version` `/config` | GET | — | 登录 |
| `/api/system/status` | GET | —（含各表行数） | hradmin |
| `/api/system/admin-password` | PUT | `{current_password, new_password}` | hradmin |
| `/api/system/check-default-password` | GET | — | hradmin |
| `/api/system/seed-test-data` | POST | — | hradmin |
| `/api/system/reset-data` | POST | —（清业务表，保留 users/settings） | hradmin |
| `/api/rules/config` | GET/PUT | 考勤时段 | hradmin |
| `/api/rules/tolerance` | GET/PUT | 容错规则 | hradmin |
| `/api/rules/holidays` | GET/POST/DELETE | 假期管理 | hradmin |
| `/api/rules/work-schedule` | GET | 排班信息 | hradmin |

`rules` 配置统一存 `settings.attendance_config` 单键（camelCase：workStartTime/workEndTime/lateThreshold/earlyThreshold/graceTimes/graceMinutes），与 V3.1 前端契约一致。

## 考勤 API（V3.2）

| 端点 | 方法 | 请求体 | 角色 |
|------|------|--------|------|
| `/api/attendance/import` | POST | `{type, records, file_name}`（6 类型） | 登录 |
| `/api/attendance/calculate` | POST | `{results, month, carry_over}` | 登录 |
| `/api/attendance/my?month=` | GET | —（按 `name`+month 查询本人） | 登录 |
| `/api/attendance/all?month=` | GET | —（deptadmin 过滤本部门，employee 403） | deptadmin/hradmin |
| `/api/attendance/summary` | GET | —（按部门/状态汇总） | hradmin |
| `/api/attendance/{id}/review` | PATCH | `{review_status}` | deptadmin/hradmin |
| `/api/attendance/dept/submit` | PATCH | `{month}`（hradmin 提交全部，deptadmin 提交本部门） | deptadmin/hradmin |
| `/api/attendance/lock` | PATCH | `{month}`（要求该月全部 submitted） | hradmin |
| `/api/attendance/leaves` `/travels` `/misses` `/overtime` `/data-month` | GET | 各类 OA 数据 | 登录 |

`handle_attendance_calculate` 行为：删除该 `month` 旧结果 → 批量插入 `results`（含 review 三字段）→ 写入 `carry_over`。

`handle_import` 行为（punch 类型）：导入前清空 `punch_records` 整表 → `_sync_employees` 建立名册 → 记录 `settings.last_punch_month`（records 中最早日期的 `YYYY-MM`，`ON CONFLICT` 更新）→ 写入 `raw_files`。

### 审核状态机（`valid_transitions`）

```
pending_review → confirmed / disputed
confirmed → disputed
disputed → confirmed
submitted / locked → （终态，不可变更）
```

## 迁移 API（V3.2）

`POST /api/migrate`（hradmin）：请求体为 V2.0 导出 JSON（`{employee, punch, leave, schedule, holiday, settings, attendance_results, carry_over}`），按字段映射 `INSERT OR IGNORE` 落库；单条失败记入 `report.errors`，整体异常时 `conn.rollback()` 并报告"已回滚"。注意：迁移前 `None` 值必须转为 `''`，否则违反 NOT NULL 约束会被 `INSERT OR IGNORE` 静默忽略（实际零落库）。

## store 表名映射（V3.2）

`/api/store/{table}` 支持 V3.1 前端短表名，自动映射物理表名：

| 短表名 | 物理表 |
|--------|--------|
| punch | punch_records |
| leave | leave_records |
| overtime | overtime_records |
| travel | travel_records |
| miss_punch | miss_punch_records |
| schedule | schedules |

其余（settings/employees/holidays/carry_over/export_templates/attendance_results/users…）同名。`PRIMARY_KEYS = {employees: 'employeeNo', settings: 'key'}`，其余默认 `id`。

## 字段序列化（V3.2）

- `json_serialize` 对 `value`（settings）、`workDays`（schedules）、`fields`（export_templates）、`source*Ids`（attendance_results）自动 `json.loads` 反序列化——**前端取到的 settings.value 是对象**，测试 mock 与断言需按对象处理
- 布尔列（isWorkday/isHoliday/isDefault/absent/isRestDay）序列化为 `bool`
