# rules 模块

**文件**：`shared/rules.js`

## RULES_VERSION 常量 (v1.0.26)

`const RULES_VERSION = '1.0.34'`，定义于 rules.js 顶部。版本号随每次规则逻辑变更递增。

**用途**：考勤页 `loadResults()` 读取该版本号，与 `settings` 表中存储的 `rules_version` 比对。若不一致，说明规则代码已更新，将自动触发重新计算而非使用陈旧的缓存结果。

**存储**：计算完成后将 `RULES_VERSION` 写入 `settings` 表的 `rules_version` 键。

## 职能

核心规则引擎，执行考勤计算全流程。暴露 `RulesEngine` 对象。

## API

| 方法 | 入参 | 返回 | 说明 |
|------|------|------|------|
| `getConfig()` | - | 配置对象 | 读取/返回默认考勤配置 |
| `getHolidays()` | - | 假期数组 | 获取全部假期记录 |
| `calculateMonth(targetMonth)` | `"YYYY-MM"` | 结果数组 | 核心计算流程 |
| `getMonthResults(targetMonth)` | `"YYYY-MM"` | 结果数组 | 从 DB 读取已计算的结果 |
| `getResultDetail(eno, date)` | 考勤号, 日期 | 详情对象 | 含关联的 source 记录 |

## 内部方法

### `_timeToMinutes(timeStr)`

将 `HH:MM` 格式转为总分钟数。用于时间差计算。

### `_calcDeviation(signIn, signOut, config)`

计算迟到/早退偏差：
- 签到 > 上班时间 + lateThreshold → 迟到
- 签退 < 下班时间 - earlyThreshold → 早退

**阈值作用**：允许与排班时间有小幅偏差（如 5 分钟内不算迟到）。

### `_isWorkDay(schedulesData, holidaysData, dateStr)`

综合排班表和假期数据判断是否为上班日。

优先级：假期管理 > 排班表 > 默认上班

### `_oaNames(r)` / `_matchOAName(r, employeeName)`

解析 OA 记录的实际人员：`subject`（V3.3 导入层解析的代申请实际人，缺省回退 `applicant`）按 `,，、;；/／` 拆分多姓名；漏打卡记录额外并入 `missPerson`。`_matchOAName` 对姓名去空白后比对。

### `_matchOA(oaRecords, employeeName, dateStr, dateStartField, dateEndField)`

按姓名 + 日期区间过滤 OA 记录（请假/出差）。`startDate` 为空整条不命中。

### `_missCoversPeriod(m, period)` (v1.0.30)

判断漏打卡说明覆盖的时段：

- `missTime` 含「上午/早上/早晨/晨」→ 覆盖 am；含「下午/中午/傍晚/晚」→ 覆盖 pm
- `missTime` 为具体时间（`HH:MM`）→ ≤12:00 覆盖 am，>12:00 覆盖 pm
- `missTime` 为空或无法识别 → 按全天覆盖

### `_leaveHoursForDay(l)` (v1.0.31)

请假记录单日分摊：跨 N 天记录每天计 `total / N`（`total = leaveHours || leaveDays * 8`，保留 2 位小数）；单天记录保持原值。用于 `leaveHours` 累加与调休当日扣减，保证两天合计等于记录总时长、结余扣减不翻倍。

### `calculateMonth(targetMonth)` - 核心流程

1. 读取配置 + 假期数据
2. 查该月所有打卡、请假、出差、漏打卡、加班记录
3. 按员工分组
4. 获取该员工的排班表
5. 按日期 (1日 ~ 月末) 遍历每天：
   - `_isWorkDay()` 判断是否休息日
    - 判断 `status` (normal → rest → leave → travel → normal(漏打卡) → absent → abnormal/early_leave)
   - 计算偏差和加班
   - 产出结果记录 (含 sourcePunchIds 等关联 ID)

  **v1.0.25 修复**：两处关键逻辑增加 `isWorkDay` 条件守卫：
  - `missRecord` 仅在上班日 (`isWorkDay`) 时将状态重置为 `normal`，防止休息日的 `suspect_ot` 被漏打卡记录错误覆盖
   - 迟到判定 (`totalLate > 0`) 仅在上班日 (`isWorkDay`) 时触发 `abnormal`，防止休息日打卡被标记为迟到

   **v1.0.27 修复**：容错豁免逻辑修正。原先将全月所有 `status === 'abnormal'` 的记录无条件重置为 `normal`，导致未打卡导致的 `abnormal` 也被错误豁免。现在使用 `lateDateSet = new Set(lateRecords.map(r => r.date))`，仅对实际出现在 `lateRecords`（迟到日期列表）中的记录执行复位。

    **v1.0.30 修复（V3.3.1，OA 数据与计算联动）**：
    - **漏打卡时段匹配**：半缺勤（有打卡但缺单边）旷工判定按时段细化——缺上午打卡需漏打卡说明覆盖 am（`_missCoversPeriod`），缺下午同理；说明时段对不上仍判 `absent`。完全无打卡 + 任一漏打卡说明 → normal 保持不变。场景：缺上午打卡 + 说明「上午」→ normal；说明「下午」→ absent
    - 说明：历史文档曾描述 v1.0.28 引入 `no_sign_in`/`no_sign_out` 细分状态，git 全历史中 rules.js 从未包含该实现，半缺勤一直判定为 `absent`，特此更正

    **v1.0.34 变更（V3.3.5，请假覆盖语义与加班口径，用户澄清）**：
    - **请假覆盖判定（替换 v1.0.33 的"真实偏差不判定"实现）**：请假分钟 ≥ 迟到分钟（早退同理独立判断）→ 状态保持 `normal`，迟到/早退数值仍显示真实打卡偏差（如 8:30 上班 + 9:51 签到 + 调休 1.5h → 状态「正常」、迟到 1h21m）；请假分钟 < 迟到分钟 → `abnormal`/`early_leave` + 真实数值（无差值冲抵）。全天假（`status = 'leave'`）迟到早退清零保留
    - **加班只认加班申请单**：打卡记录自带的 `punch.overtimeHours` 不再计入（日加班与月度结余 `_updateCarryOver` 的 `monthTotalOvertime` 均只累加 OA 加班单 `overtime_records.overtimeHours`）。无加班单当天加班显示 0h

    **v1.0.33 变更（V3.3.4，迟到早退真实偏差）**：
    - **取消请假分钟抵扣迟到/早退**（撤销 v1.0.30 的抵扣实现）：迟到/早退始终按真实打卡偏差显示。全天假（`status = 'leave'`）迟到早退清零保留。场景：上班 8:30 + 签到 9:51 + 调休 1.5h → 迟到 1h21m（原错误显示 0min）
    - **新增 `early_leave` 状态（早退）**：工作日有真实打卡且 `adjustedEarlyMinutes > 0` 时状态置 `early_leave`（迟到优先，仅 `status === 'normal'` 时触发）。constants.js 四张映射表与导出 `status_labels` 同步新增。场景：签退 16:18（下班 17:30）→ 状态「早退」（原错误显示「正常」）
    - **早退容错豁免**：`earlyRecords` 与迟到对称——月内早退次数 ≤ `graceTimes` 且总分钟 ≤ `graceMinutes` 时 `earlyMinutes` 归零、状态恢复 normal
    - **调休冲抵加班下限钳制**：`adjustedOvertime = Math.max(0, adjustedOvertime - dayHours)`，当日无加班时调休不再产生负数加班（原错误显示 -1.5h）
    - **时长显示格式统一 `formatDuration`**（constants.js）：`<60` 显示 `45m`，`≥60` 显示 `1h21m`（整点 `1h`，0 显示 `0m`）；WebUI 主表/详情/个人考勤/关联打卡记录/日历 tooltip 统一使用
 6. 全月汇总后执行容错豁免（迟到与早退各自独立判断）
7. 更新加班结余 (`_updateCarryOver`)
8. 清空旧结果 → 写入新结果

### `_updateCarryOver(employeeNo, name, targetMonth, monthOvertime, leaveRecords, carryOverList, empCarry)`

更新加班结余。公式：`newBalance = prevBalance + monthOvertime - 调休消耗`。调休消耗按 `_matchOAName(l, name)` 匹配该员工名下所有 `leaveType` 含「调休」的请假记录。`empCarry` 传入该员工已有结余记录，取 `prevMonthKey`（targetMonth - 2 个月）月份的结余为基。

## 关键设计决策

1. **OA 事件不覆盖 isRestDay**：`isRestDay` 仅由 `_isWorkDay()` 设置一次，后续 OA 处理 (leave/travel/miss/absent) 只改 `status`。这保证了排班列的一致性——同一排班休息日对所有员工显示一致。

2. **加班 OA 追加**：`overtime_records` 中的小时数独立追加到当日 `adjustedOvertime`，不依赖打卡数据中是否包含加班。

3. **调休消耗**：请假类型包含"调休"时同时影响当日加班值和月结余。

4. **工作时长计算 (v2.0 新增)**：每人每天根据 `signIn` 和 `signOut` 计算实际工作时长 `workHours`（精确到 0.01 小时），存储于 `attendance_results` 表中。

## 结果对象字段

| 字段 | 类型 | 说明 |
|------|------|------|
| employeeNo | string | 考勤号 |
| name | string | 姓名 |
| department | string | 部门 |
| date | string | 日期 (YYYY-MM-DD) |
| signIn | string | 签到时间 |
| signOut | string | 签退时间 |
| lateMinutes | number | 迟到分钟 |
| earlyMinutes | number | 早退分钟 |
| overtimeHours | number | 加班小时 |
| travelHours | number | 出差小时 |
| leaveHours | number | 请假小时 |
| workHours | number | 实际工作时长 (v2.0) |
| absent | boolean | 是否旷工 |
| status | string | 考勤状态 |
| leaveType | string | 请假类型（多种时去重用「、」拼接，如「公休、调休」） |
| leaveDetails | array (v1.0.32) | 同天多条请假的分行明细 `[{type, hours}]`，hours 为当天分摊值 |
| isRestDay | boolean | 是否休息日 |
| month | string | 月份 |
| sourcePunchIds | array | 关联打卡记录 ID |
| sourceLeaveIds | array | 关联请假记录 ID |
| sourceTravelIds | array | 关联出差记录 ID |
| sourceMissIds | array | 关联漏打卡记录 ID |
| sourceOvertimeIds | array | 关联加班记录 ID (v2.0) |
| missTime | string | 漏打卡说明时段（首条漏打卡记录的 missTime） |
| period | string | 打卡时段（首条打卡记录） |
| scheduleStart / scheduleEnd | string | 上/下班时间（取考勤配置） |

## 结余月份键

使用 `prevMonthKey = targetMonth - 2个月` 而非上个月，因为当前月的结果尚未写入 carry_over 表，需跳过一个月的 gap。
