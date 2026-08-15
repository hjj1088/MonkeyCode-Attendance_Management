# 需求实施计划 -- V3.2 多角色考勤管理系统（真实完成度版）

- 对应设计: `.monkeycode/specs/phase2-multi-role-system/design.md`
- 对应需求: `.monkeycode/specs/phase2-multi-role-system/requirements.md`
- 复刻依据: `.monkeycode/specs/phase2-multi-role-system/v31-replica-reference.md`
- 本清单按**实际完成度**重制，取代旧版失真勾选。勾选状态以代码核实为准。

> 已确认决策：
> 1. V3.2 业务表沿用 V3.1 **camelCase** schema（不按 design.md 的 snake_case）
> 2. V3.2 前端新建 Vite + Vue3 SPA（`client/src`），但 V3.1 功能逻辑已完整整理到 `v31-replica-reference.md`，复刻不丢失功能

---

## 阶段 A：后端数据层（database.py）

- [x] A1. users 与 operation_logs 表 + 用户 CRUD 函数 [R1, R6]
  - [x] 在 `database.py` `init_db()` 中新增 `users` 表：`id, username, name, department, role, password_hash, enabled, login_attempts, locked_until, created_at, updated_at`（camelCase，与 V3.1 风格一致）
  - [x] 新增 `operation_logs` 表：`id, username, action, detail, created_at`
  - [x] 实现 `create_user(username, password_hash, name, department, role)`（用户名唯一）
  - [x] 实现 `get_user_by_username(username)` / `get_user_by_id(id)` / `get_all_users()`
  - [x] 实现 `update_user(id, fields)` / `set_user_enabled(id, enabled)`
  - [x] 实现 `increment_login_attempt(username)` / `reset_login_attempts(username)` / `clear_locked_if_expired(username)`
  - [x] 实现 `log_operation(username, action, detail)` 写 operation_logs
  - [x] A1.1 单元测试：`test/db/test_users.py`（创建/唯一性/启禁用/锁定计数）→ tests/test_users.py 9 PASS

- [x] A2. 系统初始化函数 [R1-7, R9]
  - [x] 实现 `init_system()`：首次启动写 settings 默认值（company_name + data_retention_days + 复用 attendance_config）
  - [x] 实现 `ensure_admin_user()`：首次启动创建 admin（bcrypt admin123）+ hradmin 角色（handlers/auth.py 现有，已验证）
  - [x] A2.1 单元测试：默认配置写入 + admin 账号自动创建（幂等）→ tests/test_auth.py + test_users.py 通过

- [x] A3. 泛型表操作函数 [R3, R5]
  - [x] 实现 `serialize_record()`（JSON 字段 dump + bool→0/1）+ `insert_records(table, records)` 泛型批量插入（复用 V3.1 序列化语义）
  - [x] 实现 `clear_table(table)` 清空函数
  - [x] A3.1 单元测试：插入/清空/JSON 序列化往返 → tests/test_generic_ops.py 4 PASS

## 阶段 B：后端路由挂载（server.py + middleware.py）

- [x] B1. 认证与用户路由 [R1, R6]
  - [x] 复用现有 `middleware.py`（generate_token/verify_token/require_role/_send_json 已完整）
  - [x] 完成 `handlers/auth.py`：`POST /api/auth/login`（bcrypt 校验 + 失败锁定 5 次 + 返回 JWT + `need_change_password` 标记）、`POST /api/auth/change-password`、`GET /api/auth/login-check`
  - [x] 完成 `handlers/users.py`：`GET/POST /api/users`、`PUT /api/users/<id>`、`PATCH /api/users/<id>/status`、`POST /api/users/reset-password`
  - [x] 在 `server.py` 注册 auth/users 路由（移除内联 HMAC 登录/鉴权，统一用 middleware PyJWT）
  - [x] B1.1 集成测试：登录/锁定/改密/用户 CRUD/角色鉴权 → tests/test_api_e2e.py 12 PASS

- [x] B2. 系统/规则/考勤/导出路由 [R3, R5, R8]
  - [x] 完成 `handlers/system.py`：`GET /api/system/status`、`GET /api/system/check-default-password`、`PUT /api/system/admin-password`、`GET/PUT /api/system/config`、`POST /api/system/seed-test-data`（列名对齐 camelCase）、`POST /api/system/reset-data`、`GET /api/system/version`
  - [x] 完成 `handlers/rules.py`（重写为 attendance_config 单键，camelCase 字段）：`GET/PUT /api/rules/config`、`GET/PUT /api/rules/tolerance`、`GET/POST /api/rules/holidays`、`DELETE /api/rules/holidays/<id>`、`GET /api/rules/work-schedule`
  - [x] 完成 `handlers/attendance.py`（列名对齐 camelCase）：`POST /api/attendance/import`、`GET /api/attendance/my|dept|all`、`POST /api/attendance/calculate`（完整字段+source*Ids）、`PATCH review/dept/submit/lock`、`GET summary` + leaves/travels/misses/overtime/data-month
  - [x] 完成 `handlers/export.py`（复用现有）：`POST /api/export/flat`、`POST /api/export/calendar`（保留条件格式）
  - [x] 在 `server.py` 注册全部路由（do_GET/POST/PUT/PATCH/DELETE；保留 V3.1 `/api/store/*` 兼容路由）
  - [x] attendance_results 表补 id 主键 + review_status/reviewed_by/reviewed_at 列，_migrate 重建旧表
  - [x] B2.1 测试：test_rules/test_system_init/test_workflow 全部启用 → 74+12 通过

## 阶段 C：前端 Vite SPA（client/src，全新重建）

> 复刻基线：`v31-replica-reference.md` 逐页行为必须保留。

- [x] C1. 项目骨架 + 基础设施 [R5, R8]
  - [x] 初始化 `client/vite.config.js`：dev 代理 `/api → http://127.0.0.1:8001` + `allowedHosts: ['.monkeycode-ai.online']`
  - [x] `client/src/main.js` / `App.vue`（含 AppSidebar + `<router-view />`，登录页隐藏侧栏）
  - [x] `client/src/router/index.js`：路由表 + `beforeEach` 守卫（无 token→登录、role 校验→默认页）
  - [x] `client/src/shared/api.js`：fetch 封装（Bearer token、401 清 token 跳登录）——复刻 api-store.js 的 401 语义
  - [x] `client/src/shared/store.js`：Store 接口（getAll/getByKey/getByIndex/getByRange/put/bulkPut/deleteByKey/clearTable/resetAllData）转调后端 `/api/store/*`
  - [x] 复制 bigsur.css 到 `client/src/assets/`
  - [x] C1.1 单元测试：api.js 401 跳转 + store.js 方法映射

- [x] C2. 共享逻辑迁移（ES Module 化）[R3, R5]
  - [x] `client/src/shared/excel.js`：复制 V3.1 并改 ES Module export；**移除 IndexedDB 读写**，保留 6 类识别/日期时间格式化/出差范围拆分/排班解析
  - [x] `client/src/shared/matcher.js`：ES Module 化，接收数据数组参数
  - [x] `client/src/shared/rules.js`：复制 V3.1 规则引擎（RULES_VERSION、9 状态判定优先级、容错豁免、加班调休结余、source*Ids），数据获取改走 store.js/后端 API
  - [x] C2.1 单元测试：excel 类型识别 + rules 状态判定（迟到/请假/缺勤/补卡豁免/容错豁免/结余）

- [x] C3. 认证 + 设置视图 [R1, R6, R3]
  - [x] `views/LoginView.vue`：登录表单 + 错误提示 + 加载态 + 版本号；登录成功检测 `need_change_password` → 改密引导
  - [x] `views/SetupWizardView.vue`：首次改密（新密码两次一致校验）
  - [x] `views/SettingsView.vue`：Tab（常规配置/管理员密码/系统状态/数据管理 seed+reset+表行数）
  - [x] `views/RulesSettingsView.vue`：Tab（考勤时段/容错规则/假期管理批量展开+删除）——复刻 V3.1 settings.html 行为（保存写 config_updated_at）

- [x] C4. 业务视图 [R3, R4, R5, R8]
  - [x] `views/ImportView.vue`：拖拽 + 多文件 + 类型徽标 + 预览前 10 条 + 去重 + 全部入库 + 导入日志；schedule 最后展开 + syncEmployees + config_updated_at
  - [x] `views/AttendanceView.vue` + `components/AttendanceTable.vue` + `components/AttendanceCalendar.vue`：复刻 attendance.html 双视图 + 详情弹窗 5 关联表 + 规则版本/config 变更提示 + 排班缺失提示 + 重新计算
  - [x] `views/MyAttendanceView.vue`：employee 个人考勤（my 接口）
  - [x] `views/ExportView.vue`：三列布局 + 模板管理 + 19 字段编辑 + 月份筛选 + 平铺/日历导出 + 实时预览
  - [x] `components/AppSidebar.vue`：按 role 动态渲染菜单（employee/deptadmin/hradmin）

## 阶段 D：检查点与补测试

- [x] D1. 检查点 - 认证 + 系统初始化
  - [x] 启动 → admin 登录 → 检测默认密码 → 强制改密 → 系统设置各 Tab 可用

- [x] D2. 检查点 - 考勤计算 + 视图
  - [x] seed 测试数据 → 导入 → 计算 → 列表 + 日历视图正确 → 详情弹窗关联正确

- [x] D3. 补测试（对应旧版失真勾选的 6.1/7.1/8.1/9.1/11.1/12.1/13.1，7 项）
  - [x] 用户管理：重复用户名拒绝 + 禁用后登录失败
  - [x] 导入：打卡 Excel 解析 → API 写入 → 查询确认
  - [x] 数据管理：seed 后各表数量 + reset 后业务表清空而 users/settings 保留
  - [x] 考勤计算：排班+请假→正常；容错豁免（月 2 次且 ≤30min）；结余正确性
  - [x] 工作流：pending→confirmed→submitted→locked 单向流转 + disputed→confirmed + 非管理员拒绝 + 锁定阻止修改
  - [x] 导出：平铺含正确字段与条件格式；日历按部门分组合并
  - [x] 迁移：V2.0 JSON 迁移后数据完整性 + 失败回滚

## 收尾

- [ ] 提交时排除 `*.db`、`__pycache__/`、`.vite/`、`.vscode/`、`attendanceapp/test_conditional_format.xlsx`
- [ ] 用 project-wiki skill 同步文档
- [ ] 启动前后端预览验证完整链路
