# 二期需求文档 -- 多角色考勤管理系统

- 版本: v2.0 (Phase 2)
- 日期: 2026-07-17
- 状态: 草稿

---

## 概述

将一期单用户本地工具升级为多角色 Web 考勤管理系统。引入员工、部门考勤管理员、人事管理员三级角色体系，实现"员工自查 → 部门补全 → 人事汇总导出"的协作工作流。后端从浏览器端 IndexedDB 迁移到 Python + SQLite 服务端数据库，账号密码加密存储，前端页面路由增加角色权限控制。

---

## 术语表

| 术语 | 定义 |
|------|------|
| **员工 (Employee)** | 普通员工角色，仅能查看本人的考勤记录和打卡数据 |
| **考勤管理员 (DeptAdmin)** | 部门级管理员角色，能查看和管理本部门所有员工的考勤数据，执行查漏补缺操作 |
| **人事管理员 (HRAdmin)** | 公司级管理员角色，能管理所有部门、所有员工、系统配置、数据导入和报表导出 |
| **考勤工作流** | 数据从导入到导出的三个环节：员工自查确认 → 考勤管理员补全修正 → 人事汇总导出 |
| **SQLite** | 服务端关系数据库，替代浏览器端 IndexedDB |
| **bcrypt** | 密码哈希算法，用于账号安全存储 |
| **JWT** | JSON Web Token，用于 API 请求的身份认证 |
| **EARS** | Easy Approach to Requirements Syntax，本文档使用的需求描述模板 |

---

## 需求

### R1: 用户认证与账号管理

**User Story:** AS 系统管理员，I want 创建和管理不同角色的用户账号，so that 员工和各级管理员能登录系统完成各自职责。

#### Acceptance Criteria

1. WHEN 人事管理员访问用户管理页面，系统 SHALL 展示所有用户列表（含姓名、部门、角色、账号状态）
2. WHEN 人事管理员创建新用户，系统 SHALL 保存账号名（唯一）、初始密码（bcrypt 哈希加密）、姓名、部门、角色（employee/deptadmin/hradmin）
3. WHEN 用户登录提交凭据，系统 SHALL 校验 bcrypt 哈希后返回 JWT token，token 有效期设为 24 小时
4. WHEN 用户使用错误凭据连续登录失败 5 次，系统 SHALL 锁定该账号 30 分钟
5. WHEN 人事管理员禁用某账号，系统 SHALL 使该账号的所有已签发 token 立即失效
6. WHEN 任意用户修改本人密码，系统 SHALL 验证原密码、加密新密码后更新存储
7. 系统 SHALL 存在一个内置超级管理员账号（admin），首次启动时自动创建，不可删除

---

### R2: 角色权限与页面隔离

**User Story:** AS 考勤管理员，I want 系统根据我的角色展示对应功能和数据，so that 我只能操作权限范围内的内容。

#### Acceptance Criteria

1. WHEN 员工角色登录，系统 SHALL 仅显示"我的考勤"页面，含个人打卡记录和考勤统计
2. WHEN 考勤管理员登录，系统 SHALL 显示"部门考勤"页面（仅本部门数据）、"我的考勤"页面
3. WHEN 人事管理员登录，系统 SHALL 显示完整导航：数据导入、考勤计算（全部员工）、导出中心、系统设置、用户管理
4. WHEN 用户尝试通过 URL 直接访问无权限页面，系统 SHALL 重定向到其有权限的默认页面
5. WHEN 用户未登录访问任何业务页面，系统 SHALL 重定向到登录页
6. 系统 SHALL 在前端页面加载时解码 JWT token 获取角色信息，根据角色渲染对应菜单项

---

### R3: 服务端数据库 (SQLite)

**User Story:** AS 系统，I want 将数据从浏览器 IndexedDB 迁移到服务端 SQLite，so that 数据集中存储、多用户共享、不依赖本地浏览器缓存。

#### Acceptance Criteria

1. 系统 SHALL 使用 SQLite 数据库存储所有业务数据，数据文件保存在服务端持久化目录
2. 系统 SHALL 创建 users 表，字段包含：id、username（唯一）、password_hash、name、department、role、enabled、locked_until、created_at
3. 系统 SHALL 创建 punch_records 表，字段包含：id、employee_no、name、department、date、period、sign_in、sign_out、late_minutes、early_minutes、absent、overtime_hours、schedule_start、schedule_end、raw_file_id、created_at
4. 系统 SHALL 创建与一期 IndexedDB 对应的其余表：leave_records、overtime_records、travel_records、miss_punch_records、schedules、attendance_results、carry_over、holidays、settings、export_templates、employees、raw_files
5. WHEN 前端发起数据请求，系统 SHALL 通过 `/api/*` 端点提供 CRUD 操作，所有请求需携带有效 JWT token
6. 系统 SHALL 在启动时自动创建数据库表（CREATE TABLE IF NOT EXISTS），数据库文件路径为 `data/attendance.db`

---

### R4: 考勤工作流

**User Story:** AS 部门考勤管理员，I want 一个"员工自查 → 我补全 → 人事汇总"的标准流程，so that 考勤数据经过层层核对后才能作为工资依据。

#### Acceptance Criteria

1. WHEN 数据导入完成，考勤计算结果 SHALL 携带状态 `pending_review`（待确认）
2. WHEN 员工查看本人考勤，系统 SHALL 展示当月考勤记录，允许对异常记录发起申诉（标注"申诉中"）
3. WHEN 考勤管理员查看部门考勤，系统 SHALL 显示每条记录的状态（待确认/已确认/申诉中），允许逐条确认或批量确认
4. WHEN 考勤管理员确认某条记录，系统 SHALL 将状态更新为 `confirmed`，记录确认人和确认时间
5. WHEN 部门全部记录确认后，考勤管理员 SHALL 可点击"提交部门汇总"将该部门标记为 `submitted`
6. WHEN 部门已提交且人事管理员锁定该月考勤，系统 SHALL 阻止该月份数据的修改和重新计算
7. WHEN 人事管理员查看汇总面板，系统 SHALL 展示各部门的状态进度（未导入/已导入/已确认/已提交/已锁定）

---

### R5: 前端架构升级 (Vite + npm)

**User Story:** AS 开发者，I want 使用 Vite + npm 构建前端项目，so that 开发体验、代码组织和组件复用能力得到提升。

#### Acceptance Criteria

1. 系统 SHALL 使用 `npm create vite@latest` 初始化 Vue 3 前端项目（JavaScript，Options API 模式）
2. 系统 SHALL 将一期业务逻辑（db.js、rules.js、excel.js、matcher.js、auth.js、layout.js）重构为 ES Module 导入方式
3. 系统 SHALL 使用 Vue Router 管理页面路由，通过导航守卫 `beforeEach` 实现角色权限控制
4. 系统 SHALL 将登录页提取为独立路由组件，统一在 App.vue 中挂载
5. 系统 SHALL 使用 Vite 开发服务器代理 `/api` 到后端 Python 服务（`http://localhost:8001`）
6. 前端 SHALL 不包含任何构建时依赖以外的第三方库（Vue、Dexie.js、SheetJS 均通过 npm 安装，不再使用 `shared/` 目录中的本地文件）
7. 系统 SHALL 保留一期 v2.0 的 Big Sur 设计系统 `bigsur.css` 作为全局样式

---

### R6: 数据安全与隔离

**User Story:** AS 部门考勤管理员，I want 只能查看本部门的数据，so that 其他部门的考勤信息不被泄露。

#### Acceptance Criteria

1. WHEN 非人事管理员访问数据查询 API，系统 SHALL 在服务端根据角色过滤数据范围（员工仅返回本人，部门管理员仅返回本部门）
2. WHEN 前端发起任何 API 请求，请求 SHALL 携带 `Authorization: Bearer <token>` 头
3. WHEN token 过期或无效，系统 SHALL 返回 401 状态码，前端自动跳转到登录页
4. 系统 SHALL 不在前端存储任何可被篡改的角色信息，角色从服务端 JWT token 中解析
5. 系统 SHALL 不在 URL query string 或 localStorage 中传递敏感数据（token 仅存储在 sessionStorage 或 httpOnly cookie 中）

---

### R7: 数据迁移与兼容

**User Story:** AS 人事管理员，I want 从一期系统中导出已有数据并导入二期，so that 历史考勤数据不丢失。

#### Acceptance Criteria

1. 系统 SHALL 提供一键迁移脚本：将一期 IndexedDB 数据导出为 JSON → 调 `/api/migrate` 批量写入 SQLite
2. 迁移 SHALL 保留原有打卡记录、OA 记录、排班、假期、计算结果的关联关系
3. WHEN 迁移过程中发生错误，系统 SHALL 回滚当前批次数据并记录错误日志
4. 一期 `attendance/` 和 `attendanceapp/` 目录 SHALL 保留在原位，不影响二期运行

---

### R8: 后端架构重构

**User Story:** AS 开发者，I want 后端代码模块化拆分，so that 新增 API 路由时不破坏现有导出功能。

#### Acceptance Criteria

1. 系统 SHALL 将现有 `export_server.py` 拆分为模块化结构：`server.py`（主入口）、`handlers/auth.py`、`handlers/users.py`、`handlers/attendance.py`、`handlers/export.py`、`database.py`（SQLite 管理）、`middleware.py`（JWT 校验/CORS）
2. 系统 SHALL 统一 JSON 响应格式：`{"code": 0, "data": {...}}` 成功，`{"code": 1, "message": "..."}` 失败
3. 系统 SHALL 使用连接池或单连接模式访问 SQLite，确保并发安全
4. 系统 SHALL 保留现有导出功能 `/api/export/flat` 和 `/api/export/calendar` 的行为与一期完全一致

---

### R9: 日志与运维

**User Story:** AS 运维人员，I want 系统记录关键操作日志，so that 能追溯考勤数据的修改历史。

#### Acceptance Criteria

1. WHEN 用户执行数据修改操作（导入、计算、确认、锁定），系统 SHALL 在 `operation_logs` 表中记录：操作人、时间、操作类型、目标数据范围
2. 系统 SHALL 在服务端以标准格式打印请求日志（延续 v2.0.2 的 Apache 格式）
3. WHEN 系统启动，SHALL 输出完整版本信息横幅（Git SHA、构建时间、数据库路径、端口）
