# 系统架构

## 概述

考勤管理系统是一个**前后端分离**的考勤数据处理工具。前端运行在浏览器端负责数据导入、规则计算、查询浏览；后端由 Python 导出服务 (`export_server.py`) 负责生成带样式的 XLSX 报表。系统处理企业考勤数据的完整生命周期：导入 Excel → 规则计算 → 查询浏览 → 导出报表。

## 技术栈

| 层级 | 技术 | 版本/方式 | 用途 |
|------|------|-----------|------|
| UI 框架 | Vue.js | 3.x (CDN) | 响应式界面，组件化开发 |
| CSS 框架 | Tailwind CSS | 3.x (CDN) | 原子化样式 |
| 数据存储 | Dexie.js | 4.0.8 (本地文件) | IndexedDB 封装，SQL-like 查询 |
| Excel 导入 | SheetJS (xlsx) | 0.20.3 (本地文件) | Excel 解析、单元格颜色读取 |
| Excel 导出 | Python openpyxl | 3.1.5 (pip) | XLSX 生成，支持单元格样式（字体颜色、填充色） |
| 后端服务 | Python http.server | 标准库 | HTTP API + 静态文件服务 |
| 认证 | localStorage | 浏览器原生 | 简单的用户名/密码认证 |
| 部署 | Python 单进程 | 标准库 | `export_server.py` 同时提供静态文件与 API 端点 |

前端依赖通过 CDN 或本地 `lib/` 目录加载，无需 npm/pnpm 构建步骤。Python 依赖 `openpyxl` 需通过 `pip install openpyxl` 安装。

## 项目结构

```
attendance/
├── index.html            # 登录页 + 功能导航首页
├── import.html           # 数据导入页（拖拽上传 + 类型识别 + 入库）
├── attendance.html       # 考勤计算页（列表/日历视图 + 详情弹窗）
├── export.html           # 导出中心（模板编辑 + Flat/月报导出）
├── settings.html         # 考勤规则设置（上下班时间、容错、假期管理）
├── export_server.py      # Python 导出服务（HTTP API + 静态文件，openpyxl 生成 XLSX）
├── lib/                  # 第三方库（本地文件）
│   ├── vue.global.prod.js
│   ├── dexie.min.js
│   └── xlsx.full.min.js
└── shared/               # 共享业务模块
    ├── auth.js           # 认证模块
    ├── db.js             # 数据库模块
    ├── rules.js          # 规则引擎模块
    ├── excel.js          # Excel 处理模块 (SheetJS 导入 + API 导出)
    └── matcher.js        # 数据匹配模块
```

## 模块依赖关系

```
index.html         ← 认证入口，导航到功能页
    |
    +-- auth.js     ← 所有页面引用

import.html        ← 数据入口
    +-- db.js
    +-- excel.js    ← 解析 Excel
    +-- matcher.js  ← 员工匹配

attendance.html    ← 计算核心
    +-- db.js
    +-- rules.js    ← 规则引擎

export.html        ← 导出出口
    +-- db.js
    +-- excel.js    ← 准备数据 → HTTP API

export_server.py   ← Python 导出服务
    +-- openpyxl   ← XLSX 生成（字体颜色、填充色、边框、合并单元格）

settings.html      ← 配置管理
    +-- db.js
```

模块间调用关系：
- `auth.js` 不依赖其他模块
- `db.js` 不依赖其他模块
- `excel.js` 依赖 `db.js` (导出时需要查询 DB)
- `matcher.js` 依赖 `db.js`
- `rules.js` 依赖 `db.js`

## 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据生命周期                               │
├─────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────┤
│ Excel   │   │ IndexedDB│   │ 规则引擎  │   │ 考勤结果  │   │Excel │
│ 文件    │──>│ 原始数据  │──>│ 计算处理  │──>│ 存储+查询 │──>│导出  │
│ 上传    │   │          │   │          │   │          │   │      │
└─────────┘   └─────────┘   └──────────┘   └──────────┘   └──────┘
                  │                              │
                  v                              v
             排班表/假期                    模板编辑
             OA 申请                       预览/导出
```

详细数据流：

1. **导入阶段** (`import.html`)：
   - 用户拖拽 Excel → `Excel.parseExcelFile()` 解析
   - `Excel.identifyFileType()` 自动识别类型
   - `Excel.parseRecords()` 标准化字段
   - `Store.bulkPut()` 写入对应 IndexedDB 表

2. **计算阶段** (`attendance.html`)：
   - 用户选择月份 → `RulesEngine.calculateMonth()`
   - 按员工+日期遍历，结合排班表、假期、OA 数据
   - 计算迟到、早退、加班、旷工状态
   - 容错规则豁免（迟到次数≤阈值 且 累计时长≤阈值）
   - 加班结余计算 `prevBalance + monthOvertime - 调休消耗`
   - 结果写入 `attendance_results` 表

3. **导出阶段** (`export.html`)：
   - 用户编辑导出模板字段
   - Flat 模式：前端准备 records + template → POST `/api/export/flat` → Python openpyxl 生成 XLSX
   - 月报模式：前端读取 results + schedules + holidays → POST `/api/export/calendar` → Python 生成日历格式 XLSX（含假期名称、单元格样式）

## 页面导航

```
index.html (登录页)
    |
    +--> import.html (数据导入)
    +--> attendance.html (考勤计算)
    +--> export.html (导出中心)
    +--> settings.html (考勤规则设置)
```

所有功能页通过 `Auth.requireAuth()` 守卫，未登录自动跳转回 `index.html`。

## 6 种考勤状态

| 状态 | CSS 类 | 颜色 | 判定条件 |
|------|--------|------|----------|
| normal | status-normal | 绿色 | 正常出勤或容错豁免 |
| rest | status-rest | 灰色 | 排班休息日 |
| abnormal | status-abnormal | 黄色 | 迟到 (超出阈值) |
| leave | status-leave | 蓝色 | 请假 (有 leave_records) |
| travel | status-travel | 紫色 | 出差 (有 travel_records) |
| absent | status-absent | 红色 | 旷工 (上班日无打卡无OA) |

## 数据库表 (IndexedDB)

共 13 张表，详见 [INTERFACES.md](./INTERFACES.md#数据库-schema)。

## 版本与缓存

文件版本号通过 URL 查询参数 `?v=1.0.10` 控制浏览器缓存刷新。各文件版本号已按依赖关系同步（修改 `rules.js` 时连带提升 `attendance.html` 的版本号）。

当前版本：**v1.0.25**
