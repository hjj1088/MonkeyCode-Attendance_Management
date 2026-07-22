# 需求实施计划 -- V3.0 多角色考勤管理系统

- 对应设计: `.monkeycode/specs/phase2-multi-role-system/design.md`
- 对应需求: `.monkeycode/specs/phase2-multi-role-system/requirements.md`

---

- [ ] 1. 项目骨架创建与基础环境 [R5, R8]
  - 使用 `npm create vite@latest` 初始化 Vue 3 前端项目，JavaScript + Options API 模式
  - 安装依赖：`vue-router`, `xlsx`
  - 安装 devDependencies：`@vitejs/plugin-vue`, `vite`
  - 创建 `client/vite.config.js`，配置开发代理 `/api` → `http://127.0.0.1:8001`，配置 `allowedHosts: ['.monkeycode-ai.online']`
  - 创建 `client/index.html` 入口文件
  - 创建 `server/server.py` 主入口文件，继承 `http.server.BaseHTTPRequestHandler`
  - 创建 `server/database.py`，实现 `get_db()` 连接函数和 `init_tables()` 建表函数（CREATE TABLE IF NOT EXISTS）
  - 创建 `server/middleware.py`，实现 `_send_json()` 统一响应、`_read_body()` 请求体解析、CORS 头
  - 创建 `requirements.txt`：`openpyxl==3.1.5`, `PyJWT==2.8.0`, `bcrypt==4.1.2`
  - 创建 `server/data/.gitkeep`，确保 data 目录存在
  - 创建 `client/src/main.js` 挂载 Vue 应用，引入 router 并 mount 到 `#app`
  - 创建 `client/src/App.vue` 根组件，包含 `<router-view />` 占位
  - 创建 `client/src/router/index.js`，定义所有路由表的骨架（仅 path + component 占位，暂不实现守卫）
  - 创建 `client/src/shared/api.js`，封装 `fetch` 请求函数（自动附加 Bearer token，401 自动跳转登录）
  - 从 `attendanceapp/shared/bigsur.css` 复制到 `client/src/assets/bigsur.css`
  - 在 `App.vue` 中全局引入 `bigsur.css`
  - [ ] 1.1 编写项目初始化验证测试
    - 验证 `db.get_db()` 返回可用连接
    - 验证 `db.init_tables()` 创建所有15张表

- [ ] 2. 认证体系：users 表 + bcrypt + JWT + 登录页 [R1, R6]
  - 在 `database.py` 的 `init_tables()` 中创建 users 表：`id, username(unique), password_hash, name, department, role, enabled, locked_until, created_at`
  - 在 `database.py` 中实现 `ensure_admin_user()` 函数，首次启动自动创建 admin 账号（bcrypt 哈希密码）
  - 在 `database.py` 中实现用户 CRUD 函数：`create_user()`, `get_user_by_username()`, `get_all_users()`, `update_user()`, `set_user_enabled()`, `increment_login_attempt()`
  - 在 `middleware.py` 中实现 `generate_token(user_id, username, role, department)` 和 `verify_token(token)`，24小时过期，使用 HS256
  - 在 `middleware.py` 中实现 `require_role(*roles)` 装饰器，从 Authorization header 提取 token、验证、校验角色
  - 创建 `server/handlers/` 目录和 `__init__.py`
  - 创建 `server/handlers/auth.py`，实现 `POST /api/auth/login`：校验用户名/密码/bcrypt → 失败计数锁定 → 成功返回 JWT
  - 创建 `server/handlers/auth.py`，实现 `POST /api/auth/change-password`：验证 token + 原密码 → 更新 bcrypt 哈希
  - 在 `server.py` 的 `do_GET` / `do_POST` / `do_OPTIONS` 中注册 auth 路由
  - 创建 `client/src/views/LoginView.vue`，登录表单（用户名/密码），居中毛玻璃卡片布局
  - 创建 `client/src/components/AppSidebar.vue`，根据 token 中的 role 动态渲染菜单项
  - 创建 `client/src/App.vue` 完整布局：左侧 AppSidebar + 右侧 `<router-view />`，非登录页显示侧边栏
  - 实现 `router/index.js` 的 `beforeEach` 守卫：无 token 跳转登录、role 校验跳转默认页
  - [ ] 2.1 编写认证模块单元测试
    - 测试 bcrypt 密码哈希和校验
    - 测试 JWT token 生成和验证（包括过期 token）
    - 测试 5 次登录失败锁定逻辑

- [ ] 3. 检查点 - 确保登录流程和数据库基础功能正常
  - 启动 `server.py`，验证 `/api/auth/login` 能用 admin 登录并返回 token
  - 启动 `npm run dev`，验证登录页显示、登录成功跳转、未登录访问被拦截

- [ ] 4. 用户管理：CRUD + 用户管理页面 [R1, R6]
  - 创建 `server/handlers/users.py`，实现 `GET /api/users`（列表，仅 hradmin）
  - 实现 `POST /api/users`（创建，用户名唯一校验，bcrypt 加密初始密码）
  - 实现 `PUT /api/users/<id>`（编辑姓名/部门/角色）
  - 实现 `PATCH /api/users/<id>/status`（启用/禁用，禁用时记录操作日志）
  - 在 `server.py` 中注册 users 路由
  - 创建 `client/src/views/UserManageView.vue`，用户列表表格 + 新增/编辑弹窗 + 启用/禁用开关
  - [ ] 4.1 编写用户管理单元测试
    - 测试创建重复用户名被拒绝
    - 测试禁用用户后 token 验证失败

- [ ] 5. 数据导入：6 类数据表 + ImportView [R3, R5]
  - 在 `database.py` 的 `init_tables()` 中创建 punch_records、leave_records、overtime_records、travel_records、miss_punch_records、schedules、employees、raw_files 表
  - 为每张表实现 `insert_records(table, records)` 泛型插入函数和 `clear_table(table)` 清空函数
  - 创建 `server/handlers/attendance.py`，实现 `POST /api/attendance/import`（接收 JSON 批量写入 SQLite）
  - 从 `attendanceapp/shared/excel.js` 复制 Excel 解析逻辑到 `client/src/shared/excel.js`，改为 ES Module export
  - 从 `attendanceapp/shared/matcher.js` 复制匹配逻辑到 `client/src/shared/matcher.js`，改为 ES Module export
  - 修改 `excel.js`：移除所有 IndexedDB 读写（`Store.*`），改为纯解析工具函数
  - 修改 `matcher.js`：接收数据数组作为参数，不再依赖 IndexedDB
  - 创建 `client/src/views/ImportView.vue`：拖拽上传 + 类型识别 + 预览表格 + 确认导入
  - 导入成功后调用 `POST /api/attendance/import` 将数据同步到服务端
  - [ ] 5.1 编写导入功能集成测试
    - 测试上传打卡 Excel → 解析 → API 写入 → 查询确认

- [ ] 6. 考勤计算：rules.js 迁移 + API + 双视图 [R3, R5]
  - 从 `attendanceapp/shared/rules.js` 复制规则引擎到 `client/src/shared/rules.js`，改为 ES Module export
  - 修改 `rules.js`：所有 `Store.get*()` / `DB.*` 调用改为通过 `api.js` 调用后端 API
  - 在 `server/handlers/attendance.py` 中实现 `POST /api/attendance/calculate`（接收计算结果批量 upsert 到 attendance_results）
  - 在 `server/handlers/attendance.py` 中实现 `GET /api/attendance/my`（返回本人当月结果）
  - 在 `server/handlers/attendance.py` 中实现 `GET /api/attendance/dept`（返回本部门结果，deptadmin+）
  - 在 `server/handlers/attendance.py` 中实现 `GET /api/attendance/all`（全公司，hradmin，支持部门/月份/状态筛选）
  - 创建 `client/src/components/AttendanceTable.vue`：列表视图表格组件（状态颜色徽标、点击行详情弹窗）
  - 创建 `client/src/components/AttendanceCalendar.vue`：日历视图组件（日期格内显示签到/签退、颜色标识）
  - 创建 `client/src/views/MyAttendanceView.vue`：个人考勤页，包含列表/日历切换 + 申诉按钮
  - 创建 `client/src/views/AllAttendanceView.vue`：全公司考勤页（hradmin），含部门/月份/状态筛选
  - [ ] 6.1 编写考勤计算单元测试
    - 测试 given 打卡+排班+请假 → 正常出勤状态
    - 测试 容错规则豁免逻辑（月累计2次且≤30min）
    - 测试 加班结余计算正确性

- [ ] 7. 检查点 - 确保考勤计算和视图功能正常
  - 导入测试数据 → 执行计算 → 验证列表视图和日历视图显示正确

- [ ] 8. 工作流：review_status 四状态流转 [R4]
  - 在 `server/handlers/attendance.py` 中实现 `PATCH /api/attendance/<id>/review`（确认/标记争议，记录 reviewed_by 和 reviewed_at）
  - 实现 `PATCH /api/attendance/dept/submit`（批量提交部门当月数据，状态 confirmed → submitted）
  - 实现 `PATCH /api/attendance/lock`（锁定指定月份，hradmin，阻止修改）
  - 实现 `GET /api/attendance/summary`（汇总面板：各部门状态进度）
  - 创建 `client/src/components/ReviewPanel.vue`：单条确认按钮 + 批量确认按钮 + 提交部门汇总按钮
  - 创建 `client/src/views/DeptAttendanceView.vue`：部门考勤页，ReviewPanel 集成，展示本部门所有员工数据
  - 在 `MyAttendanceView.vue` 中添加员工申诉按钮，调用 `PATCH /api/attendance/<id>/review` 标记 disputed
  - 在 `AllAttendanceView.vue` 中添加汇总面板 tab
  - [ ] 8.1 编写工作流状态机测试
    - 测试 pending_review → confirmed → submitted → locked 流转
    - 测试 locked 后拒绝修改

- [ ] 9. 导出中心：ExportView + 复用 openpyxl 导出 [R8]
  - 从 `attendanceapp/export_server.py` 复制 `build_flat_report()` 和 `build_calendar_report()` 到 `server/handlers/export.py`
  - 在 `server/handlers/export.py` 中实现 `POST /api/export/flat`（保持与 v2.0 完全一致的行为）
  - 实现 `POST /api/export/calendar`（保持与 v2.0 完全一致的行为）
  - 从 `attendanceapp/export.html` 迁移导出页面逻辑，创建 `client/src/views/ExportView.vue`
  - ExportView 包含：模板列表 + 字段编辑器 + 实时预览 + 平铺导出 + 日历导出按钮
  - [ ] 9.1 编写导出功能回归测试
    - 验证 Flat 导出生成的 xlsx 包含正确的条件格式
    - 验证 Calendar 导出生成的 xlsx 包含 2 条全局 FormulaRule

- [ ] 10. 系统设置 + 假期管理 [R3]
  - 在 `server/handlers/attendance.py` 中实现 settings 表的读写 API
  - 实现 `GET /api/holidays` 和 `POST /api/holidays`（holidays CRUD）
  - 创建 `client/src/views/SettingsView.vue`：考勤规则配置 + 假期管理（日期选择器批量添加/删除）
  - [ ] 10.1 编写 settings 生命周期测试
    - 测试配置变更后触发重新计算提示

- [ ] 11. 操作日志与运维 [R9]
  - 在 `database.py` 的 `init_tables()` 中创建 operation_logs 表
  - 实现 `log_operation(operator, action, target, detail)` 写入函数
  - 在用户管理、考勤确认、数据锁定等关键操作点调用 `log_operation()`
  - 在 `server.py` 的 `log_message()` 中保留 Apache 格式的请求日志
  - 在 `server.py` 启动时打印完整版本横幅（延续 v2.0.2 风格）

- [ ] 12. 数据迁移工具 [R7]
  - 创建 `client/src/views/MigrateView.vue`（hradmin only），从 IndexedDB 导出全量 JSON 并下载
  - 在 `server/handlers/attendance.py` 中实现 `POST /api/migrate`（接收 JSON 逐表写入 SQLite，事务回滚）
  - 迁移完成后返回报告：各表导入行数 + 错误列表
  - [ ] 12.1 编写迁移端到端测试
    - 用一期测试数据验证迁移后考勤结果一致性

- [ ] 13. Docker 构建与 CI/CD [R8]
  - 创建 `attendance-v3/Dockerfile`（python:3.12-slim + 构建参数注入 + 前端 build + 后端服务）
  - 创建 `.github/workflows/docker-publish-v3.yml`（自动构建发布到 GHCR）
  - Dockerfile 构建时先 `npm build` 生成 `dist/`，然后 `server.py` 同时服务静态文件 + API

- [ ] 14. 检查点 - 完整功能验证
  - Docker 构建通过 → 部署 → /health 返回正确版本
  - 登录 admin → 创建员工账号 → 员工登录只能看本人考勤
  - 导入测试数据 → 计算 → 部门管理员确认 → 人事锁定 → 导出 xlsx 格式正确
