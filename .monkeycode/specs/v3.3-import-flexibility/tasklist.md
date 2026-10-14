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
