# fieldMap 模块

**文件**：`attendance-v3/client/src/shared/fieldMap.js` *(v3.3)*

## 职能

OA / 打卡 Excel 表头别名、模糊匹配、本人/帮他人判定、代申请 `subject` 解析。`settings.oa_field_map` 持久化。被 `excel.js`（识别 + 标准化 + 学习）和 `RulesSettingsView.vue`（编辑保存）使用。

## 常量

| 导出 | 值 |
|------|-----|
| `OA_FIELD_MAP_KEY` | `'oa_field_map'` |
| `DEFAULT_TRUE_VALUES` | 本人, 是, Y, YES, TRUE, 是本人 |
| `DEFAULT_FALSE_VALUES` | 非本人, 否, N, NO, FALSE, 帮他人, 代申请, 其它, 其他, 其它人, 其他人, 帮其它人 |
| `DEFAULT_OA_FIELD_MAP` | `selfTrueValues` / `selfFalseValues` + `types.{punch,leave,overtime,travel,miss_punch}` |

打卡默认含 V3.2 精确表头（`考勤号码`/`考勤号`、`签到时间` 等）。OA 四类共用 `OA_SELF_ALIASES` / `OA_APPLICANT_ALIASES`。识别规则 `TYPE_IDENTIFY`、标准化规格 `RECORD_SCHEMA` 与别名同文件；`excel.js` 按配置循环，5 类 Excel 同一套 `pickField`。

## 纯函数

| 函数 | 说明 |
|------|------|
| `normalizeHeader(h)` | 去空白 |
| `compactHeader(h)` | 再去掉「是否为的了吧呢啊_-」 |
| `mergeFieldMap(saved)` | 默认底 + 已存非空数组覆盖 |
| `pickField(clean, aliases)` | `{value, header, fuzzy, score}`；最高分，同分优先非空 |
| `uniquifyHeaders(headerRow)` | 重复表头写成 `申请人#2` |
| `headerBase(h)` | 去掉 `#N` 后缀再打分 |
| `pickApplicantAndOther(clean, applicantAliases, subjectAliases)` | 第 1 个申请人 / 第 2 个申请人或实际人员列 |
| `labelForField(fileType, field)` | 预览/设置页中文名 |
| `headerExists(headers, aliases)` | 任一头得分 >= 40 |
| `isSelfValue(val, trueVals, falseVals)` | true / false / 空串 `null`；含「非本人」优先 false，再「本人」为 true |
| `resolveSubject(isSelfRaw, applicant, otherPerson, ...)` | 本人取第一个申请人；其它取第二个或实际人员 |

打分：精确 100；compact 相等且长度 >= 2 为 80；前后缀包含 60；compact 长度 >= 3 的前后缀包含 40。

## FieldMap 对象

| 方法 | 说明 |
|------|------|
| `getMap()` | `Store.getByKey('settings', 'oa_field_map')`；字符串则 `JSON.parse`；失败回退默认 |
| `saveMap(map)` | `mergeFieldMap` 后 `Store.put` |
| `learnMany(items)` | `{type, field, header}`；未见过的表头 `unshift` 到别名列表；无变更返回 `null` |

依赖 `store.js` → `/api/store/settings`。无独立后端 handler。

## 接入点

- `excel.js` `_getFieldMap()`：命中缓存则直接返回；`learnMany` / 设置页保存后必须把 `Excel._fieldMapCache` 置 `null`
- `excel.js` `_pick`：模糊且 score >= 60 推入 `learned`
- `RulesSettingsView`「OA 字段」Tab：五类型别名 + 本人/帮他人取值

## 测试

`tests/field_map.mjs` + `tests/test_field_map.py`：stub `Store` 后用 Node 跑。覆盖 pickField 精确/模糊、headerExists、isSelfValue、resolveSubject、mergeFieldMap、重复申请人列、preview 中文表头、Matcher 代申请绑号、同名唯一回退、同名多人保持 null、learnMany。

概念说明见 [专有概念/V3.3-导入灵活性.md](../专有概念/V3.3-导入灵活性.md)。
