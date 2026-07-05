# 系统架构

## 概述

考勤管理系统是一个**前后端分离**的考勤数据处理工具。前端运行在浏览器端负责数据导入、规则计算、查询浏览；后端由 Python 导出服务 (`export_server.py`) 负责生成带样式的 XLSX 报表。系统处理企业考勤数据的完整生命周期：导入 Excel -> 规则计算 -> 查询浏览 -> 导出报表。

v2.0 进行了 macOS Big Sur 风格重设计，引入统一的 `bigsur.css` 设计系统替代 Tailwind CDN，新增侧边栏导航 (`layout.js`) 和模块兼容桥接层 (`init.js`)。

## 技术栈

| 层级 | 技术 | 版本/方式 | 用途 |
|------|------|-----------|------|
| UI 框架 | Vue.js | 3.x (本地文件) | 响应式界面，Options API 组件化开发 |
| CSS 框架 | bigsur.css | 本地文件 (472行) | macOS Big Sur + 中国风设计系统，无 CDN 依赖 |
| 图标 | Lucide SVG | 内嵌 | 侧边栏导航和登录页图标 |
| 数据存储 | Dexie.js | 4.0.8 (本地文件) | IndexedDB 封装，SQL-like 查询 |
| Excel 导入 | SheetJS (xlsx) | 0.20.3 (本地文件) | Excel 解析、单元格颜色读取 |
| Excel 导出 | Python openpyxl | 3.1.5 (pip) | XLSX 生成，支持单元格样式（字体颜色、填充色） |
| 后端服务 | Python http.server | 标准库 | HTTP API + 静态文件服务，单进程 |
| 认证 | localStorage | 浏览器原生 | 简单的用户名/密码认证 |
| 部署 | Python 单进程 | 标准库 | `export_server.py` 同时提供静态文件与 API 端点 |

前端依赖全部本地化（`shared/` 目录），无需 npm/pnpm 构建步骤，无 CDN 依赖。Python 依赖 `openpyxl` 需通过 `pip install openpyxl` 安装。

## 项目结构

```
attendanceapp/
├── index.html            # 登录页入口（宣纸白渐变 + 毛玻璃卡片）
├── login.html            # 登录页（与 index.html 内容相同）
├── attendance.html       # 考勤计算页（列表/日历双视图 + 详情弹窗 + 部门/状态/姓名筛选）
├── import.html           # 数据导入页（拖拽上传 + 自动识别类型 + 预览弹窗 + 导入日志）
├── export.html           # 导出中心（模板管理 + 平铺/日历导出 + 实时预览）
├── settings.html         # 系统设置（考勤规则 + 容错规则 + 假期管理 + 数据库重置）
├── export_server.py      # Python 导出服务（HTTP API + 静态文件，openpyxl 生成 XLSX）
├── requirements.txt      # Python 依赖声明
├── Dockerfile            # Docker 容器化部署
└── shared/               # 共享模块（全部本地文件）
    ├── bigsur.css        # Big Sur 设计系统（CSS 变量 + 组件类 + 毛玻璃效果）
    ├── layout.js         # 侧边栏导航框架（AppLayout，v2.0 新增）
    ├── init.js           # 模块兼容桥接层（AttendanceDB/AttendanceRules/AttendanceMatcher，v2.0 新增）
    ├── auth.js           # 认证模块
    ├── db.js             # 数据库模块
    ├── rules.js          # 规则引擎模块
    ├── excel.js          # Excel 处理模块（SheetJS 导入 + API 导出）
    ├── matcher.js        # 数据匹配模块
    ├── dexie.min.js      # Dexie.js 本地文件 (230KB)
    ├── vue.min.js        # Vue.js 3 本地文件 (131KB)
    └── xlsx.min.js       # SheetJS 本地文件 (882KB)
```

## 模块依赖关系

```
index.html / login.html
    +-- bigsur.css
    +-- dexie.min.js
    +-- auth.js

attendance.html
    +-- bigsur.css + dexie.min.js + vue.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> rules.js

import.html
    +-- bigsur.css + dexie.min.js + vue.min.js + xlsx.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> excel.js -> matcher.js

export.html
    +-- bigsur.css + dexie.min.js + vue.min.js + xlsx.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js -> excel.js

settings.html
    +-- bigsur.css + dexie.min.js + vue.min.js
    +-- auth.js -> layout.js (Auth)
    +-- db.js

init.js (独立，向后兼容桥接)
    +-- db.js (DB, Store)

export_server.py (独立进程，HTTP API + 静态文件)
```

模块间调用关系：
- `auth.js` 不依赖其他模块
- `db.js` 不依赖其他模块
- `layout.js` 依赖 `auth.js`
- `excel.js` 依赖 `db.js` (导出时需要查询 DB)
- `matcher.js` 依赖 `db.js`
- `rules.js` 依赖 `db.js`
- `init.js` 依赖 `db.js`

## 数据流

```
+------------------------------------------------------------------+
|                        数据生命周期                                |
+---------+   +---------+   +----------+   +----------+   +------+
| Excel   |   | IndexedDB|   | 规则引擎  |   | 考勤结果  |   |Excel |
| 文件    |-->| 原始数据  |-->| 计算处理  |-->| 存储+查询 |-->|导出  |
| 上传    |   |          |   |          |   |          |   |      |
+---------+   +---------+   +----------+   +----------+   +------+
                  |                              |
                  v                              v
             排班表/假期                    模板编辑
             OA 申请                       预览/导出
```

详细数据流：

1. **导入阶段** (`import.html`)：
   - 用户拖拽 Excel -> `Excel.parseExcelFile()` 解析
   - `Excel.identifyFileType()` 自动识别类型
   - `Excel.parseRecords()` 标准化字段
   - 预览弹窗展示前10条数据
   - `Store.bulkPut()` 写入对应 IndexedDB 表
   - punch 类型额外调用 `Matcher.syncEmployees()` 同步员工表
   - schedule 类型按员工展开后再写入

2. **计算阶段** (`attendance.html`)：
   - 用户选择月份或自动检测有数据月份 -> `RulesEngine.calculateMonth()`
   - 按员工+日期遍历，结合排班表、假期、OA 数据
   - 计算迟到、早退、加班、旷工状态、实际工作时长
   - 容错规则豁免（迟到次数<=阈值 且 累计时长<=阈值）
   - 加班结余计算 `prevBalance + monthOvertime - 调休消耗`
   - 结果写入 `attendance_results` 表，每条含 `workHours`、`sourcePunchIds`、`sourceLeaveIds` 等来源ID

3. **导出阶段** (`export.html`)：
   - 用户编辑导出模板字段（19个可选字段，含工作时长）
   - Flat 模式：前端准备 records + template -> POST `/api/export/flat` -> Python openpyxl 生成 XLSX
   - 月报模式：前端读取 results + schedules + holidays -> POST `/api/export/calendar` -> Python 生成日历格式 XLSX（按部门分组、上午/下午双行、异常着色）

## 页面导航

```
index.html / login.html (登录页)
    |
    +--> attendance.html (考勤计算，登录后默认跳转)
    +--> import.html (数据导入)
    +--> export.html (导出中心)
    +--> settings.html (系统设置)
```

所有功能页通过 `Auth.requireAuth()` 守卫，未登录自动跳转回 `index.html`。侧边栏导航通过 `AppLayout.init()` 统一管理，含4个导航项和动态问候语。

## 设计系统 (bigsur.css)

v2.0 使用自定义 `shared/bigsur.css` 替代 Tailwind CDN，定义了中国风色彩 + macOS Big Sur 毛玻璃风格：

| 色彩 | CSS 变量 | 色值 | 用途 |
|------|---------|------|------|
| 宣纸白 | `--paper` | #FAF8F5 | 页面背景 |
| 墨色 | `--ink` | #2C2416 | 标题文字 |
| 朱砂红 | `--vermillion` | #C43D3D | 主色调（按钮/强调/错误） |
| 金色 | `--gold` | #C9A96E | 侧边栏图标/装饰 |
| 翠玉绿 | `--jade` | #2D7D46 | 正常状态/成功 |
| 靛蓝 | `--indigo` | #3B5998 | 请假状态/信息 |
| 檀木棕 | `--sandal` | #8B5E3C | 早退/出差状态 |

核心组件类：`.card`、`.btn-primary`（朱砂红）、`.btn-secondary`、`.badge-*`（6种状态）、`.tabs`、`.form-input`。侧边栏和登录卡片使用毛玻璃效果（`backdrop-filter: blur()`）。

## 9 种考勤状态

| 状态 | 含义 | 判定条件 |
|------|------|----------|
| normal | 正常出勤 | 有打卡记录且无异常（或被容错豁免） |
| rest | 休息日 | 排班表标记为休息 |
| abnormal | 迟到 | 签到时间晚于上班时间+阈值 |
| leave | 请假 | 有对应日期的 leave_records |
| travel | 出差 | 有对应日期的 travel_records |
| absent | 旷工 | 上班日无打卡无OA |
| overtime | 加班 | 休息日有打卡+加班OA |
| suspect_ot | 疑似加班 | 休息日有打卡但无加班OA |
| no_sign_in / no_sign_out | 未打卡 | 上班日只有签到无签退，或反之 |

## 数据库表 (IndexedDB)

共 13 张表，详见 [INTERFACES.md](./INTERFACES.md#数据库-schema)。

## 兼容桥接层 (init.js)

v2.0 新增 `shared/init.js` 兼容桥接层，为旧版 API 提供映射：

- `window.AttendanceDB` -> Proxy 代理 `punch_records`/`leave_records` 表（旧版名为 `punches`/`leaves`）
- `window.AttendanceRules` -> 适配旧的 `get()`/`save()` API 到新的 `settings` 表
- `window.AttendanceMatcher` -> 提供简化的规则引擎 `match()` 方法

## 与 v1.0 的主要变更

| 方面 | v1.0 (attendance/) | v2.0 (attendanceapp/) |
|------|-------|-------|
| CSS | Tailwind CDN + 内联样式 | bigsur.css 自定义设计系统 |
| 导航 | 顶部 `<a>` 链接 | 侧边栏 AppLayout + 移动端汉堡菜单 |
| 图标 | 无 | Lucide SVG 内嵌 |
| CDN 依赖 | Tailwind CSS CDN | 无（全部本地化） |
| 导出 | 浏览器端 SheetJS | Python openpyxl（带样式） |
| 设计风格 | 通用工具类 | macOS Big Sur 毛玻璃 + 中国风色彩 |
| 页面布局 | 单栏 `max-w-7xl` | 侧边栏 + 主内容区 `app-shell` |
| 登录页 | 顶部导航式 | 居中毛玻璃卡片 |

## 版本

当前版本：**v2.0**（Big Sur 重设计）。原始稳定版 v1.0.28 保留于 `attendance/` 目录。

业务逻辑核心（`auth.js`、`db.js`、`matcher.js`）与 v1.0 完全一致，`rules.js` 新增了调休抵扣、`missPerson` 支持、`workHours` 计算和 `sourceOvertimeIds` 字段。
