# 需求实施计划 -- V3.3 导入文件灵活性

- 对应设计: `.monkeycode/specs/v3.3-import-flexibility/design.md`
- 对应需求: `.monkeycode/specs/v3.3-import-flexibility/requirements.md`
- 实施分支: `261008-feat-oa-field-map`
- 勾选以工作区代码核实为准（2026-10-10）

---

## 阶段 A：Field Map 核心

- [x] A1. `client/src/shared/fieldMap.js` [R1, R2, R3, R6]
  - [x] 默认别名覆盖 punch/leave/overtime/travel/miss_punch
  - [x] `mergeFieldMap` / `pickField` / `headerExists` / `isSelfValue` / `resolveSubject`
  - [x] `FieldMap.getMap` / `saveMap` / `learnMany`（settings 键 `oa_field_map`）
  - [x] A1.1 测试：`tests/field_map.mjs` + `tests/test_field_map.py`

## 阶段 B：导入链路接入

- [x] B1. `excel.js` 识别与标准化 [R2, R4]
  - [x] `identifyFileType` 改 `headerExists` + Field Map 别名
  - [x] `_normalizeRecord` 改 `pickField`；OA 四类 `resolveSubject`
  - [x] 模糊命中 score >= 60 调用 `learnMany`
  - [x] 排班路径不读 Field Map
- [x] B2. `matcher.js` 代申请匹配 [R3]
  - [x] 人员优先 `subject`
  - [x] 姓名+部门未命中时，同名仅一人则回退该考勤号

## 阶段 C：设置页

- [x] C1. `RulesSettingsView.vue`「OA 字段」Tab [R1, R5]
  - [x] 视为本人 / 视为帮他人
  - [x] 请假 / 漏打卡 / 加班 / 出差 / 打卡别名编辑
  - [x] 保存后清 `Excel._fieldMapCache`

## 阶段 D：文档与收尾

- [x] D1. 规格：`requirements.md` / `design.md` / `tasklist.md`
- [x] D2. wiki：INDEX、数据文件类型、excel/matcher 模块、ARCHITECTURE、README
- [x] D3. 提交并推送到 `main`（2026-10-14），打 tag `v3.3` 触发 GHCR 镜像构建

## 已知未做

1. 导入预览不展示命中列名（已改为中文列名，仍不展示「命中了 Excel 哪一列」）
2. 无 Field Map 专用 REST，走 store/settings

## 后续修复（V3.3.1，2026-10-15）

V3.3 只改导入层，考勤计算引擎（rules.js）未适配，产生脱节。已补：

- [x] F1. `rules.js` 请假豁免迟到/早退 [迟到 56min + 请假 1h 场景]
  - 短假（leaveDays < 1）有打卡时，迟到分钟数被请假时长（leaveHours*60）抵扣，抵扣后为 0 则状态 normal
  - 全天假（status=leave）迟到早退直接清零
  - abnormal 判定改用抵扣后 adjustedLateMinutes
  - RULES_VERSION 1.0.29 → 1.0.30
- [x] F2. `rules.js` 漏打卡说明按时段匹配
  - 新增 `_missCoversPeriod`：missTime 含上午/下午词或具体时间（12:00 分界）推断覆盖时段；空值按全天
  - 半缺勤（缺签到或签退）旷工判定按时段匹配：缺上午打卡需说明覆盖上午，缺下午同理
  - 完全无打卡 + 任一漏打卡说明 → normal 保持不变
- [x] F3. `tests/calc_flow.mjs` 补场景：短假豁免（代请假 subject 王五）、短假不足抵扣（86-30=56min）、漏打卡上午/下午/具体时间
  - `rowFor` 加 employeeNo 参数（多员工结果行）
