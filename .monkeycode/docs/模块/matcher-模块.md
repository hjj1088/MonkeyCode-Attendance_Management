# matcher 模块

**文件**：`shared/matcher.js`

## 职能

跨表数据匹配，建立员工标识（考勤号、姓名、部门）之间的映射关系。

## API

### `buildEmployeeMap()`

从打卡记录构建 `{ 考勤号 → { name, department } }` 映射。

```js
// 返回：
{ "75": { name: "梁XX", department: "市场营销部" }, ... }
```

以考勤号为主键，同号取首次出现的姓名和部门。

### `syncEmployees()`

将员工映射写入 `employees` 表。先清空后插入全量。

在打卡数据导入后自动调用，确保员工表始终与打卡数据同步。

### `resolveEmployeeNo(applicant, department)`

通过姓名 + 部门反查考勤号。

```js
// 返回考勤号字符串，或 null
Matcher.resolveEmployeeNo("梁XX", "市场营销部")  // → "75"
```

### `matchOAToPunch(oaRecords, oaType)`

将 OA 记录（请假/加班/出差/漏打卡）匹配到考勤号。

```js
// 返回：
[{ index: 0, employeeNo: "75", applicant: "梁XX", department: "市场营销部" }, ...]
```

匹配逻辑：`applicant|department` 组合键 → 查 `buildEmployeeMap()` 的 `name|department` 反向映射。

## 匹配策略

两步匹配策略：
1. **考勤号匹配**：按 `employeeNo` 直接关联（精确）
2. **姓名+部门匹配**：按 `name + department` 降级关联（当 OA 文件无考勤号时）

员工列表以打卡数据为权威来源，打卡导入后同步。

## 注意事项

- `buildEmployeeMap()` 每次从 `punch_records` 全量读取，不缓存
- `resolveEmployeeNo` 依赖 `employees` 表已同步，当 `employees` 表为空时返回 null
- 姓名重复但不同部门视为不同员工
