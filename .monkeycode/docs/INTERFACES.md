# 接口文档

## 数据库 Schema

基于 Dexie.js 的 IndexedDB 数据库 `AttendanceDB`，共 13 张表。

### 表结构

#### raw_files
已导入文件的记录（用于去重）。
```js
'++id, fileType, importTime'
```
| 字段 | 说明 |
|------|------|
| id | 自增主键 |
| fileName | 文件名 |
| fileType | 文件类型 (punch/leave/overtime/travel/miss_punch/schedule) |
| importTime | 导入时间 |

#### punch_records - 打卡记录
```js
'++id, employeeNo, name, date, department'
```
| 字段 | 说明 |
|------|------|
| id | 自增主键 |
| employeeNo | 考勤号 |
| name | 姓名 |
| date | 日期 (YYYY-MM-DD) |
| period | 时段 (上午/下午) |
| scheduleStart | 排班上班时间 |
| scheduleEnd | 排班下班时间 |
| signIn | 签到时间 |
| signOut | 签退时间 |
| lateMinutes | 迟到(分钟) |
| earlyMinutes | 早退(分钟) |
| absent | 是否旷工 |
| overtimeHours | 加班时间 |
| department | 部门 |

#### leave_records - 请假记录
```js
'++id, applicant, startDate, endDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| department | 申请部门 |
| leaveType | 请假类型 (含"调休"关键字触发结余扣减) |
| startDate | 开始日期 |
| endDate | 结束日期 |
| leaveDays | 请假天数 |
| leaveHours | 请假小时数 |
| reason | 请假事由 |

#### overtime_records - 加班记录
```js
'++id, applicant'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| startTime | 开始时间 |
| endTime | 结束时间 |
| overtimeHours | 加班小时数 |
| content | 加班内容 |

#### travel_records - 出差记录
```js
'++id, applicant, startDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| startDate | 开始日期 |
| endDate | 结束日期 |
| destination | 目的地 |
| reason | 出差事由 |

#### miss_punch_records - 漏打卡记录
```js
'++id, applicant, missDate'
```
| 字段 | 说明 |
|------|------|
| applicant | 申请人姓名 |
| missDate | 忘记打卡日期 |
| missPerson | 忘打卡人员 |
| missTime | 未打卡时间 |
| cardTime | 当天刷卡时间 |
| reason | 事由 |

#### schedules - 排班表 (按员工展开)
```js
'++id, [employeeNo+year+month], year, month'
```
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| department | 部门 |
| year | 年份 |
| month | 月份 |
| workDays | `{ "01": true, "02": false, ... }` - 每天是否上班 |

#### attendance_results - 考勤计算结果
```js
'[employeeNo+date], employeeNo, date, month, department, status'
```
主关键字为 `[employeeNo+date]` 联合主键，确保每人每天仅一条结果。
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| department | 部门 |
| date | 日期 |
| month | 月份 |
| status | 考勤状态 (normal/rest/abnormal/leave/travel/absent) |
| signIn | 签到时间 |
| signOut | 签退时间 |
| lateMinutes | 迟到分钟 |
| earlyMinutes | 早退分钟 |
| overtimeHours | 加班小时 |
| travelHours | 出差小时 |
| leaveType | 请假类型 |
| isRestDay | 是否排班休息日 (仅由排班表+假期决定) |
| absent | 是否旷工 |
| sourcePunchIds | 关联打卡记录 ID 列表 |
| sourceLeaveIds | 关联请假记录 ID 列表 |
| sourceTravelIds | 关联出差记录 ID 列表 |
| sourceMissIds | 关联漏打卡记录 ID 列表 |
| sourceOvertimeIds | 关联加班记录 ID 列表 |

#### carry_over - 加班结余
```js
'[employeeNo+month], employeeNo, month'
```
| 字段 | 说明 |
|------|------|
| employeeNo | 考勤号 |
| name | 姓名 |
| month | 月份 |
| overtimeBalance | 累计结余小时 (非负) |

#### holidays - 假期管理
```js
'++id, date'
```
| 字段 | 说明 |
|------|------|
| date | 日期 |
| name | 假期名称 |
| isWorkday | 是否调休上班日 |
| isHoliday | 是否休息日 |

#### settings - 系统设置 (key-value)
```js
'key'
```
| key | value |
|-----|-------|
| attendance_config | 考勤规则配置对象 |
| config_updated_at | 配置更新时间戳 |
| last_calc_{YYYY-MM} | 某月份最后计算时间 |

#### export_templates - 导出模板
```js
'++id, isDefault'
```

#### employees - 员工列表
```js
'employeeNo, name, department'
```

## Store CRUD API

所有表通过 `Store` 工具对象访问：

| 方法 | 说明 |
|------|------|
| `Store.bulkPut(tableName, records)` | 批量插入/更新，自动 JSON 深拷贝防污染 |
| `Store.clearTable(tableName)` | 清空表 |
| `Store.getAll(tableName)` | 获取全部记录 |
| `Store.getByIndex(tableName, indexName, value)` | 按索引查询 |
| `Store.getByRange(tableName, indexName, lower, upper)` | 按索引范围查询 |
| `Store.getByKey(tableName, key)` | 按主键查询 |
| `Store.put(tableName, record)` | 插入/更新单条 |
| `Store.deleteByKey(tableName, key)` | 按主键删除 |
| `Store.resetAllData()` | 清空所有表并重新初始化 |

> **注意**：Dexie 4.0.8 中 `bulkPut` 会修改传入数组，必须在写入前通过 `JSON.parse(JSON.stringify(value))` 创建深拷贝。

## 文件类型识别规则

`Excel.identifyFileType()` 通过表头关键词匹配识别以下类型：

| 类型 | 必含表头 | 加分表头 |
|------|----------|----------|
| punch (打卡) | 考勤号码, 签到时间 | 签退时间, 迟到时间, 部门, 日期 |
| leave (请假) | 请假类型, 开始日期 | 结束日期, 请假天数, 申请人 |
| overtime (加班) | 加班起止时间 | 申请人, 加班内容 |
| travel (出差) | 出差起止日期 | 申请人, 目的地, 出差事由 |
| miss_punch (漏打卡) | 忘打卡日期 | 申请人, 未打卡时间, 事由 |

排班文件通过 Sheet 名称识别：匹配 `^\\d{1,2}月$` 的 Sheet 名。

## 认证 API

```js
Auth.isLoggedIn()        // 检查是否已登录
Auth.login(user, pass)   // 登录 (默认 admin/admin123)
Auth.logout()            // 登出并跳转到登录页
Auth.requireAuth()       // 页面守卫 (未登录跳转)
```

## Matcher API

```js
Matcher.buildEmployeeMap()           // 从打卡记录构建 { 考勤号 → {name, dept} }
Matcher.syncEmployees()              // 同步到 employees 表
Matcher.resolveEmployeeNo(name, dept) // 姓名+部门 → 考勤号
Matcher.matchOAToPunch(records, type) // OA 记录 → 考勤号匹配
```

## RulesEngine API

```js
RulesEngine.getConfig()                  // 获取考勤规则配置
RulesEngine.getHolidays()                // 获取全部假期
RulesEngine.calculateMonth(targetMonth)  // 计算指定月考勤
RulesEngine.getMonthResults(targetMonth) // 获取某月考勤结果
RulesEngine.getResultDetail(eno, date)   // 获取某天详情 (含关联源记录)
```

## HTTP 导出 API

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/api/export/flat` | POST | `{records: array, template: {fields: [{label, field}]}, filename: string}` | 二进制 XLSX, `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `/api/export/calendar` | POST | `{targetMonth: "YYYY-MM", fields: array, results: array, schedules: array, holidays: array}` | 二进制 XLSX |
| `/*` | OPTIONS | — | 204, `Access-Control-Allow-Origin: *` (CORS 预检)
