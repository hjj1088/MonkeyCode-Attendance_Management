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
  "filename": "attendance_export.xlsx",
  "startTime": "08:30",
  "endTime": "17:30"
}
```

`startTime`/`endTime` 为选填参数，用于生成迟到/早退条件格式规则。未传入时从数据中自动提取，兜底默认 `08:30`/`17:30`。

返回：`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，触发浏览器下载。

### POST /api/export/calendar

请求体（JSON）：

```json
{
  "targetMonth": "2025-06",
  "fields": [{ "field": "signIn", "label": "签到" }, ...],
  "results": [{ "employeeNo": "001", "date": "2025-06-01", ... }],
  "schedules": [{ "workDays": { "01": true, "02": false }, ... }],
  "holidays": [{ "date": "2025-06-10", "name": "端午节", "isWorkday": false }],
  "startTime": "08:30",
  "endTime": "17:30"
}
```

`startTime`/`endTime` 选填，同上用于条件格式生成，兜底默认 `08:30`/`17:30`。

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
5. **休息日处理**：排班休息日或假期休息日整行填充 `GRAY_FILL`，在此之前先通过 `_get_cell_style()` 保留状态字体颜色
6. **假期标注**：节假日日期在排班列显示假期名称（如"端午节"），替代默认"休息日"/"工作日"
7. **迟到/早退标记**：预处理 `schedule_by_date` 映射，每日期整体签到签退时间如果满足条件（`signIn > startTime` 或 `signOut < endTime`），为该日期格设置 `RED_FONT` 直接样式
8. **逐列独立条件格式**：为工作日的每列生成 `FormulaRule`（不含 `$` 绝对引用），迟到用 `TIMEVALUE(cell) > TIMEVALUE(startTime)`，早退用 `TIMEVALUE(cell) < TIMEVALUE(endTime)`，各列独立应用 `RED_FONT`
9. **单元格直接样式**：通过 `_get_cell_style()` 为迟到/早退（红色）、OA 假/休/出差/加班/补卡（蓝色）着色
10. **列宽自适应**：CJK 字符按 2 倍宽度估算，上限 30

### build_flat_report(records, template, filename)

构建平铺表格 XLSX。

处理流程：

1. 从 `template.fields` 提取表头标签
2. 写入加粗居中带边框的表头行
3. 遍历 records 逐行写入数据，`_index` 特殊字段自动填充行号，`status` 字段通过 `status_labels` 映射为中文标签：
   ```
   'normal' → '正常', 'rest' → '休息', 'abnormal' → '迟到',
   'leave' → '请假', 'travel' → '出差', 'absent' → '缺勤',
   'overtime' → '加班', 'suspect_ot' → '疑似加班',
   'no_sign_in' → '上班未打卡', 'no_sign_out' → '下班未打卡'
   ```
4. 通过 `_get_cell_style()` 为异常状态单元格着色
5. 对签到/签退列（`field == 'signIn'/'signOut'` 或标签含 `签到`/`签退`）按列生成逐列独立 `FormulaRule`，迟到/早退用 `RED_FONT` 条件格式；同时对签到/签退单元格直接设置 `RED_FONT`
6. 列宽自适应，上限 40

### _get_cell_style(val)

根据单元格文本内容返回 `(font, fill)` 元组：

| 文本匹配 | 样式 | 说明 |
|----------|------|------|
| `假\|休\|出差\|加班\|补卡` | `BLUE_FONT` (#0066CC) | OA 审批类状态（含调休、公休、补休、婚假等所有假期类型） |
| `迟\|早\|上班未打卡\|下班未打卡` | `RED_FONT` (#FF0000) | 迟到/早退/未打卡标记 |
| `^\d{1,2}:\d{2}` (时间格式) | `RED_FONT` | 打卡时间异常 |
| 其他 | 无样式 | 正常文本 |

v2.0.2 将正则从 `请假|出差|加班|补卡` 改为 `假|休|出差|加班|补卡`，覆盖 `调休`/`公休`/`补休` 等不带"请假"前缀的 OA 类型。

### _is_time_val(val)

新增模块级工具函数，判断一个值是否为有效时间格式（`HH:MM` 或 `H:MM`）。用于条件格式生成和迟到/早退的时间判断。

### build_am_cell(r) / build_pm_cell(r)

构建上午/下午行单元格内容的内联函数（定义在 `build_calendar_report` 内部）。

**build_am_cell** 返回值：

| 条件 | 显示内容 |
|------|----------|
| 记录为空 | 空 |
| `status='rest'` | 空 |
| `status='leave'` | `类型/nh`（如 `婚假/3.5h`；类型+时长都无时回退显示 `请假`） |
| `status='travel'` | `出差/nh` |
| `status='absent'` 或 `absent=true` | `缺勤` |
| `status='no_sign_in'` | `上班未打卡` (通过 `_get_cell_style` 获得 `RED_FONT`) |
| `status='overtime'/'suspect_ot'` | `加班/nh`（不再替换为"疑似加班"，直接显示签到时间） |
| 有签到时间 | `signIn 值 [+ 迟nmin]` |
| 其他 | 空 |

**build_pm_cell** 返回值：

| 条件 | 显示内容 |
|------|----------|
| 记录为空 | 空 |
| `status` 为 rest/leave/travel/absent | 空 |
| `absent=true` | 空 |
| `status='no_sign_out'` | `下班未打卡` (通过 `_get_cell_style` 获得 `RED_FONT`) |
| 有签退时间 | `signOut 值 [+ 早nmin]` |
| 其他 | 空 |

> **v2.0.2 变更**：`build_am_cell` 中 `leave` 状态 `请假/` 前缀已移除（直接显示 `类型/h`），`overtime`/`suspect_ot` 状态不再覆盖签到时间为"疑似加班"文本。

## 条件格式规则

v2.0.2 新增迟到/早退的 Excel 条件格式（Conditional Formatting），采用**直接单元格样式 + 逐列独立 FormulaRule** 双重保障策略：

### 设计决策

经过多轮迭代（统一大范围 + `INDIRECT(ADDRESS())` → D3 相对引用 → 逐列独立），最终采用**逐列生成独立 `FormulaRule`** 方案：

- 日历报表：遍历每个工作日的每个员工列，为每列生成独立的 `FormulaRule`（如 D3:D64 配 `D3<>""`）
- 平铺报表：遍历所有签到/签退列（`field == 'signIn'/'signOut'` 或标签含 `签到`/`签退`），为每列生成独立的 `FormulaRule`

### 规则公式

| 场景 | 公式 | 说明 |
|------|------|------|
| 日历报表迟到 | `AND(TIMEVALUE(D3) > TIMEVALUE("08:30"), MOD(ROW(D3),2)=1)` | 奇数行（AM 行）签到时间大于上班时间 |
| 日历报表早退 | `AND(TIMEVALUE(D4) < TIMEVALUE("17:30"), MOD(ROW(D3),2)=0, LEN(D4)>0)` | 偶数行（PM 行）签退时间小于下班时间 |
| 平铺报表迟到 | `AND(TIMEVALUE(D3) > TIMEVALUE("08:30"), LEN(D3)>0)` | 签到时间大于上班时间 |
| 平铺报表早退 | `AND(TIMEVALUE(F3) < TIMEVALUE("17:30"), LEN(F3)>0)` | 签退时间小于下班时间 |

### 双重保障

1. **直接单元格样式**：在生成 XLSX 时直接设置 `cell.font = RED_FONT`，确保红色字体始终可见
2. **FormulaRule 条件格式**：通过 `ws.conditional_formatting.add(range_string, rule)` 添加，用户可在 Excel 中查看/编辑规则

开放调试日志记录 `_st`/`_et` 值和 `rules_added` 计数，便于排查条件格式是否生效。`MOD(ROW())` 用于日历报表区分 AM（奇数行）/PM（偶数行）。

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

`ExportHandler` 继承 `SimpleHTTPRequestHandler`，`directory` 参数指向 `export_server.py` 所在目录（即 `/workspace/attendanceapp/`），使得同一服务既能返回静态 HTML/JS 文件，也能处理 API 路由。

## 错误处理

- `ExportHandler.do_POST()` 仅匹配 `/api/export/flat` 和 `/api/export/calendar`，其余路径返回 404
- 导出过程异常捕获后返回 500，错误信息写入响应体
- 日志输出通过重写 `log_message()` 抑制（`pass`），保持控制台清洁
