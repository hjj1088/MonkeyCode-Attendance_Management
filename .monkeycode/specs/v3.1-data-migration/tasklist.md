# 考勤管理系统 V3.1 实施计划

## 策略

**保留 V2.0 全部前端代码不变**（HTML 页面、Vue 应用、业务逻辑、Excel 解析、规则引擎、UI 样式），**只替换数据层**：将 `Store` 对象中的 IndexedDB CRUD 操作替换为 HTTP REST API 调用（后端 SQLite）。

V2.0 代码位置：`/workspace/attendanceapp/`
V3.1 代码位置：`/workspace/attendance-v3/`

---

## 任务列表

- [x] 1. 构建 Python 后端 -- SQLite 数据库与 REST API
  - [x] 1.1 创建数据库 Schema -- 按照 V2.0 IndexedDB 的 13 张表结构在 SQLite 中建表
    - 表名和字段名与 V2.0 完全一致（camelCase 如 `employeeNo`, `leaveHours`）
    - 13 张表：raw_files, punch_records, leave_records, overtime_records, travel_records, miss_punch_records, schedules, attendance_results, carry_over, holidays, settings, export_templates, employees
    - 实现数据库初始化函数 init_db()，首次运行时建表 + 写入默认 settings + 默认导出模板
    - 参考 V2.0 db.js 的 createDB() 和 startDB() 中的 Schema 定义
  - [x] 1.2 实现 REST API -- 每个 Store 方法对应一个 HTTP 端点
    - GET /api/store/:table → Store.getAll(tableName)
    - GET /api/store/:table?index=field&value=val → Store.getByIndex(tableName, indexName, value)
    - GET /api/store/:table/range?index=field&lower=a&upper=b → Store.getByRange(tableName, indexName, lower, upper)
    - GET /api/store/:table/:key → Store.getByKey(tableName, key)
    - POST /api/store/:table → Store.put(tableName, record)（单条）
    - POST /api/store/:table/bulk → Store.bulkPut(tableName, records)（批量）
    - DELETE /api/store/:table → Store.clearTable(tableName)
    - DELETE /api/store/:table/:key → Store.deleteByKey(tableName, key)
    - POST /api/store/reset → Store.resetAllData()
    - SQLite JSON 字段（workDays, fields, sourcePunchIds 等）存为 TEXT，读写时 json.dumps/json.loads
  - [x] 1.3 实现认证 -- 基于 JWT 的登录/鉴权
    - POST /api/auth/login → 验证用户名密码 → 返回 JWT token
    - 所有 /api/store/* 请求校验 Authorization: Bearer <token>
    - 默认 admin 账号密码与 V2.0 一致
    - token 24 小时有效期，用 HS256 签名
  - [x] 1.4 实现导出服务 -- 复用 V2.0 的 export_server.py
    - POST /api/export/flat → 复用 V2.0 的 export_flat 逻辑
    - POST /api/export/calendar → 复用 V2.0 的 export_calendar 逻辑
    - 将 V2.0 中直接读 IndexedDB 的逻辑改为从请求 body 接收数据
    - 返回 xlsx 二进制文件（Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet）
  - [x] 1.5 为后端 API 编写单元测试
    - 测试认证流程（JWT 生成/校验/过期，登录）
    - 测试每张表的 CRUD 操作
    - 测试批量导入和清空
    - 测试导出接口（含 V3.1.1 日历格子逻辑 12 场景）
    - 注：V3.2 范畴测试（users 表、多角色、review 流程）已按 skip 标注，待 V3.2 实现

- [x] 2. 适配前端 -- 创建 API 版 Store 替换 IndexedDB
  - [x] 2.1 复制 V2.0 全部前端文件到 V3.1 目录
    - 复制所有 HTML（import.html, attendance.html, export.html, settings.html, index.html）
    - 复制所有 shared JS（db.js→重命名 api-store.js, rules.js, excel.js, layout.js, matcher.js, auth.js）
    - 复制所有 CSS（bigsur.css）
    - 复制所有 vendor lib（dexie.min.js→移除, vue.min.js, xlsx.min.js）
  - [x] 2.2 创建 api-store.js -- 替代 db.js 的 Store 对象
    - 保持 Store 的所有方法签名不变（getAll, bulkPut, clearTable, getByIndex, getByRange, getByKey, put, deleteByKey, resetAllData）
    - 每个方法内部改为调用对应的 REST API（使用 fetch）
    - 自动附加 JWT token（从 sessionStorage 读取）
    - 处理 401 响应 → 跳转登录页
    - 保持 _clean() 方法用于 JSON 字段序列化
    - 移除 Dexie 和 IndexedDB 相关代码，移除 DB 对象
  - [x] 2.3 更新页面引用 -- 替换 db.js 为 api-store.js
    - 所有 HTML 页面将 `<script src="shared/db.js">` 改为 `<script src="shared/api-store.js">`
    - 移除 `<script src="shared/dexie.min.js">` 引用
    - 更新 login.html 中的登录逻辑：调用 POST /api/auth/login 替代 localStorage 验证
    - 保持 Auth 对象接口不变，内部的 login() 改为调后端 API
  - [x] 2.4 调整导出逻辑 -- Excel.exportToExcel() 通过后端生成
    - exportToExcel() 中构建请求数据（template, records, filename）
    - POST 到 /api/export/flat，接收 blob 后用 URL.createObjectURL 触发下载
    - exportCalendarReport() 同理调用 /api/export/calendar
    - 保持 Excel._apiExport() 方法签名不变
  - [x] 2.5 为前端适配编写集成测试
    - 测试 Store API 各方法与后端交互正确
    - 测试认证流程前端到后端完整链路
    - 覆盖 getByKey/deleteByKey 各表主键（employees 文本主键、settings key），验证 401 跳转与 JSON 字段序列化

- [x] 3. 验证 -- 确保 V3.1 与 V2.0 业务行为一致
  - [x] 3.1 导入验证 -- 用 V2.0 测试数据完整跑通导入流程
    - 导入 6 个 Excel 文件（打卡/请假/加班/出差/漏打卡/排班）
    - 验证数据条数与 V2.0 一致（punch_records 420 条等）
    - 验证字段值与 V2.0 一致（包括 customNo, travelType, travelers 等）
  - [x] 3.2 计算验证 -- 跑通考勤计算并对比结果
    - 运行 RulesEngine.calculateMonth()
    - 对比 V3.1 和 V2.0 的 attendance_results 条数和状态分布（420 条，suspect_ot 231 / normal 112 / leave 23 / overtime 15 / absent 14 / rest 13 / no_sign_in 6 / no_sign_out 5 / travel 1）
  - [x] 3.3 导出验证 -- 验证导出 Excel 格式正确
    - 平铺导出 → 验证字段完整性
    - 日历导出 → 验证条件格式和颜色
    - V3.1.1 增强：格子逻辑（缺卡→缺勤、出差信息补齐、下午补文字）12 场景测试 + 真实数据验证
  - [x] 3.4 设置页验证 -- 验证配置保存/读取正常
    - 修改考勤规则 → 验证 config_updated_at 更新
    - 添加假期 → 验证 calculateMonth 识别正确（春节假期→rest、调休上班→normal）
    - 暴露并修复：attendance_results 表缺 missTime 列（rules.js 写入报错）→ database.py 加列 + ALTER TABLE 迁移

---

## 补充记录

- 2026-08-10：V3.1.1 日历导出格子规则修复（缺卡统一显示缺勤、出差信息落到缺失卡一侧、请假/缺勤/出差全天下午格子补文字），已实施并验证
- 2026-08-10：V3.1 新增版本显示（登录页 + 侧栏底部，后端 /api/system/version 返回 app_version）
- 测试状态：24 passed / 41 skipped（skipped 为 V3.2 范畴：users 表、多角色、review 流程、rules/holidays handler）
