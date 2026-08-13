# V3.2 前端复刻依据 — V3.1 完整功能逻辑

> 用途：V3.2 将 V3.1 静态 HTML 前端重建为 Vite + Vue3 SPA 时的功能基线。本文件逐页、逐模块记录 V3.1 实际行为，复刻时**功能不可丢失**。
>
> 依据代码：`attendance-v3/client/`（6 个 HTML + 7 个 shared JS）。V3.2 决策已确认：**业务表沿用 V3.1 camelCase schema**，**前端新建 Vite SPA**。

---

## 0. 架构总览

```
浏览器（静态 HTML + Vue3 Options API，本地 vue.min.js）
  ├── index.html     登录（唯一可用入口）
  ├── attendance.html 考勤计算（列表/日历双视图 + 详情弹窗）
  ├── import.html    数据导入（拖拽 Excel）
  ├── export.html    导出中心（模板编辑 + 平铺/日历导出）
  └── settings.html  考勤规则 + 假期 + 数据管理
后端（Python http.server + SQLite，端口 8001）
  ├── GET/POST/DELETE /api/store/*    通用 CRUD（Store 接口）
  ├── POST /api/auth/login            登录
  ├── GET  /api/auth/login-check      登录态检查
  ├── GET  /api/system/version        版本
  ├── POST /api/export/flat           平铺导出
  └── POST /api/export/calendar       日历导出
```

- 认证：JWT token 存 `sessionStorage.token`，user 存 `sessionStorage.user`。401 → 清 token 跳 `index.html`。
- 所有页面 `<script>` 顶部 `Auth.requireAuth()`，未登录跳 index.html。
- Vue 组件全部 `Options API`（`data()` + `methods`），`v-cloak` 防闪烁。
- 设计系统 `shared/bigsur.css`（Big Sur 风格：CSS 变量 `--vermillion/--paper/--ink/--card-bg/--border` 等）。

---

## 1. 登录页 index.html（+ login.html）

### 行为
1. DOMContentLoaded：若 `Auth.isLoggedIn()` → 跳 `attendance.html`。
2. 渲染 `/api/system/version` 到 `#login-version`（仅在有 version_name 时显示 "V3.1 考勤管理系统"）。
3. 登录流程 `handleLogin()`：
   - 校验用户名/密码非空。
   - `Auth.login(username, password)`（async，返回 `{success, message}`）。
   - 成功 → `window.location.href = 'attendance.html'`；失败 → 显示 `#login-error`。
   - 登录中按钮禁用 + 文案 "登录中..."。
   - Enter 提交（密码框）、Enter 焦点切换（用户名框）。

### 注意
- `login.html` 是**损坏副本**：`Auth.login()` 未 `await`，`result.success` 恒 undefined → 登录永远失败。**实际入口是 index.html**。V3.2 复刻只需一个登录视图。

### 复刻要求
- 登录成功跳默认页；错误提示内联；加载态按钮；版本号展示。

---

## 2. 考勤计算 attendance.html

### 布局
- 左侧 sidebar（nav 由 layout.js 渲染），顶栏 greeting，主区卡片。
- 卡片 header：视图切换按钮（列表/日历）、"重新计算"按钮（`calculating` 时禁用显示"计算中..."）。

### 数据加载 `created()` → `loadResults()`
1. `currentMonth = detectDataMonth()`：
   - 读全部 `punch_records`，取所有 `date` 的 `YYYY-MM` 前缀排序取最大值；无打卡 → 当前月。
2. `results = RulesEngine.getMonthResults(currentMonth)`（= `Store.getByIndex('attendance_results','month',month)`）。
3. 结果为空但有该月打卡 → 自动 `runCalculation()`。
4. 结果非空时检查规则版本：
   - `config_updated_at` 存在且 `> last_calc_{month}` → `configChanged = true`（顶部红色警告条，可一键重算）。
   - `rules_version` 缺失或 ≠ `RULES_VERSION` → 写入新版本并自动重算。
5. 构建 `scheduleMissing`：该月 `schedules` 表（year==y && month==m）数量为 0 且 results 非空 → 黄色警告（"所有日期默认视为上班日"）。
6. 构建 `holidayMap`（当月 holidays）、`calendarEmployees`（从 results 去重员工）、`departments`（去重部门，排序）。

### 列表视图
- 表格列：考勤号、姓名、部门、日期、排班、签到、签退、迟到(min)、早退(min)、加班(h)、备注、状态。
- 排班列显示：`holidayMap[date].name`（若假期）否则 `r.isRestDay ? '休息' : '上班'`。
- 备注 `remarkText(r)` 拼接规则（按序）：
  1. `leaveType` 存在 → `leaveType + (leaveHours ? leaveHours+'h' : '')`；否则 `sourceLeaveIds.length` → "请假"
  2. `travelHours > 0` 或 `sourceTravelIds.length` → "出差"
  3. `overtimeHours > 0` 且 status ∉ {leave, travel} → "加班{h}h"；否则 status=='overtime' → "疑似加班{h}h"；否则 `sourceOvertimeIds.length` → "有加班"
  4. status=='suspect_ot' → "疑似加班"
  5. `sourceMissIds.length` → "补卡"
  6. `absent` → "缺勤"
  - 用 `/` 连接。
- 状态徽标 `statusBadgeClass` + 文案 `statusLabel`（映射见 §2.7）。
- 行点击 → `showDetail(r)`。
- 空态：`filteredResults.length===0 && !calculating` → "暂无数据，请先导入数据后计算"。
- 筛选：部门下拉、状态下拉、姓名搜索。排序：`employeeNo`（先数字后字符串）→ 部门 → 日期。

### 日历视图
- 员工下拉（`calEmployee`），选择后显示部门；"全部"模式。
- 7 列网格（周一~周日），`buildCalendar()` 生成格子：
  - 月初前填充空 `cal-unknown` 格。
  - 每日判定 `isRest`：先查 `holidayMap`（`h.isWorkday` 为 false 即休息，`holidayName` 显示）；否则查该员工（或全部员工）的排班 `workDays[dayStr] !== true`。
  - 格子状态类 `cal-normal/cal-abnormal/cal-absent/cal-rest/cal-leave/cal-travel/cal-overtime/cal-unknown/cal-holiday`，映射逻辑：normal→cal-normal，rest→cal-rest，abnormal/no_sign_in/no_sign_out→cal-abnormal，leave→cal-leave，travel→cal-travel，absent→cal-absent，overtime→cal-overtime，suspect_ot→cal-unknown；无记录时假期→cal-holiday，休息→cal-rest。
  - 格内容：日期、`signIn/signOut`、休息日标注、假期名（红色）、异常状态文字（`statusColor`）。
- 点击有记录的格子 → `showDetail`。

### 详情弹窗 `showDetail(r)`
- `detail = RulesEngine.getResultDetail(employeeNo, date)`。
- 顶部摘要 grid：考勤号、部门、签到、签退、迟到、早退、加班、出差、请假类型(+小时)、状态徽标、排班。
- 5 个关联表（v-if 非空）：
  - 关联打卡记录：签到/签退/迟到/早退
  - 关联请假记录：类型/开始/结束/天数/小时
  - 关联出差记录：开始/结束/目的地/事由
  - 关联漏打卡说明：日期/说明
  - 关联加班记录：开始/结束/小时/内容
- 关闭：点遮罩（`.self`）或关闭按钮。

### 重新计算 `runCalculation()`
- `calculating=true`，`configChanged=false`。
- `RulesEngine.calculateMonth(month)` → `Store.put('settings', {key:'last_calc_'+month, value:Date.now()})` → 重新 `loadResults()`。
- 错误 → `alert('计算出错: '+err.message)`。

### 复刻要求
- 双视图完整保留；详情弹窗 5 关联表；规则版本/config 变更提示；排班缺失提示；自动计算触发。

---

## 3. 数据导入 import.html

### 文件选择
- 拖拽区（dragover 高亮）+ "选择文件"（`.xlsx,.xls`，multiple）。
- `processFiles`：过滤 `.xlsx?` 扩展名；同名文件跳过（`files` 数组内去重）。
- 每个文件：`Excel.parseExcelFile` → `identifyFileType` → `parseRecords` → 构建 entry `{fileName, fileType, recordCount, records, workbook, imported, error}`。
- `unknown` 类型：读首 sheet 前 5 个表头写入 error 提示。
- 解析失败 → entry 带 `error: '解析失败: ...'`。

### 文件列表
- 每行：文件名、类型徽标（`type-{type}` CSS 类 + `typeLabel`）、解析条数、预览按钮、"已入库"（imported）、错误文本。
- 类型文案：punch 打卡 / leave 请假 / overtime 加班 / travel 出差 / miss_punch 漏打卡 / schedule 排班 / unknown 未知。

### 预览弹窗
- 前 10 条，动态表头（`Object.keys(records[0])`）；超 10 条显示 "仅显示前 10 条，共 N 条"。

### 全部入库 `importAll()`
1. 读 `raw_files` 已有 fileName 集合。
2. 逐文件：同名已导入（`importedNames`）→ 日志 "已存在，跳过"；schedule 类型先缓存最后处理。
3. 各类型写入：
   - punch：`clearTable('punch_records')` + `bulkPut` + `Matcher.syncEmployees()`
   - leave/overtime/travel/miss_punch：`clearTable` + `bulkPut`
   - 每文件成功 → `put('raw_files', {fileName, fileType, importTime: ISO})`；日志 `+N 条`。
   - 失败 → alert + entry.error。
4. schedule 文件（最后）：`syncEmployees()` → 读 `employees` → 每个员工 × 每个排班月生成 `{employeeNo, name, department, year, month, workDays}` 行 → `clearTable('schedules')` + `bulkPut` → raw_files → 日志 "排班展开 N 人 x M 月 = K 条"。
5. 全部导入成功 → alert "所有数据导入完成！可前往考勤计算页面运行计算。"
6. 最后：`put('settings', {key:'config_updated_at', value:Date.now()})`。

### 导入日志
- 时间线（unshift 最新在前）：时间、类型徽标、文件名、结果（`+N 条` 或 提示文本）。

### 复刻要求
- 拖拽 + 选择；同名去重；类型识别徽标；预览前 10 条；导入日志；punch 后自动 syncEmployees；schedule 展开逻辑；导入结束写 config_updated_at。

---

## 4. 导出中心 export.html

### 布局（三列）
- 左：模板列表（`export_templates`，点击选中）+ "另存为模板"。
- 中：模板字段编辑 + 导出设置。
- 右：实时预览（前 5 条）。

### 字段编辑
- `editingFields` 为 `{label, field}` 数组，默认加载选中模板的 `fields`。
- 19 个可选字段（`availableColumns`）：
  `_index`(序号自动) / `employeeNo` / `name` / `department` / `date` / `period` / `scheduleStart` / `scheduleEnd` / `signIn` / `signOut` / `lateMinutes` / `earlyMinutes` / `overtimeHours` / `travelHours` / `absent` / `status` / `leaveType` / `leaveHours` / `workHours`
- 添加字段（默认选第一个）、删除字段、编辑列名/字段映射。
- "另存为模板"：`prompt('请输入模板名称:')` → `put('export_templates', {name, isDefault:0, fields})`。

### 导出设置
- 月份下拉：`availableMonths`（`attendance_results` 去重 month，默认选最大）。
- "导出 Excel"（平铺）`doExport`：
  - 校验 fields 非空；按 exportMonth 取 `getByIndex('attendance_results','month',m)` 或全部。
  - `Excel.exportToExcel(records, {fields:editingFields}, '考勤记录_{month}.xlsx'|'考勤记录_全部.xlsx')`。
- "导出考勤明细"（日历）`doCalendarExport`：需选月份 + fields → `Excel.exportCalendarReport(month, editingFields)`。

### 实时预览
- `updatePreview()`：取全部 `attendance_results` 前 5 条，按 editingFields 渲染；`_index` 显示行号；editingFields deep watch 触发刷新。

### 复刻要求
- 三列布局、模板增改、19 字段、月份筛选、平铺 + 日历两导出、实时预览。

---

## 5. 设置页 settings.html

### 考勤规则配置
- 字段：`workStartTime`(time)、`workEndTime`(time)、`lateThreshold`(number)、`earlyThreshold`(number)。
- 保存 `saveConfig`：`put('settings',{key:'attendance_config',value:{...config}})` + `put('settings',{key:'config_updated_at',value:Date.now()})`。
- 保存后顶部 info 提示 "设置已保存，请前往考勤计算页点击「重新计算」使新规则生效"（4 秒消失）。

### 容错规则配置
- 字段：`graceTimes`（每月豁免次数）、`graceMinutes`（累计豁免时长），同一 config 对象。

### 假期管理
- 表单：开始日期、结束日期（默认=开始）、假期名称、类型（holiday 休息日 / workday 调休上班日）。
- "批量添加" `addHolidays`：校验 start<=end；名称默认（调休上班/假期）；按日展开生成 `{date, name, isWorkday, isHoliday:!isWorkday}` → `bulkPut('holidays', records)` → 写 config_updated_at → 刷新列表 → 清空表单。
- 列表：每行 `date - name + 徽标(上班/休息)` + 删除按钮 → `deleteByKey('holidays', id)` + 写 config_updated_at。

### 数据管理
- "重置数据库" `resetDB`：`confirm` 二次确认 → `Store.resetAllData()` → 清空 holidays 列表，显示"已重置"。

### 复刻要求
- 规则 + 容错同一 config；假期批量展开；重置二次确认；保存均写 config_updated_at。

---

## 6. Store 接口（api-store.js）

```js
const Store = {
  bulkPut(tableName, records)        // POST /api/store/{t}/bulk {records} → {count}
  clearTable(tableName)              // DELETE /api/store/{t}
  getAll(tableName)                  // GET /api/store/{t}
  getByIndex(tableName, indexName, value) // GET /api/store/{t}?index=&value=
  getByRange(tableName, indexName, lower, upper) // GET /api/store/{t}/range?index=&lower=&upper=
  getByKey(tableName, key)           // GET /api/store/{t}/{key}
  put(tableName, record)             // POST /api/store/{t} {record}
  deleteByKey(tableName, key)        // DELETE /api/store/{t}/{key}
  resetAllData()                     // POST /api/store/reset
}
```

- `_request(path, options)`：自动带 `Authorization: Bearer {token}`（从 sessionStorage）；**401 → 清 token/user + 跳 index.html + throw**；非 ok → 读 body.message throw；`body.code !== 0` → throw message；成功返回 `body.data`。
- `_clean(value)`：`JSON.parse(JSON.stringify(value))` 深拷贝。
- **模块加载即执行**：`Store.getByKey('settings','attendance_config')` 若无则写入默认配置 `{workStartTime:'08:30', workEndTime:'17:30', lateThreshold:0, earlyThreshold:0, graceTimes:2, graceMinutes:30}`。

### 复刻要求
- 方法签名必须保持；401 全局跳转；加载时初始化默认配置。

---

## 7. Auth（auth.js）与 layout.js

### Auth
- `isLoggedIn()`：`!!sessionStorage.getItem('token')`
- `login(username, password)`：`POST /api/auth/login`；成功存 token + `user={username}`；返回 `{success:true}` 或 `{success:false, message}`；网络错误 → "网络错误，请检查后端服务"。
- `logout()`：清 token/user → 跳 index.html。
- `requireAuth()`：未登录跳 index.html。

### AppLayout（layout.js）
- `navItems`：import 数据导入 / attendance 考勤计算 / export 导出中心 / settings 系统设置（icon 为 lucide 内联 SVG）。
- `init()`：未登录跳转；渲染侧栏 nav（当前页高亮）；`_updateGreeting()`（按小时上午/下午/晚上好 + `localStorage.attendance_user` 默认"管理员"）；`_updateVersion()`：GET `/api/system/version` 有 `version_name` 则在 footer 追加 "V3.1 考勤管理系统"。
- `toggleMenu/closeMenu`：移动端汉堡菜单。
- `_detectPage()`：按 pathname 含 import/attendance/export/settings 判定。

### 复刻要求
- V3.2 用 Vue Router 替代多页面 + AppSidebar 组件；问候语与版本显示保留；菜单项将按角色分组（employee/deptadmin/hradmin）。

---

## 8. 规则引擎 RulesEngine（rules.js）— 核心逻辑

`RULES_VERSION = '1.0.28'`

### 数据获取
- `getConfig()`：`Store.getByKey('settings','attendance_config')` 有则 `.value`，无则默认 `{workStartTime:'08:30', workEndTime:'17:30', lateThreshold:0, earlyThreshold:0, graceTimes:2, graceMinutes:30}`。
- `getHolidays()`：`Store.getAll('holidays')`。

### 工具函数
- `_trimName(n)`：去空白。
- `_matchOA(oaRecords, employeeName, dateStr, startField, endField)`：按 trim(applicant)==trim(name) 且 `dateStr ∈ [start,end]` 过滤。
- `_timeToMinutes(t)`："HH:MM" → 分钟；空 → null。
- `_calcDeviation(signIn, signOut, config)`：`lateMinutes = signInMin > startMin + lateThreshold`；`earlyMinutes = signOutMin < endMin - earlyThreshold`。
- `_isWorkDay(schedulesData, holidaysData, dateStr)`：
  - holidays 命中：`isWorkday` → true；`isHoliday` → false。
  - 无 schedule → true。
  - 否则 `schedulesData.workDays[dayStr] === true`。

### `calculateMonth(targetMonth)` 完整流程
1. 取 config、holidays；`startDate = {month}-01`，`endDate = {month}-{月末日}`。
2. 拉取当月数据：`punch_records`（getByRange date）、`leave_records`、`travel_records`、`miss_punch_records`（getByRange missDate）、`overtime_records`（startTime 前缀当月）。
3. 按员工分组打卡；每员工取排班（先 `getByIndex('schedules','employeeNo',no)` 找同年同月，无则 `getByIndex('schedules','year',y)` 找同月，均无 → null=全上班日）。
4. 逐日（1..lastDay）：
   - `isWorkDay = _isWorkDay(...)`。
   - 当日打卡聚合：firstSignIn（最小）、lastSignOut（最大）、`totalOvertime`（仅 isWorkDay 时累加 `overtimeHours`）、`totalLate/totalEarly`（_calcDeviation）。
   - `hasRealPunch = !!firstSignIn || !!lastSignOut`。
   - 状态判定（优先级从上到下，后覆盖前）：
     - **非工作日**：`isRestDay=true`；有打卡 → 有加班记录 ? `overtime` : `suspect_ot`；无打卡 → `rest`。
     - 工作日加班记录：`adjustedOvertime` 累加所有当日加班 `overtimeHours`。
     - 请假记录命中：`leaveType=record.leaveType`，`leaveHours += l.leaveHours || l.leaveDays*8`；调休类 `adjustedOvertime -= leaveHours`；**`!hasRealPunch || leaveDays>=1` → status='leave'**。
     - 出差命中：`travelHours=8`；**无打卡 → status='travel'**。
     - 漏打卡命中且 isWorkDay → **status='normal'**（补卡豁免）。
     - **isWorkDay && !hasRealPunch && 无请假/出差/漏卡 → status='absent', absent=true**。
     - **isWorkDay && hasRealPunch && 缺签到或签退 && 无请假/出差/漏卡 → status='absent', absent=true**。
     - `totalLate>0 && hasRealPunch && isWorkDay && status∉{leave,travel,absent}` → `lateRecords.push({date,minutes})`，`status='abnormal'`。
   - `workHours`：firstSignIn/lastSignOut 差值（保留 2 位）。
   - 结果对象字段：`employeeNo/name/department/date/period(取当日首条)/scheduleStart/scheduleEnd(用 config 时间)/signIn/signOut/lateMinutes/earlyMinutes/overtimeHours/travelHours/leaveHours/workHours/absent/status/leaveType/isRestDay/month/sourcePunchIds/sourceLeaveIds/sourceTravelIds/sourceMissIds/sourceOvertimeIds/missTime`。
5. **容错豁免**（每员工月结）：`lateRecords.length <= config.graceTimes && 总迟到分钟 <= config.graceMinutes` → 该员工所有 status='abnormal' 的迟到日 `lateMinutes=0`、`status='normal'`。
6. **结余更新** `_updateCarryOver(employeeNo, name, month, monthOvertime, leaveRecords)`：
   - `adjustmentHours` = 当月调休类请假 leaveHours 之和。
   - `prevMonthKey` = 上月（跨年回退）月份。
   - `carry_over` 读上月末 balance（getByIndex employeeNo），`newBalance = max(0, prevBalance + monthOvertime - adjustmentHours)` → put carry_over。
   - **注意**：`monthOvertime` 传参为每员工当日 overtimeHours 汇总（results 按天叠加），与 adjustedOvertime 独立。
7. 清空 `attendance_results` → `bulkPut(results)` → 返回 results。

### 其他方法
- `getMonthResults(month)`：`getByIndex('attendance_results','month',month)`。
- `getResultDetail(employeeNo, date)`：取结果，按 `source*Ids` 数组逐一 `getByKey` 填充 `sourcePunches/sourceLeaves/sourceTravels/sourceMisses/sourceOvertimes`。

### 状态体系（9 种，V3.1 实际）
| status | 含义 | 徽标类 | 触发 |
|--------|------|--------|------|
| normal | 正常 | badge-normal | 正常/补卡豁免 |
| rest | 休息 | (空) | 非工作日无打卡 |
| abnormal | 迟到/早退 | badge-late | 迟到/早退未豁免 |
| leave | 请假 | badge-leave | 请假命中 |
| travel | 出差 | badge-travel | 出差无打卡 |
| absent | 缺勤 | badge-miss | 工作日无卡/缺单卡 |
| overtime | 疑似加班 | badge-early | 休息日打卡+有加班 |
| suspect_ot | 疑似加班 | badge-nosign | 休息日打卡无加班记录 |
| no_sign_in / no_sign_out | 上班/下班未打卡 | badge-nosign | 单卡缺卡（被 absent 覆盖前理论上不出现） |

`statusLabel` 文案映射：normal正常 / rest休息 / abnormal迟到 / leave请假 / travel出差 / absent缺勤 / overtime疑似加班 / suspect_ot疑似加班 / no_sign_in上班未打卡 / no_sign_out下班未打卡。

### 复刻要求
- 状态判定优先级顺序必须逐条保留；容错豁免逻辑；结余计算；补卡豁免；source*Ids 关联；missTime 字段。

---

## 9. Excel 解析（excel.js）与 Matcher（matcher.js）

### Excel
- `parseExcelFile(file)`：FileReader + `XLSX.read(data,{type:'array',cellStyles:true})`。
- `getSheetNames/sheetToJson(ws,{defval:''})/sheetToArray(ws,{header:1,defval:''})`。
- `_hasFill(cell)`：排班休息日颜色识别（排除白/索引 64/65/theme=1 tint=0）。
- `parseScheduleSheet(ws, sheetName)`：
  - sheet 名必须匹配 `/^(\d{1,2})月$/` → month。
  - 前几行找 `/(\d{4})年/` → year。
  - 找表头行（含"周次/周一/周日"或 `/^周[一二三四五六日]$/`）→ 列映射。
  - 逐行逐日列取 `日期数字`（1-31），有填充色 → 休息日，`workDays[dayStr] = !isRest`。
- `isScheduleWorkbook(wb)`：任一 sheet 名匹配 `^\d{1,2}月$`。
- `parseAllScheduleSheets(wb)`：所有排班 sheet 解析。
- `identifyFileType(wb)`：先排班；否则首行表头打分——`required` 全中 + `bonus` 命中数，分高者胜；unknown 若 bestScore 低。
  - punch：required `[考勤号码, 签到时间]` bonus `[签退时间, 迟到时间, 部门, 日期, 上班时间, 下班时间]`
  - leave：required `[请假类型, 开始日期]` bonus `[结束日期, 请假天数, 申请人, 申请部门]`
  - overtime：required `[加班起止时间]` bonus `[申请人, 申请部门, 加班内容]`
  - travel：required `[出差起止日期]` bonus `[申请人, 目的地, 出差事由, 出差人员]`
  - miss_punch：required `[忘打卡日期]` bonus `[申请人, 忘打卡人员, 未打卡时间, 事由]`
- `parseRecords(wb, fileType)`：schedule 走 parseAllScheduleSheets；其他首 sheet `sheet_to_json` → `_normalizeRecord` 过滤空。
- `_normalizeRecord(row, type)` 字段映射（**表头先去空白键**）：
  - **punch**：employeeNo(考勤号码|考勤号) / customNo(自定义编号) / name(姓名) / date(日期) / period(对应时段) / scheduleStart(上班时间) / scheduleEnd(下班时间) / signIn(签到时间) / signOut(签退时间) / lateMinutes(迟到时间) / earlyMinutes(早退时间) / absent(是否旷工∈[是,True,true,TRUE,1]) / overtimeHours(加班时间) / workHours(工作时间) / department(部门) / isWeekday(平日) / isWeekend(周末) / isHoliday(节假日) / weekdayOT(平日加班) / weekendOT(周末加班) / holidayOT(节假日加班)
  - **leave**：applicant(申请人) / department(申请部门) / leaveType(请假类型) / startDate(开始日期) / endDate(结束日期||开始) / leaveDays(请假天数) / leaveHours(小时) / reason(请假事由)
  - **overtime**：applicant(申请人) / department(申请部门) / startTime(加班起止时间，数字>1当日期否则时间) / endTime('') / overtimeHours(小时) / content(加班内容)
  - **travel**：applicant(申请人) / department(申请部门) / destination(目的地) / travelers(出差人员) / startDate+endDate(出差起止日期按 `[~至到]` 拆分) / travelType(出差类型) / reason(出差事由)
  - **miss_punch**：applicant(申请人) / department(申请部门) / missDate(忘打卡日期) / missPerson(忘打卡人员) / missTime(未打卡时间) / cardTime(当天刷卡时间) / reason(事由)
- `_formatDate(val)`：Excel 序列号（`XLSX.SSF.parse_date_code`）或 `YYYY[-\/.]M[-\/.]D` → `YYYY-MM-DD`。
- `_formatTime(val)`：<1 小数 → 时:分；字符串 `H:MM` → 补零 `HH:MM`。
- 导出（`_apiExport` / `exportToExcel` / `exportCalendarReport`）见 §4：POST blob 下载。
  - `exportToExcel(records, template, filename)`：config 读 attendance_config 的 workStartTime/EndTime → `POST /api/export/flat {records, template, filename, startTime, endTime}`。
  - `exportCalendarReport(targetMonth, fields)`：`getByIndex('attendance_results','month',m)` 空 → throw "没有考勤结果，请先执行计算"；取当月 schedules（getByIndex year）+ holidays（getAll 前缀过滤）+ config 时间 → `POST /api/export/calendar {targetMonth, fields, results, schedules, holidays, startTime, endTime}`，文件 `考勤明细_{month}.xlsx`。

### Matcher
- `buildEmployeeMap()`：从 punch_records 构建 `employeeNo → {name, department}`（仅当两者都非空）。
- `syncEmployees()`：`clearTable('employees')` + `bulkPut(employees)`。
- `resolveEmployeeNo(applicant, department)`：employees 中 `name===applicant && department===department` 匹配。
- `matchOAToPunch(oaRecords, oaType)`：按 `applicant|department` → employeeNo 映射返回匹配数组。

### 复刻要求
- 类型识别规则表逐条保留；排班颜色识别；日期/时间格式化；字段映射（含列名变体）；导出请求体结构。

---

## 10. init.js（兼容桥接层）

- `window.AttendanceDB`：`punches.toArray/bulkPut/clear`、`leaves.toArray` 桥接到 Store。
- `window.AttendanceRules.get/save`：读写 attendance_config（默认值含 `work_hours:8, lunch_start/lunch_end, work_days:[1-5], single_punch_threshold:4`）。
- `window.AttendanceMatcher.match(...)`：旧版匹配（snake_case 字段），V3.2 无需保留（规则引擎已用 rules.js）。

---

## 11. 后端 API 清单（V3.1 已挂载）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | /api/auth/login | 登录（admin/admin123 内联，SHA256） | 无 |
| GET | /api/auth/login-check | 登录态检查 | Bearer |
| GET | /api/system/version | 版本 `{app_version, version_name}` | 无 |
| GET | /api/store/:table | getAll；`?index=&value=` 过滤 | Bearer |
| GET | /api/store/:table/range?index=&lower=&upper= | getByRange | Bearer |
| GET | /api/store/:table/:key | getByKey（主键映射：employees→employeeNo、settings→key、其余 id） | Bearer |
| POST | /api/store/:table | put（body `{record}` 或裸对象） | Bearer |
| POST | /api/store/:table/bulk | bulkPut（body `{records}`） | Bearer |
| DELETE | /api/store/:table | clearTable | Bearer |
| DELETE | /api/store/:table/:key | deleteByKey | Bearer |
| POST | /api/store/reset | 清全部业务表 + 重灌默认 settings | Bearer |
| POST | /api/export/flat | 平铺导出（xlsx blob） | Bearer |
| POST | /api/export/calendar | 日历导出（xlsx blob） | Bearer |

- 静态文件：非 /api 路径从 `client/` 目录托管；缺失文件 302 → /index.html。
- JSON 响应格式：`{code:0, data}` 成功；`{code:1, message}` 失败；`_send_json` code≥400 时用 HTTP 对应状态码，否则 400。

---

## 12. 数据库 Schema（V3.1，camelCase，13 表）

| 表 | 主键 | 关键字段 |
|----|------|---------|
| raw_files | id | fileName, fileType, recordCount, importTime |
| punch_records | id | employeeNo, customNo, name, date, period, scheduleStart, scheduleEnd, signIn, signOut, lateMinutes, earlyMinutes, absent, overtimeHours, workHours, department, isWeekday, isWeekend, isHoliday, weekdayOT, weekendOT, holidayOT |
| leave_records | id | applicant, department, leaveType, startDate, endDate, leaveDays, leaveHours, reason |
| overtime_records | id | applicant, department, startTime, endTime, overtimeHours, content |
| travel_records | id | applicant, department, destination, travelers, startDate, endDate, travelType, reason |
| miss_punch_records | id | applicant, department, missDate, missPerson, missTime, cardTime, reason |
| schedules | id | employeeNo, name, department, year, month, workDays(JSON `{dd:bool}`) |
| attendance_results | id | employeeNo, name, department, date, period, scheduleStart, scheduleEnd, signIn, signOut, lateMinutes, earlyMinutes, overtimeHours, travelHours, leaveHours, workHours, absent, status, leaveType, isRestDay, month, sourcePunchIds/LeaveIds/TravelIds/MissIds/OvertimeIds(JSON 数组), missTime |
| carry_over | id | employeeNo, name, month, overtimeBalance |
| holidays | id | date, name, isWorkday, isHoliday |
| settings | key | value(JSON) |
| export_templates | id | name, isDefault, fields(JSON) |
| employees | employeeNo | name, department |

JSON 字段序列化：workDays/fields/source*Ids/value 由后端 `json_serialize` 读写时 dump/load；布尔字段（isWorkday/isHoliday/isDefault/absent/isRestDay）读写转 0/1。

---

## 13. 已知缺陷 / 边界行为（V3.2 需注意）

1. `login.html` 未 await `Auth.login()`，登录失效——V3.2 只做单登录视图。
2. 后端当前登录为**内联 admin 硬编码**（SHA256 admin/admin123），非 handlers/auth.py（后者依赖缺失的 users 表）。
3. `attendance_results.missTime` 为 V3.2 已补列；export.py 漏打卡识别依赖它。
4. Store.put/bulkPut 对 `settings` 特殊处理（key/value 直写）；其他表 `id` 存在则 UPDATE 否则 INSERT（bulk 一律 INSERT，pop id）。
5. `schedules` 无员工记录时默认全上班日（calculateMonth 中 schedulesData=null → _isWorkDay 返回 true）。
6. `holidayMap`/日历排班依赖 `workDays[dayStr] !== true` 判休息——排班未导入时全上班。
7. 导出 `exportCalendarReport` 无结果时 throw；前端 alert。
8. `config_updated_at` 每次保存/假期变更/导入后都会更新，驱动考勤页"规则已变更"提示。
