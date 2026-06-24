# excel 模块

**文件**：`shared/excel.js`

## 职能

Excel 文件的全生命周期处理：解析上传、类型识别、数据标准化、导出生成。基于 SheetJS (xlsx)。

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

| 方法 | 说明 |
|------|------|
| `exportToExcel(records, template, filename)` | Flat 格式导出 |
| `exportCalendarReport(targetMonth)` | 日历月报格式导出 |

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

## 日历月报导出

详见 [专有概念/导出模板系统.md](../专有概念/导出模板系统.md)。

核心逻辑 (`exportCalendarReport`)：
1. 查询指定月考勤结果
2. 按部门分组建列，员工按考勤号排序
3. 生成双行表头（部门名跨列合并 + 员工名列）
4. 每天 2 行（上午/下午），日期/排班列跨 2 行合并
5. 日期列使用 Excel 序列号格式
6. 根据考勤状态和 OA 来源填充单元格文本
