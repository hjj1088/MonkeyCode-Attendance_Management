# Requirements Document -- V3.3 导入文件灵活性

- 版本: v3.3.0
- 日期: 2026-10-10
- 状态: 实施中（分支 `261008-feat-oa-field-map`）
- 对应设计: `.monkeycode/specs/v3.3-import-flexibility/design.md`
- 对应任务: `.monkeycode/specs/v3.3-import-flexibility/tasklist.md`

---

## Introduction

V3.1/V3.2 导入识别与字段标准化依赖**精确表头字符串**（去空白后 `headers.includes('请假类型')`）。OA 导出改列名（`是否为本人`、`请假人`、`漏打卡日期`）或代他人申请时，类型识别失败或 `subject` 落到申请人，考勤计算错绑员工。

V3.3 在现有 6 类导入（打卡/请假/加班/出差/漏打卡/排班）上增加 **OA 字段映射**：可配置别名、模糊表头匹配、导入时自动学习相近列名、代申请按「是否本人 + 实际人员」解析 `subject`。排班仍按 Sheet 名识别，不进字段映射。

当前实现位于分支 `261008-feat-oa-field-map`，工作区未提交。本规格按该分支代码核实。

---

## Glossary

- **OA 字段映射 (Field Map)**：`settings.oa_field_map` 中保存的别名表，按文件类型列出内部字段对应的表头别名，以及「视为本人 / 视为帮他人」取值
- **内部字段**：标准化记录键，如 `leaveType`、`subjectPerson`、`missDate`
- **别名 (alias)**：Excel 表头字符串，去空白后参与匹配，如 `请假类型`、`假别`
- **精确匹配**：去空白后表头与别名完全相等，得分 100
- **模糊匹配**：去语气助词后相等（得分 80）或前后缀包含（得分 60/40）；`headerExists` 阈值 40，学习阈值 60
- **主体 (subject)**：OA 记录真正作用的员工姓名；本人申请取申请人，代申请取「请假人员 / 忘打卡人员」等
- **代申请**：`isSelf` 判定为非本人时，用 `subjectPerson`（或出差 `travelers`）作为 `subject`
- **自动学习**：模糊命中且得分 >= 60 时，把实际表头写入对应字段别名列表头部并落库
- **排班 (schedule)**：仍按 Sheet 名 `^\d{1,2}月$` 识别，不走 Field Map

---

## Requirements

### Requirement 1: 可配置字段别名

**User Story:** AS 人事管理员，I want 为 OA 表头配置多个别名，so that 列名改版后仍能识别文件并标准化字段。

#### Acceptance Criteria

1. 系统 SHALL 在 `settings` 表以键 `oa_field_map` 持久化字段映射
2. WHEN 映射缺失或损坏，系统 SHALL 使用内置默认别名完成识别与标准化
3. 默认映射 SHALL 覆盖类型 `punch`、`leave`、`overtime`、`travel`、`miss_punch` 的内部字段，每个字段至少含 V3.2 原精确表头
4. WHEN 人事管理员在规则设置页「OA 字段」Tab 保存，系统 SHALL 把各字段别名（逗号/顿号/分号分隔）与「视为本人 / 视为帮他人」取值写入 `oa_field_map`
5. WHEN 保存后再次打开该 Tab，系统 SHALL 展示已保存别名与取值

---

### Requirement 2: 表头模糊识别与标准化

**User Story:** AS 人事管理员，I want 导入时按别名模糊匹配表头，so that `是否为本人`、`请假人` 这类近义列名无需先改 Excel。

#### Acceptance Criteria

1. WHEN `identifyFileType` 判定非排班文件，系统 SHALL 用当前 Field Map 的别名列表做必含/加分匹配（`headerExists`，得分 >= 40 视为命中）
2. WHEN 必含别名全部命中（加班可用起止时间列作为替代必含），系统 SHALL 将该类型视为候选并按必含数 + 加分命中数计分，取最高分类型
3. WHEN `parseRecords` 标准化一行，系统 SHALL 按 Field Map 别名 `pickField` 取值：精确优先；同分时优先非空单元格
4. `pickField` SHALL 对去空白后完全相等的表头给 100 分；去「是否为的了吧呢啊_-」后长度 >= 2 且相等给 80 分；前后缀包含给 60 分；压缩后长度 >= 3 的前后缀包含给 40 分
5. 排班工作簿识别与解析 SHALL 保持 V3.2 行为，不读取 Field Map

---

### Requirement 3: 代申请主体解析

**User Story:** AS 人事管理员，I want 代他人提交的请假/漏打卡/加班/出差落到实际员工，so that 考勤计算绑对人。

#### Acceptance Criteria

1. 系统 SHALL 用可配置的「视为本人」与「视为帮他人」列表解析 `isSelf` 单元格（去空白、大小写不敏感）
  2. WHEN `isSelf` 判定为本人，系统 SHALL 将 `subject` 设为申请人姓名（重复「申请人」列时取从左到右第 1 列）
  3. WHEN `isSelf` 判定为帮他人、「其它」或为空，系统 SHALL 将 `subject` 设为实际人员字段；实际人员为空时回退申请人
  4. 请假/加班的实际人员字段 SHALL 为 `subjectPerson`；出差 SHALL 优先 `travelers` 再 `subjectPerson`；漏打卡 SHALL 为 `subjectPerson`（写入 `missPerson` 与 `subject`）
  5. WHEN Excel 含两列同名「申请人」，系统 SHALL 将第 1 列映射为 `applicant`、第 2 列映射为实际人员；本人看第 1 列，其它看第 2 列
  6. WHEN OA 记录匹配考勤号，系统 SHALL 先按 `subject|department` 精确匹配员工；同名仅一人时按姓名唯一回退

---

### Requirement 4: 导入自动学习

**User Story:** AS 人事管理员，I want 相近列名在成功导入后自动记入别名，so that 下次无需手工补映射。

#### Acceptance Criteria

1. WHEN 标准化过程中模糊命中且得分 >= 60，系统 SHALL 收集 `{type, field, header}`
2. WHEN 一批记录解析结束且收集非空，系统 SHALL 把新表头插入对应别名列表头部并写回 `oa_field_map`
3. IF 学习写入失败，系统 SHALL 仍返回已解析记录，导入流程继续
4. 精确匹配（得分 100）SHALL 不触发学习

---

### Requirement 5: 规则设置入口

**User Story:** AS 人事管理员，I want 在规则设置里维护 OA 字段映射，so that 表头改名后可手工补别名。

#### Acceptance Criteria

1. `RulesSettingsView` SHALL 增加「OA 字段」Tab，与考勤时段 / 容错规则 / 假期管理并列
2. 该 Tab SHALL 提供请假 / 漏打卡 / 加班 / 出差 / 打卡五个子类型切换，均可编辑别名
3. 每个内部字段 SHALL 用单行输入展示别名，占位符为该字段中文名
  4. WHEN 点击「保存映射」，系统 SHALL 持久化当前草稿并清除 Excel 侧 Field Map 缓存
  5. WHEN 导入预览展示标准化记录，系统 SHALL 用中文列名（`FIELD_LABELS` / `PREVIEW_LABELS`），例如 `applicant` 显示为「申请人」、`subject` 显示为「实际人员」

---

### Requirement 6: 解析器与往返

**User Story:** AS 系统，I want Field Map 的读出、合并、序列化可往返，so that 设置页与导入使用同一套别名。

#### Acceptance Criteria

1. 系统 SHALL 提供 `mergeFieldMap(saved)`：以默认映射为底，用已存 `selfTrueValues` / `selfFalseValues` / `types[type][field]` 覆盖非空数组
2. 系统 SHALL 提供 `pickField` / `headerExists` / `isSelfValue` / `resolveSubject` 纯函数，输入去空白表头与别名，输出取值或布尔
3. WHEN `FieldMap.getMap` 读到字符串 `value`，系统 SHALL JSON 解析后再合并；解析失败则回退默认映射
4. `FieldMap.saveMap` 写入的对象经 `getMap` 再读出后，用户配置的非空别名 SHALL 仍在对应字段列表中（与默认别名并存或覆盖，以 merge 规则为准）

---

## Out of Scope

- 排班表表头映射与颜色规则变更
- 后端新建 Field Map 专用 API（沿用 `/api/store/settings`）
- 导入预览 UI 展示「命中了哪列表头」
- 多语言表头（英文列名作为默认别名）
- 修改考勤规则引擎判定优先级
