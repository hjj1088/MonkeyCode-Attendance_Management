# db 模块

**文件**：`shared/db.js`

## 职能

数据库抽象层，封装 IndexedDB (Dexie.js) 的所有操作，提供 Schema 定义、CRUD 工具、自动恢复和默认初始化。

## Schema 版本管理

```js
DB = new Dexie('AttendanceDB');

DB.version(1).stores({
  raw_files, punch_records, leave_records, overtime_records,
  travel_records, miss_punch_records, schedules,
  attendance_results, carry_over, holidays, settings,
  export_templates, employees
});

DB.version(2).stores({
  travel_records: '++id, applicant, startDate'  // 新增 startDate 索引
}).upgrade(tx => tx.table('travel_records').clear());
```

版本 2 的升级清空了旧版 travel_records（因索引结构变更）。

## Store 工具

`Store._clean(value)` 是 Dexie 4.0.8 的必需防护措施：`bulkPut` 会修改传入数组的 `__dexie_key` 等内部字段。写入前必须 `JSON.parse(JSON.stringify(value))` 创建深拷贝。

### 关键方法

**`Store.bulkPut(tableName, records)`** - 批量插入/更新，自动深拷贝。空数组直接返回 0。

**`Store.resetAllData()`** - 清空全部 13 张表，重新调用 `initDefaultSettings()`。

**`Store.getByRange(tableName, indexName, lower, upper)`** - 范围查询，用于月度数据筛选。`between(lower, upper, true, true)` 表示闭区间。

## 自动恢复

`startDB()` 函数：
1. 打开数据库
2. 初始化默认设置
3. 若打开失败 → 删除数据库 (`Dexie.delete('AttendanceDB')`) → 重建 → 重试

## 默认设置初始化 (`initDefaultSettings`)

系统首次启动时自动创建：

1. **考勤规则配置** (`settings.attendance_config`)：
   ```js
   { workStartTime: '08:30', workEndTime: '17:30',
     lateThreshold: 0, earlyThreshold: 0,
     graceTimes: 2, graceMinutes: 30 }
   ```

2. **默认导出模板** (`export_templates`)：包含 14 个预定义字段的 flat 导出模板。

## 索引设计

| 表 | 索引 | 用途 |
|----|------|------|
| punch_records | date | 按月范围查询打卡数据 |
| schedules | [employeeNo+year+month] | 按员工+月份精确查排班 |
| attendance_results | [employeeNo+date] | 联合主键，查每人每天结果 |
| attendance_results | month | 按月批量查询 |
| attendance_results | department | 按部门筛选 |
| carry_over | [employeeNo+month] | 联合主键，查每人每月结余 |
