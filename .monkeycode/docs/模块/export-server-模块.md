# export_server 模块

**文件**：`attendance/export_server.py`

## 职能

Python HTTP 服务，使用 openpyxl 生成带单元格样式的 XLSX 考勤报表。同时提供静态文件服务（前端 HTML/JS）和导出 API 端点，单个进程承载全部后端功能。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/export/flat` | Flat（列表）报表导出 |
| `POST` | `/api/export/calendar` | Calendar（月报）报表导出 |
| `OPTIONS` | `/*` | CORS 预检请求 |

所有 API 响应均设置 `Access-Control-Allow-Origin: *`，允许跨域请求。

### POST /api/export/flat

请求体（JSON）：

```json
{
  "records": [{ "employeeNo": "001", "name": "张三", ... }],
  "template": { "fields": [{ "field": "name", "label": "姓名" }, ...] },
  "filename": "attendance_export.xlsx"
}
```

返回：`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，触发浏览器下载。

### POST /api/export/calendar

请求体（JSON）：

```json
{
  "targetMonth": "2025-06",
  "fields": [{ "field": "signIn", "label": "签到" }, ...],
  "results": [{ "employeeNo": "001", "date": "2025-06-01", ... }],
  "schedules": [{ "workDays": { "01": true, "02": false }, ... }],
  "holidays": [{ "date": "2025-06-10", "name": "端午节", "isWorkday": false }]
}
```

返回：同上 MIME 类型，文件名自动生成为 `考勤明细_{targetMonth}.xlsx`。

### OPTIONS /*

CORS 预检：返回 `204 No Content`，允许 `POST, OPTIONS` 方法及 `Content-Type` 请求头。

## 核心函数

### build_calendar_report(targetMonth, fields, results, schedules, holidays=None)

构建日历格式月报 XLSX。

处理流程：

1. **部门分组**：将考勤结果按 `department` 分组，员工按 `employeeNo` 排序
2. **双行表头**：第 1 行部门名（跨列合并），第 2 行员工姓名
3. **每日双行**：每天 2 行 —— 上午行（AM）和下午行（PM），日期/排班列跨 2 行合并
4. **合并单元格**：A1:A2（日期）、B1:B2（排班）、C1:C2（打卡时间）、部门表头按员工数合并
5. **休息日处理**：排班休息日或假期休息日整行填充 `GRAY_FILL`
6. **假期标注**：节假日日期在排班列显示假期名称（如"端午节"），替代默认"休息日"/"工作日"
7. **单元格样式**：通过 `_get_cell_style()` 为迟到/早退（红色）、OA 请假/出差/加班（蓝色）着色
8. **列宽自适应**：CJK 字符按 2 倍宽度估算，上限 30

### build_flat_report(records, template, filename)

构建平铺表格 XLSX。

处理流程：

1. 从 `template.fields` 提取表头标签
2. 写入加粗居中带边框的表头行
3. 遍历 records 逐行写入数据，`_index` 特殊字段自动填充行号
4. 通过 `_get_cell_style()` 为异常状态单元格着色
5. 列宽自适应，上限 40

### _get_cell_style(val)

根据单元格文本内容返回 `(font, fill)` 元组：

| 文本匹配 | 样式 | 说明 |
|----------|------|------|
| `请假\|出差\|加班\|补卡` | `BLUE_FONT` (#0066CC) | OA 审批类状态 |
| `迟\|早` | `RED_FONT` (#FF0000) | 迟到/早退标记 |
| `^\d{1,2}:\d{2}` (时间格式) | `RED_FONT` | 打卡时间异常 |
| 其他 | 无样式 | 正常文本 |

注：`_get_cell_style()` 在中途有一个不可达的 `return` 语句（第 42 行），其下方代码（第 44-52 行）为实际生效逻辑。该结构不改变功能但存在冗余分支。

### build_am_cell(r) / build_pm_cell(r)

构建上午/下午行单元格内容的内联函数（定义在 `build_calendar_report` 内部）。

**build_am_cell** 返回值：

| 条件 | 显示内容 |
|------|----------|
| 记录为空 | 空 |
| `status='rest'` | 空 |
| `status='leave'` | `请假/类型/nh`（根据 fields 控制字段显示） |
| `status='travel'` | `出差/nh` |
| `status='absent'` 或 `absent=true` | `缺勤` |
| `status='overtime'/'suspect_ot'` | `加班/nh` |
| 有签到时间 | `signIn 值 [+ 迟nmin]` |
| 其他 | 空 |

**build_pm_cell** 返回值：

| 条件 | 显示内容 |
|------|----------|
| 记录为空 | 空 |
| `status` 为 rest/leave/travel/absent | 空 |
| `absent=true` | 空 |
| 有签退时间 | `signOut 值 [+ 早nmin]` |
| 其他 | 空 |

## 样式常量

```python
RED_FONT   = Font(color='FFFF0000')                                    # 红色，迟到/早退
BLUE_FONT  = Font(color='FF0066CC')                                    # 蓝色，OA 审批
GRAY_FILL  = PatternFill(start_color='FFD9D9D9', end_color='FFD9D9D9', fill_type='solid')  # 灰色背景，休息日
THIN_BORDER = Border(left=..., right=..., top=..., bottom=..., style='thin')  # 细边框
CENTER_ALIGN = Alignment(horizontal='center', vertical='center')        # 居中对齐
```

颜色值为 ARGB 格式（`FF` 前缀为完全不透明）。

## 依赖

| 依赖 | 用途 |
|------|------|
| `openpyxl` (3.1.5+) | XLSX 工作簿创建、单元格样式、合并单元格、列宽设置 |
| `http.server` | Python 标准库 HTTP 服务器 |
| `json` | 请求体 JSON 解析 |
| `io` | 内存中生成 XLSX 二进制流（BytesIO） |
| `os` | 环境变量读取（PORT）、文件路径处理 |
| `urllib.parse` | URL 路径解析与文件名编码 |
| `calendar` | `monthrange()` 获取每月天数 |
| `re` | 单元格文本正则匹配（样式判定） |

## 与旧方案的差异

系统最初使用前端 SheetJS（`xlsx.full.min.js`）完成 Excel 导出，存在以下限制：

| 维度 | SheetJS (旧) | openpyxl (当前) |
|------|-------------|-----------------|
| 单元格样式 | 社区版不支持写入字体颜色/填充色 | 原生支持 Font/Fill/Border/Alignment |
| 合并单元格 | 支持但 API 复杂 | `merge_cells()` 简洁直观 |
| 列宽自适应 | 运行时受限于浏览器性能 | 服务端计算，不受浏览器限制 |
| 假期标注 | 无法区分 | 可标注假期名称替代默认标签 |
| 文件编码 | 中文文件名下载需额外处理 | `Content-Disposition` UTF-8 编码标准处理 |

切换后，前端 `excel.js` 中的导出方法（`exportToExcel`、`exportCalendarReport`）改为通过 `_apiExport()` 将 JSON 数据 POST 到 Python 后端，由 `export_server.py` 生成最终 XLSX 文件并返回下载。

## 服务启动

```bash
# 安装依赖
pip install openpyxl

# 启动服务（默认 8000 端口）
python3 /workspace/attendance/export_server.py

# 自定义端口
PORT=8080 python3 /workspace/attendance/export_server.py
```

`ExportHandler` 继承 `SimpleHTTPRequestHandler`，`directory` 参数指向 `export_server.py` 所在目录（即 `/workspace/attendance/`），使得同一服务既能返回静态 HTML/JS 文件，也能处理 API 路由。

## 错误处理

- `ExportHandler.do_POST()` 仅匹配 `/api/export/flat` 和 `/api/export/calendar`，其余路径返回 404
- 导出过程异常捕获后返回 500，错误信息写入响应体
- 日志输出通过重写 `log_message()` 抑制（`pass`），保持控制台清洁
