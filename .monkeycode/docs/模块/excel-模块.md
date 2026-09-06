# excel 模块

**文件**：`shared/excel.js`

## 职能

Excel 文件的全生命周期处理：解析上传、类型识别、数据标准化基于 SheetJS (xlsx)；导出通过 Python openpyxl 后端生成 XLSX。

## API

### 解析相关

| 方法 | 说明 |
|------|------|
| `parseExcelFile(file)` | 读取 File 对象为 Workbook |
| `getSheetNames(wb)` | 获取 Sheet 名称列表 |
| `sheetToJson(ws)` | Sheet 转 JSON 数组（默认 defval='' 处理空单元格） |
| `sheetToArray(ws)` | Sheet 转二维数组（header:1 模式） |

### 排班相关

| 方法 | 说明 |
|------|------|
| `_hasFill(cell)` | 判断单元格是否有背景填充色 |
| `parseScheduleSheet(ws, sheetName)` | 解析单个月份排班 Sheet |
| `isScheduleWorkbook(wb)` | 判断是否为排班工作簿 |
| `parseAllScheduleSheets(wb)` | 解析全部排班 Sheet |

### 识别相关

| 方法 | 说明 |
|------|------|
| `identifyFileType(wb)` | 自动识别文件类型 |
| `parseRecords(wb, fileType)` | 按类型解析全部记录 |

### 导出相关

导出流程由 Python `openpyxl` 后端处理，前端通过 HTTP API 发送 JSON 数据、接收 XLSX 二进制流触发浏览器下载。

| 方法 | 类型 | 说明 |
|------|------|------|
| `_apiExport(endpoint, data, filename)` | `async` | 内部 fetch 封装，POST JSON 到 Python 后端，接收 XLSX blob 并触发浏览器下载 |
| `_normalizeWorkTime(val)` | sync | 把 `HH:MM` / `HH:MM:SS` 规范成 `HH:MM` |
| `_getWorkTimes()` | `async` | 每次导出读 `Store.getByKey('settings','attendance_config')`，取 `.value.workStartTime` / `workEndTime`，缺省 `08:30`/`17:30` |
| `exportToExcel(records, template, filename)` | `async` | Flat 导出。调用 `_getWorkTimes()` 后 POST `/api/export/flat` |
| `exportCalendarReport(targetMonth, fields)` | `async` | 日历月报导出。同上取作息后 POST `/api/export/calendar` |

V3.2 实现位于 `attendance-v3/client/src/shared/excel.js`。`getByKey` 返回 `{key, value}`，必须解包 `.value`；直接读 `config.workStartTime` 得到空串，后端会落到默认 08:30。

## 条件格式规则

### 迟到/早退时间异常检测

导出 XLSX 对迟到/早退打卡标红字。规则以当前 `handlers/export.py` 为准：

迟到：签到 > `workStartTime`，红字。早退：签退 < `workEndTime`，红字。颜色来自 `RED_FONT`（`#FF0000`），无白字、无红底色阶。

日历月报对 `D3:{lastCol}{lastRow}` 挂 2 条规则：

```
AND(MOD(ROW(),2)=1,ISNUMBER(D3),D3>TIME(h,m,0))
AND(MOD(ROW(),2)=0,ISNUMBER(D3),D3<TIME(h,m,0))
```

平铺报表对签到/签退列逐列挂：

```
AND(ISNUMBER(D2),D2>TIME(h,m,0))
AND(ISNUMBER(F2),F2<TIME(h,m,0))
```

### 条件格式应用流程

1. 前端 `Excel._getWorkTimes()`：`Store.getByKey('settings','attendance_config')`，解包 `.value`，`_normalizeWorkTime` 去掉秒。
2. POST `/api/export/calendar` 或 `/api/export/flat`，带 `startTime`/`endTime`。
3. 后端 `_resolve_work_times()`：请求参数 → `settings.attendance_config` → `08:30`/`17:30`。
4. `_write_cell_value()` 把 `HH:MM` 写成 Excel `datetime.time`（`HH:MM`），`ISNUMBER` 才能命中。
5. 生成时直接给迟到/早退单元格 `RED_FONT`，再挂 FormulaRule。

详见 [专有概念/导出模板系统.md](../专有概念/导出模板系统.md)。

## 排班表解析细节

### Sheet 名称匹配

正则 `^\d{1,2}月$` 匹配 "1月" 到 "12月" 的 Sheet。

### 年份查找

遍历前 30 行，查找包含 `\d{4}年` 的单元格提取年份。

### 表头定位

查找包含 `周次`、`周一`、`周日` 全部关键词的行作为表头行。

### 列映射

扫描表头行，建立 `{ "周一": colIndex, ... }` 映射。若精确匹配不足 7 列，回退为正则 `^周[一二三四五六日]$` 模糊匹配。

### 填充色检测

`_hasFill()` 采用排除法：
- `patternType === 'none'` → 无填充
- `fgColor.rgb === 'FFFFFF'` → 白色（默认背景）
- `indexed === 64 或 65` → 系统自动色
- `theme === 1 且 tint === 0` → 无着色
- 其余有 `rgb` 或 `indexed` 非排除值 → 有填充色

## 日期/时间格式化

`_formatDate(val)` 处理两种格式：
- **数字** (Excel 日期序列号) → `XLSX.SSF.parse_date_code()` 分解为 y/m/d
- **字符串** → 正则匹配 `YYYY-MM-DD` 或 `YYYY/MM/DD` 格式

`_formatTime(val)` 处理两种格式：
- **小数** (< 1) → 乘 24 得小时，小数部分乘 60 得分钟
- **字符串** → 正则匹配 `HH:MM` 格式

## 导出流程

导出通过 `Excel._apiExport()` 统一处理：将数据 POST 到 Python 后端（`export_server.py`），后端使用 openpyxl 生成带样式的 XLSX，返回二进制 blob 由前端触发浏览器下载。

### `_apiExport(endpoint, data, filename)`

- 用 `fetch` 发送 `Content-Type: application/json` 的 POST 请求
- 请求体为 `data` 对象的 JSON 序列化
- 响应非 2xx 时抛出 `"导出失败: " + 错误信息` 异常
- 成功时将 blob 转为临时 URL，创建隐藏 `<a>` 触发下载后清理

### `exportToExcel(records, template, filename)`

- 将 `records`（考勤记录数组）、`template`（模板名）、`filename` 打包发往 `/api/export/flat`
- 后端生成 Flat 格式 XLSX（明细行列表）

### `exportCalendarReport(targetMonth, fields)`

1. 解析 `targetMonth`（格式 `YYYY-MM`）提取年、月
2. 从 IndexedDB 查询指定月的 `attendance_results`，无结果时抛错
3. 从 IndexedDB 查询对应年份的 `schedules`，筛选当月排班
4. 从 IndexedDB 查询全部 `holidays`，筛选当月节假日
5. `Excel._getWorkTimes()` 读 `attendance_config.value` 的 `workStartTime`/`workEndTime`
6. 将 `{ targetMonth, fields, results, schedules, holidays, startTime, endTime }` 发往 `/api/export/calendar`
7. 后端生成日历月报 XLSX（部门分组、双行表头、单元格着色 + 条件格式规则等样式由 Python openpyxl 完成）

## 加班记录导入修复

v2.0.2 修复了 `overtime` 类型记录的 `startTime` 字段长期为空导致的追溯缺失：

- **原问题**：`_normalizeRecord` 中 `case 'overtime'` 始终设置 `startTime: ''`，导致 `calculateMonth` 的 `(o.startTime || '').substring(0, 10)` 无法提取日期匹配
- **修复**：解析 `加班起止时间` 字段的原始值存入 `startTime`：Excel 数值（>1）通过 `_formatDate` 转 `YYYY-MM-DD`；字符串原样保留
- **影响**：加班 OA 记录现在可正确匹配到对应日期的考勤结果，详情弹窗中的加班追溯恢复正常
