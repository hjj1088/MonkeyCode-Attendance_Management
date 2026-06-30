# rules 模块

**文件**：`shared/rules.js`

## RULES_VERSION 常量 (v1.0.26)

`const RULES_VERSION = '1.0.28'`，定义于 rules.js 顶部。版本号随每次规则逻辑变更递增。

**用途**：`attendance.html` 的 `loadResults()` 读取该版本号，与 `settings` 表中存储的 `rules_version` 比对。若不一致，说明规则代码已更新，将自动触发重新计算而非使用陈旧的缓存结果。

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

### `calculateMonth(targetMonth)` - 核心流程

1. 读取配置 + 假期数据
2. 查该月所有打卡、请假、出差、漏打卡、加班记录
3. 按员工分组
4. 获取该员工的排班表
5. 按日期 (1日 ~ 月末) 遍历每天：
   - `_isWorkDay()` 判断是否休息日
   - 判断 `status` (normal → rest → leave → travel → normal(漏打卡) → absent → no_sign_in/no_sign_out → abnormal)
   - 计算偏差和加班
   - 产出结果记录 (含 sourcePunchIds 等关联 ID)

  **v1.0.25 修复**：两处关键逻辑增加 `isWorkDay` 条件守卫：
  - `missRecord` 仅在上班日 (`isWorkDay`) 时将状态重置为 `normal`，防止休息日的 `suspect_ot` 被漏打卡记录错误覆盖
   - 迟到判定 (`totalLate > 0`) 仅在上班日 (`isWorkDay`) 时触发 `abnormal`，防止休息日打卡被标记为迟到

   **v1.0.27 修复**：容错豁免逻辑修正。原先将全月所有 `status === 'abnormal'` 的记录无条件重置为 `normal`，导致未打卡导致的 `abnormal` 也被错误豁免。现在使用 `lateDateSet = new Set(lateRecords.map(r => r.date))`，仅对实际出现在 `lateRecords`（迟到日期列表）中的记录执行复位。

   **v1.0.28 修复**：未打卡状态细分与迟到拦截增强。
   - 新增 `no_sign_in`（上班未打卡，有签退无签到）和 `no_sign_out`（下班未打卡，有签到无签退）两种细分状态
   - 判断时机位于 absent 检查之后、迟到检查之前（第 5 步内部）
   - 迟到判定增加守卫条件 `status !== 'no_sign_in' && status !== 'no_sign_out'`，防止未打卡状态被迟到 (`abnormal`) 覆盖
6. 全月汇总后执行容错豁免
7. 更新加班结余 (`_updateCarryOver`)
8. 清空旧结果 → 写入新结果

### `_updateCarryOver(employeeNo, name, targetMonth, monthOvertime, leaveRecords)`

更新加班结余。公式：`newBalance = prevBalance + monthOvertime - 调休消耗`。

## 关键设计决策

1. **OA 事件不覆盖 isRestDay**：`isRestDay` 仅由 `_isWorkDay()` 设置一次，后续 OA 处理 (leave/travel/miss/absent) 只改 `status`。这保证了排班列的一致性——同一排班休息日对所有员工显示一致。

2. **加班 OA 追加**：`overtime_records` 中的小时数独立追加到当日 `adjustedOvertime`，不依赖打卡数据中是否包含加班。

3. **调休消耗**：请假类型包含"调休"时同时影响当日加班值和月结余。

4. **结余月份键**：使用 `prevMonthKey = targetMonth - 2个月` 而非上个月，因为当前月的结果尚未写入 carry_over 表，需跳过一个月的 gap。
