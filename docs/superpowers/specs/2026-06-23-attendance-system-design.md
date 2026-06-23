# 考勤管理系统 -- 技术设计文档

- 版本: v1.0.0 (Phase 1 MVP)
- 架构: 纯前端 SPA (多 HTML) + IndexedDB (Dexie.js) + 本地静态文件
- 日期: 2026-06-23

---

## 1. 项目结构

```
attendance/
├── index.html              # 登录页 + 主导航
├── import.html             # 数据导入
├── attendance.html         # 考勤计算与查看 (列表+日历)
├── export.html             # 导出中心 + 模板设计器
├── settings.html           # 系统设置
├── lib/
│   ├── vue.global.prod.js  # Vue 3 CDN 本地化
│   ├── dexie.min.js        # Dexie.js IndexedDB 封装
│   └── xlsx.full.min.js    # SheetJS Excel 读写
├── shared/
│   ├── db.js               # 数据库 Schema + CRUD
│   ├── auth.js             # 登录状态管理
│   ├── rules.js            # 考勤规则引擎
│   ├── excel.js            # SheetJS 封装 + 排班表颜色解析
│   └── matcher.js          # 跨文件数据匹配 (考勤号/姓名+部门)
```

所有模块通过 `<script src="./shared/xxx.js">` 加载共享逻辑，通过 `<script src="./lib/xxx.js">` 加载第三方库。无构建工具，浏览器直接打开 `index.html`。

---

## 2. 共享基础设施

### 2.1 认证 (auth.js)

- 前端形式验证，默认账号 `admin` / `admin123`
- 登录状态存入 `localStorage` (`attendance_auth` key)
- 每个 HTML 页面加载时检查登录状态，未登录跳转 `index.html`
- Phase 1 仅超级管理员角色，无权限隔离

### 2.2 数据库 Schema (db.js)

基于 Dexie.js 定义 IndexedDB 数据库 `AttendanceDB`，包含以下表：

| 表名 | 用途 | 主键 | 核心字段 |
|------|------|------|----------|
| `raw_files` | 原始导入文件元信息 | `++id` | fileName, fileType (punch/leave/overtime/travel/miss_punch/schedule), importTime |
| `punch_records` | 打卡记录 | `++id` | employeeNo (考勤号), customNo, name, date, period, scheduleStart, scheduleEnd, signIn, signOut, lateMinutes, earlyMinutes, absent, overtimeHours, workHours, department, isWeekday, isWeekend, isHoliday, weekdayOT, weekendOT, holidayOT, rawFileId |
| `leave_records` | 请假记录 | `++id` | applicant, department, leaveType, startDate, endDate, leaveDays, leaveHours, reason, rawFileId |
| `overtime_records` | 加班记录 | `++id` | applicant, department, startTime, endTime, overtimeHours, content, rawFileId |
| `travel_records` | 出差记录 | `++id` | applicant, department, destination, travelers, startDate, endDate, travelType, reason, rawFileId |
| `miss_punch_records` | 漏打卡说明 | `++id` | applicant, department, missDate, missPerson, missTime, cardTime, reason, rawFileId |
| `schedules` | 排班数据 | `++id` | employeeNo/name, year, month, workDays (JSON: {date: boolean}), rawFileId |
| `attendance_results` | 计算结果 | `[employeeNo, date]` | employeeNo, name, department, date, period, scheduleStart, scheduleEnd, signIn, signOut, lateMinutes, earlyMinutes, overtimeHours, travelHours, absent, status (normal/abnormal/absent), leaveType, sourceRecords (关联原始记录ID), carryOverOvertime, adjustedOvertime, month |
| `carry_over` | 结余数据 | `[employeeNo, month]` | employeeNo, name, overtimeBalance, leaveBalance, month |
| `holidays` | 公司假期/调休 | `++id` | date, name, isWorkday (调休上班日), isHoliday (休息日) |
| `settings` | 系统配置 | `key` | key, value (JSON) |
| `export_templates` | 导出模板 | `++id` | name, isDefault, fields (JSON: [{label, field, width}]) |
| `employees` | 员工花名册(自动聚合) | `employeeNo` | employeeNo, name, department |

> `employees` 表在导入打卡数据时自动更新: 从 punch_records 中提取 `(employeeNo, name, department)` 去重后写入。

### 2.3 SheetJS 封装 (excel.js)

- `parseExcelFile(file)` — FileReader 读取 ArrayBuffer 后调用 `XLSX.read()`，返回 workbook 对象
- `parseScheduleSheet(ws, sheetName)` — 日历样式排班表解析:
  1. 从 Sheet 名 (如 "12月") 提取月份; 从首行标题 (如 "2026年12月日历表") 提取年份
  2. 定位行头 "周次|周一|周二|周三|周四|周五|周六|周日"
  3. 遍历数据行，从行头提取"第N周"，从对应日期单元格读取日期数值
  4. 对每个日期单元格: 读取 `cell.s` (样式) → 有 `fill.fgColor` 且非默认白色 → 休息，否则 → 上班
  5. 返回 `{year, month, workDays: {"1": true, "2": false, ...}}`
- `getWorkbookSheets(wb)` — 获取所有 Sheet 名，匹配 "1月"-"12月" (trim 后) 的为排班表 Sheet
- `recordsToExcel(records, template)` — 根据模板定义将数据数组导出为 Excel 文件
- `exportExcel(records, template, filename)` — 生成 Blob 并触发浏览器下载

### 2.4 数据匹配器 (matcher.js)

- `matchByEmployeeNo(sourceRecords, targetRecords)` — 以考勤号为 key 匹配
- `matchByApplicantName(sourceRecords, targetRecords, employeeMap)` — OA 单据用"申请人+部门"匹配打卡数据中的"姓名+部门"
- `buildEmployeeMap()` — 从打卡记录构建 `{employeeNo: {name, department}}` 映射表
- `resolveEmployeeNo(applicant, department, employeeMap)` — 尝试解析 OA 单据的考勤号

---

## 3. 各模块详细设计

### 3.1 index.html (登录 + 导航)

**UI 结构**: 登录表单 (账号/密码/登录按钮)，登录后显示 4 个模块入口卡片。

**流程**:
1. 检查 `auth.isLoggedIn()` → 已登录则跳过登录直接显示导航
2. 输入 admin/admin123 → 验证通过 → 保存状态 → 显示导航
3. 导航卡片: 数据导入 / 考勤计算 / 导出中心 / 系统设置，点击跳转对应 HTML

### 3.2 import.html (数据导入)

**UI 结构**: 拖拽区域 + 已导入文件列表 + 识别结果预览表 + 确认入库按钮

**流程**:
1. 拖拽/选择多个 Excel 文件
2. 逐个文件调用 `excel.parseExcelFile()` 解析
3. 自动识别 (基于表头关键词匹配):

| 文件类型 | 识别关键词 (列名匹配) |
|----------|----------------------|
| 打卡 | "考勤号码" + "签到时间" |
| 请假 | "请假类型" + "开始日期" |
| 加班 | "加班起止时间" |
| 出差 | "出差起止日期" |
| 漏打卡 | "忘打卡日期" |
| 排班 | Sheet 名匹配 "1月"-"12月" 且为日历样式 |

4. 识别结果预览 (每种类型一个表格 tab)
5. 确认入库 → 数据写入 IndexedDB 对应表，同时记录 `raw_files`
6. 入库完成后提示"计算考勤"，可跳转到 `attendance.html`

**重导入策略**: 重新导入同类型数据时，先清空该类型旧数据再写入 (保证数据一致性)。

### 3.3 attendance.html (考勤计算与查看)

**UI 结构**: 顶部筛选栏 (部门/人员/月份/状态) + 视图切换 (列表/日历) + 计算结果表格

**列表视图**:
- 排序: 考勤号 → 部门 → 日期 (补零排序)
- 筛选: 按部门、人员、月份、状态 (正常/异常/缺勤)
- 点击行 → 弹出详情面板，显示关联原始打卡记录和 OA 单据
- 颜色: 绿(正常)/黄(异常)/红(缺勤)

**日历视图**:
- 按月展示，日期格内显示签到/签退时间
- 颜色标识: 绿(正常)/黄(异常)/红(缺勤)/灰(休息日)
- 点击日期格 → 显示当天详情

**规则引擎 (rules.js) 核心逻辑**:

```
输入: 某人员某月
  1. 加载该人员的排班数据 → 确定本月每天是否应出勤
  2. 加载公司假期/调休 → 覆盖排班 (调休上班日覆盖休息日)
  3. 遍历应出勤日期:
     a. 读取当天打卡记录 → 计算迟到/早退/漏打卡
     b. 应用容错规则 → 月累计2次且≤30min迟到豁免
     c. 读取请假记录 → 全天请假 → 当天标记为请假(非旷工)
     d. 读取出差记录 → 当天标记为出差
     e. 读取漏打卡说明 → 清除漏打卡异常标记
     f. 汇总当天加班时长
  4. 加载上上个月结余数据 → 计算当月加班余额
      overtimeBalance = 上上个月余额 + 当月加班 - 当月调休(请假类型=调休)
  5. 保存计算结果到 attendance_results
  6. 保存结余到 carry_over
```

**容错规则**:
- 每月迟到 ≤ 2 次 **且** 累计迟到时长 ≤ 30 分钟 → 不计为迟到
- 超出任一条件 → 按正常迟到计算

**结余计算**:
- 当月结余 = 上上个月结余 + 当月加班累计 - 当月调休时长 (请假类型=调休的请假时长)
- 注意"上上个月": 计算 6 月时取 4 月 carry_over 记录

**异常判定**:
- 漏打卡: 应出勤日无签到/签退记录且无请假/出差/漏打卡说明
- 迟到: 签到时间 > 上班基准时间 (8:30) 且超出容错
- 早退: 签退时间 < 下班基准时间 (17:30)
- 旷工: 应出勤日无任何记录 (无打卡、无请假、无出差)

### 3.4 export.html (导出中心 + 模板设计器)

**UI 结构**: 左侧模板列表 + 中间模板编辑器 + 右侧实时预览

**默认模板字段**:

| 序号 | 字段名 | 数据源字段 |
|------|--------|-----------|
| 1 | 序号 | (自动编号) |
| 2 | 考勤号码 | employeeNo |
| 3 | 姓名 | name |
| 4 | 部门 | department |
| 5 | 日期 | date |
| 6 | 对应时段 | period |
| 7 | 上班时间 | scheduleStart |
| 8 | 下班时间 | scheduleEnd |
| 9 | 签到时间 | signIn |
| 10 | 签退时间 | signOut |
| 11 | 迟到时间 | lateMinutes |
| 12 | 早退时间 | earlyMinutes |
| 13 | 加班时间 | overtimeHours |
| 14 | 出差时间 | travelHours |
| 15 | 是否旷工 | absent |

**模板操作**:
- 编辑字段 → 增删改字段、调整顺序、修改列名
- 实时预览 → 取当月前 5 条数据展示预览表
- 另存为 → 基于当前模板创建副本
- 导出 → 根据选中模板、选中月份/部门生成 Excel 并下载

### 3.5 settings.html (系统设置)

**考勤规则配置**:
- 上班基准时间 (默认 8:30)
- 下班基准时间 (默认 17:30)
- 迟到阈值 (分钟)
- 早退阈值 (分钟)
- 容错: 每月豁免次数 (默认 2)
- 容错: 累计豁免时长 (默认 30 分钟)

**假期管理**:
- 日期选择器添加公司假期 (节假日/调休)
- 调休上班日 (周末但需上班的日期)
- 已添加假期列表，支持删除

---

## 4. 数据流

```
[Excel文件拖拽] → import.html
  → excel.js 解析 → 自动识别类型
  → 写入 IndexedDB (punch/leave/overtime/travel/miss_punch/schedules)
  → attendance.html 触发计算
  → rules.js 读取排班+打卡+OA+假期+上月结余
  → 逐人逐日计算 → 存入 attendance_results + carry_over
  → 列表/日历视图展示
  → export.html 读取 attendance_results
  → 按模板导出 Excel
```

---

## 5. 实施顺序

| 阶段 | 模块 | 依赖 |
|------|------|------|
| S1 | lib/ 依赖下载 + shared/ 全部共享模块 | 无 |
| S2 | index.html (登录+导航骨架) | S1 |
| S3 | settings.html | S1 |
| S4 | import.html (含自动识别) | S1 |
| S5 | attendance.html (规则引擎+视图) | S1, S4 |
| S6 | export.html (模板+导出) | S1, S5 |

每个阶段完成后可独立验证，后一阶段依赖前一阶段的共享模块但不受 HTML 页面影响。

---

## 6. 技术约束

- Vue 3 CDN 模式，使用 Options API (兼容性好，无需编译)
- 所有第三方库本地化存储于 `lib/`，不依赖外部 CDN
- TailwindCSS 通过 CDN 引入 (浏览器本地缓存)，也可以后续考虑本地化
- IndexedDB 数据不清除则持久保留，支持跨月计算
- 浏览器需支持 IndexedDB、FileReader API (Chrome/Firefox/Edge 现代版本)

## 7. 版本管理 (缓存更新)

- 所有 `<script src>` 和 `<link href>` 引用统一附加 `?v=1.0.0` 查询参数防浏览器缓存
- 每次发布时递增版本号，确保用户加载最新文件
- `shared/` 模块加载顺序: `lib/*` → `shared/auth.js` → `shared/db.js` → `shared/excel.js` → `shared/matcher.js` → `shared/rules.js`
