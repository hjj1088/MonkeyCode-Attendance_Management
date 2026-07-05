# init 模块 (v2.0 新增)

**文件**：`shared/init.js`

## 职能

向后兼容桥接层。将 v2.0 的模块命名体系映射到 v1.0 的旧版 API，确保引用旧命名的代码仍然可运行。

## 导出

挂载到 `window` 的三个对象：
- `window.AttendanceDB`
- `window.AttendanceRules`
- `window.AttendanceMatcher`

## AttendanceDB

Proxy 代理，映射旧版表名到新版表名：

```js
// 旧版代码调用 AttendanceDB.punches -> 实际操作 DB.punch_records
// 旧版代码调用 AttendanceDB.leaves   -> 实际操作 DB.leave_records
```

自动重写以下方法中的表名参数：
- `table(tableName)` -> 自动转换表名
- 直接属性访问 `punches`/`leaves` -> 自动重定向到 `punch_records`/`leave_records`

## AttendanceRules

适配旧的 `get()`/`save()` API 到新的 `settings` 表（key-value 模式）。

```js
// 旧版: AttendanceRules.get() -> 从 settings 表读取 attendance_config
// 旧版: AttendanceRules.save(config) -> 写入 settings 表 key='attendance_config'
// 旧版: AttendanceRules.getHolidays() -> 从 DB.holidays 读取
```

同时提供一个简化的 `calculateMonth(month)` 方法，内部调用 `RulesEngine.calculateMonth()`。

## AttendanceMatcher

提供与旧版兼容的 `match()` 方法，内部实现为简化的规则引擎逻辑：

- `AttendanceMatcher.match(punches)` -> 按 (employeeNo, date) 分组打卡记录
- 返回包含 `signIn`、`signOut`、`status`、`lateMinutes`、`earlyMinutes`、`overtimeHours`、`workHours`、`leaveType` 的结果数组

## 依赖

`db.js`（`DB`、`Store` 对象），必须在 `init.js` 加载前完成初始化。

## 使用方式

```html
<script src="shared/db.js"></script>
<script src="shared/init.js"></script>
```

加载后即可通过 `window.AttendanceDB`、`window.AttendanceRules`、`window.AttendanceMatcher` 访问兼容 API。

## 注意事项

v2.0 页面的主要业务逻辑直接使用新版 API（`DB`、`Store`、`RulesEngine`、`Excel`），init.js 仅作为向后兼容层存在。新功能开发应使用新版 API。
