# export_server 模块

**文件**：`attendanceapp/export_server.py`

## 职能

Python HTTP 服务，使用 openpyxl 生成带单元格样式的 XLSX 考勤报表。同时提供静态文件服务（前端 HTML/JS）和导出 API 端点，单个进程承载全部后端功能。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查，返回版本信息 JSON |
| `POST` | `/api/export/flat` | Flat（列表）报表导出 |
| `POST` | `/api/export/calendar` | Calendar（月报）报表导出 |
| `OPTIONS` | `/*` | CORS 预检请求 |

所有 API 响应均设置 `Access-Control-Allow-Origin: *`，允许跨域请求。

### GET /health

v2.0.3 新增。返回 JSON 格式的服务版本和运行状态信息，用于验证 Docker 镜像版本：

```json
{
  "status": "ok",
  "service": "attendance-export-server",
  "version": "ed71a7b0c524219d77805adcf13a63022530da6e",
  "build_time": "2026-07-17T01:20:50Z",
  "python": "3.12.13",
  "server_time": "2026-07-17T01:45:11.635068+00:00"
}
```

| 字段 | 说明 |
|------|------|
| `version` | Git SHA，Docker 构建时注入 |
| `build_time` | Docker 镜像构建时间（UTC） |
| `python` | Python 运行时版本 |
| `server_time` | 服务器当前时间（UTC） |

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
5. **休息日处理**：排班休息日或假期休息日整行填充 `GRAY_FILL`；在此之前先通过 `_get_cell_style()` 保留 OA 状态字体颜色（蓝色），然后再覆盖灰色填充
6. **假期标注**：节假日日期在排班列显示假期名称（如"端午节"），替代默认"休息日"/"工作日"
7. **作息时间预处理**：从 schedules 提取 `schedule_by_date` 映射 `{date_str: {workStartTime, workEndTime}}`，供迟到/早退判定使用
8. **迟到/早退直接样式**：AM 行签到时间通过 `_time_to_minutes()` 与日期的 `workStartTime` 做数值比较，大于则 `RED_FONT`；PM 行签退时间与 `workEndTime` 比较，小于则 `RED_FONT`
9. **全局条件格式**：对整体数据范围生成 2 条 `FormulaRule`：
   - 迟到：`MOD(ROW(),2)=1`（奇数行=AM）× `TIMEVALUE(D3) > TIME(startTime)`
   - 早退：`MOD(ROW(),2)=0`（偶数行=PM）× `TIMEVALUE(D3) < TIME(endTime)`
   公式中 `D3` 为范围的左上角相对引用，Excel 自动对范围内每个单元格做偏移适配
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
5. 对签到/签退列（`field == 'signIn'/'signOut'` 或标签含 `签到`/`签退`）对应的单元格用 `_time_to_minutes()` 做数值时间比较：签到 > 上班时间 → `RED_FONT`，签退 < 下班时间 → `RED_FONT`；同时为这些列按列生成条件格式 `FormulaRule`
6. 列宽自适应，上限 40

### _get_cell_style(val)

根据单元格文本内容返回 `(font, fill)` 元组：

| 文本匹配 | 样式 | 说明 |
|----------|------|------|
| `假\|休\|出差\|加班\|补卡` | `BLUE_FONT` (#0066CC) | OA 审批类状态（含调休、公休、补休、婚假等所有假期类型） |
| `迟\|早\|上班未打卡\|下班未打卡\|缺勤` | `RED_FONT` (#FF0000) | 迟到/早退/未打卡/缺勤标记 |
| 其他 | 无样式 | 正常文本 |

v2.0.2 将正则从 `请假|出差|加班|补卡` 改为 `假|休|出差|加班|补卡`，覆盖 `调休`/`公休`/`补休` 等不带"请假"前缀的 OA 类型。移除了 `^\d{1,2}:\d{2}` 时间格式全量标红规则，改为由下半部分的迟到/早退直接样式+条件格式双重机制精确控制。

### _is_time_val(val)

模块级工具函数，判断一个值是否为有效时间格式（`HH:MM` 或 `H:MM`，正则 `^\d{1,2}:\d{2}$`）。用于条件格式生成和迟到/早退的时间判断。

### _time_to_minutes(t)

v2.0.2 新增。将 `HH:MM` 时间字符串转换为分钟数（`int(h)*60 + int(m)`），无效返回 `None`。用于直接单元格样式中的迟到/早退时间比较，替代不可靠的字符串字典序比较（如 `"17:40" < "17:30"` 在 Python 中是字符串比而非时间比）。

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

v2.0.2 新增迟到/早退的 Excel 条件格式，采用**直接单元格样式 + FormulaRule** 双重保障：

### 日历报表：2 条全局规则

对整个数据范围 `D3:{last_col}{last_row}` 应用 2 条 `FormulaRule`，通过 `MOD(ROW())` 区分上午（奇数行）/下午（偶数行），`D3` 作为范围的左上角相对引用使 Excel 自动逐行偏移：

| 规则 | 公式 | 效果 |
|------|------|------|
| 迟到 | `AND(MOD(ROW(),2)=1, D3<>"", NOT(ISERROR(TIMEVALUE(D3))), TIMEVALUE(D3)>TIME(h,m,0))` | 奇数行（AM）时间 > 上班时间 → 红字 |
| 早退 | `AND(MOD(ROW(),2)=0, D3<>"", NOT(ISERROR(TIMEVALUE(D3))), TIMEVALUE(D3)<TIME(h,m,0))` | 偶数行（PM）时间 < 下班时间 → 红字 |

### 平铺报表：按列规则

签到/签退位于不同列，每列单独应用规则：

| 规则 | 公式 | 效果 |
|------|------|------|
| 迟到 | `AND(D2<>"", NOT(ISERROR(TIMEVALUE(D2))), TIMEVALUE(D2)>TIME(h,m,0))` | 签到列时间 > 上班时间 → 红字 |
| 早退 | `AND(F2<>"", NOT(ISERROR(TIMEVALUE(F2))), TIMEVALUE(F2)<TIME(h,m,0))` | 签退列时间 < 下班时间 → 红字 |

### 作息时间来源

`startTime`/`endTime` 优先级：前端传入 > 排班 schedules 数据提取 > 兜底默认 `08:30`/`17:30`。

### 关键设计要点

1. **`D3<>""` 替代 `ISTEXT(D3)`**：因所有数据单元格已设 `number_format = '@'`（文本格式），空单元格也满足 `ISTEXT()` 导致误判，改用非空检查
2. **直接样式用 `_time_to_minutes()` 数值比较**：避免 Python 字符串字典序误判（如 `"17:40" > "17:30"` 在字符串比较中为 `True` 但并非早退）
3. **日历 2 条规则 vs 逐列 62 条**：范围 `D3:AH64` 统一应用，`MOD(ROW())` 区分 AM/PM，`D3` 相对引用自动适配各列各行的单元格

## 样式常量

```python
RED_FONT   = Font(color='FFFF0000')                                    # 红色，迟到/早退
BLUE_FONT  = Font(color='FF0066CC')                                    # 蓝色，OA 审批
GRAY_FILL  = PatternFill(start_color='FFD9D9D9', end_color='FFD9D9D9', fill_type='solid')  # 灰色背景，休息日
TEXT_FMT   = '@'                                                        # 文本格式，防止 Excel 将时间值自动转为时间序列号
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
# 本地开发
pip install openpyxl
python3 /workspace/attendanceapp/export_server.py

# 自定义端口
PORT=8080 python3 /workspace/attendanceapp/export_server.py

# Docker 部署
docker run -d -p 38000:8000 ghcr.io/hjj1088/monkeycode-attendance_management:latest

# 启动日志示例
# ============================================================
#  考勤导出服务器  Attendance Export Server
# ============================================================
#  Git SHA      : ed71a7b0c524219d77805adcf13a63022530da6e
#  Build Time   : 2026-07-17T01:20:50Z
#  Python       : 3.12.13
#  Port         : 8000
#  Health Check : http://0.0.0.0:8000/health
#  Start Time   : 2026-07-17T01:45:11.635068+00:00
# ============================================================
```

`ExportHandler` 继承 `SimpleHTTPRequestHandler`，`directory` 参数指向 `export_server.py` 所在目录（即 `/workspace/attendanceapp/`），使得同一服务既能返回静态 HTML/JS 文件，也能处理 API 路由。

启动时通过 `_startup_banner()` 打印版本信息横幅（含 Git SHA、构建时间、Python 版本、端口、health 地址），便于在 Docker logs 中识别运行版本。Git SHA 和构建时间在 Docker 镜像构建时通过 `--build-arg` 注入到 `version.py`。

## 访问日志

v2.0.3 恢复了 HTTP 请求日志输出。`log_message()` 使用标准 Apache 格式写入 `stderr`：

```
127.0.0.1 - - [17/Jul/2026 01:21:26] "GET /health HTTP/1.1" 200 -
172.17.0.1 - - [17/Jul/2026 01:21:18] "GET /shared/dexie.min.js HTTP/1.1" 200 -
```

每条日志包含客户端 IP、请求时间戳、HTTP 方法、路径和响应状态码。Docker 容器的 `docker logs` 命令可直接查看。

## 错误处理

- `ExportHandler.do_GET()` 处理 `/health` 路由，其余路径回退到父类 `SimpleHTTPRequestHandler.do_GET()` 返回静态文件
- `ExportHandler.do_POST()` 仅匹配 `/api/export/flat` 和 `/api/export/calendar`，其余路径返回 404
- 导出过程异常捕获后返回 500，错误信息写入响应体
