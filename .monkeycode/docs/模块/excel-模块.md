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
| `exportToExcel(records, template, filename)` | `async` | Flat 格式导出，调用 `_apiExport` 发往 `/api/export/flat` |
| `exportCalendarReport(targetMonth, fields)` | `async` | 日历月报格式导出。查询指定月考勤结果、排班、节假日后，通过 `_apiExport` 发往 `/api/export/calendar` |

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
5. 将 `{ targetMonth, fields, results, schedules, holidays }` 发往 `/api/export/calendar`
6. 后端生成日历月报 XLSX（部门分组、双行表头、单元格着色等样式由 Python openpyxl 完成）
