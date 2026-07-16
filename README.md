# MonkeyCode 考勤管理系统

前后端分离的企业考勤数据处理工具，支持 Excel 导入、自动规则计算、查询浏览、带样式 XLSX 导出。前端使用 Vue.js 3 + Dexie.js（浏览器端 IndexedDB），后端使用 Python openpyxl 生成带条件格式的 Excel 报表。

## 功能

- **Excel 导入**：拖拽上传打卡记录、请假/出差/加班 OA、排班表，自动识别文件类型并标准化字段
- **规则引擎**：9 种考勤状态判定（正常/迟到/早退/请假/出差/加班/疑似加班/缺勤/未打卡），支持容错豁免、加班结余计算、实际工作时长
- **考勤查询**：列表/日历双视图，部门/状态/姓名多维度筛选，详情弹窗追溯打卡与 OA 数据
- **导出中心**：平铺列表 + 日历月报两种格式，19 种可选字段模板，迟到/早退条件格式自动标红
- **系统设置**：考勤规则配置、容错规则、假期管理、数据库重置/导出

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue.js 3.x (Options API) | 本地文件，无构建步骤 |
| CSS | bigsur.css | macOS Big Sur + 中国风，无 CDN 依赖 |
| 数据库 | Dexie.js 4.0.8 | IndexedDB 封装，13 张表 |
| Excel 导入 | SheetJS 0.20.3 | 解析 + 单元格颜色读取 |
| Excel 导出 | Python openpyxl 3.1.5 | 样式/合并/条件格式 |
| 后端服务 | Python http.server | 单进程，静态文件 + API |
| 部署 | Docker + GitHub Actions | 自动构建推送到 GHCR |

所有前端依赖本地化存放于 `shared/` 目录，无需 `npm install`。

## 快速开始

```bash
# 安装 Python 依赖
pip install openpyxl

# 启动服务
python3 attendanceapp/export_server.py
```

访问 `http://localhost:8000`，使用 `admin` / `admin123` 登录。

### Docker 部署

```bash
docker run -d -p 8000:8000 ghcr.io/hjj1088/monkeycode-attendance_management:latest
```

## 项目结构

```
attendanceapp/
├── index.html              # 登录页
├── attendance.html         # 考勤计算（列表/日历视图 + 详情弹窗）
├── import.html             # 数据导入（拖拽上传 + 自动识别 + 预览）
├── export.html             # 导出中心（模板管理 + 平铺/月报导出）
├── settings.html           # 系统设置（考勤规则 + 假期管理）
├── export_server.py        # Python 导出服务（API + 静态文件）
├── requirements.txt        # Python 依赖
├── Dockerfile              # 容器化部署
└── shared/                 # 共享模块
    ├── bigsur.css          # 设计系统
    ├── layout.js           # 侧边栏导航框架
    ├── init.js             # 模块兼容桥接层
    ├── auth.js             # 认证模块
    ├── db.js               # 数据库模块（Dexie.js 13 张表）
    ├── rules.js            # 规则引擎
    ├── excel.js            # Excel 处理（导入 + API 导出）
    ├── matcher.js          # 数据匹配
    ├── dexie.min.js        # IndexedDB 封装
    ├── vue.min.js          # Vue 3 运行时
    └── xlsx.min.js         # SheetJS
```

## 数据流

```
Excel 上传 -> IndexedDB 原始数据 -> 规则引擎计算 -> 考勤结果 -> XLSX 导出
                  |                         |
             排班/假期/OA               模板编辑/预览
```

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/export/flat` | POST | 平铺报表导出 |
| `/api/export/calendar` | POST | 日历月报导出 |

## 文档

完整技术文档：`.monkeycode/docs/`

- [ARCHITECTURE.md](.monkeycode/docs/ARCHITECTURE.md) — 系统架构
- [INTERFACES.md](.monkeycode/docs/INTERFACES.md) — 接口/数据库 Schema
- [DEVELOPER_GUIDE.md](.monkeycode/docs/DEVELOPER_GUIDE.md) — 开发者指南

## License

MIT
