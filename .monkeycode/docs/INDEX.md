# 考勤管理系统 - 文档索引

本目录包含考勤管理系统的完整技术文档。

## 文档结构

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构：技术栈、模块关系、数据流、设计系统、v1.0 vs v2.0 vs v3.1 对比 |
| [INTERFACES.md](./INTERFACES.md) | 接口文档：IndexedDB 数据库 Schema、REST API、所有模块 API、文件类型识别规则 |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | 开发者指南：环境搭建、CSS 定制、调试方法、常见问题 |

## 专有概念

| 文档 | 说明 |
|------|------|
| [专有概念/考勤规则引擎.md](./专有概念/考勤规则引擎.md) | 考勤判定逻辑：9种状态体系、容错规则、结余计算、工作时长计算 |
| [专有概念/数据文件类型与格式.md](./专有概念/数据文件类型与格式.md) | Excel 导入格式：打卡/请假/加班/出差/漏打卡/排班的字段与识别规则 |
| [专有概念/排班与假期管理.md](./专有概念/排班与假期管理.md) | 排班导入解析、假期设置、isWorkDay 判定逻辑 |
| [专有概念/导出模板系统.md](./专有概念/导出模板系统.md) | 导出设计：19种可选字段、Flat/日历两种模式、Python openpyxl 样式规则 |
| [专有概念/Big-Sur-设计系统.md](./专有概念/Big-Sur-设计系统.md) *(v2.0)* | 设计系统：中国风色彩、毛玻璃效果、组件类、响应式规则 |
| [专有概念/V3.1-数据层迁移.md](./专有概念/V3.1-数据层迁移.md) *(v3.1)* | V3.1 数据层迁移：IndexedDB → SQLite + REST API 的完整方案与差异对照 |

## 模块

| 文档 | 说明 |
|------|------|
| [模块/db-模块.md](./模块/db-模块.md) | 数据库层（V2.0）：13张表 Schema、Store CRUD、自动恢复、初始化 |
| [模块/rules-模块.md](./模块/rules-模块.md) | 规则引擎：考勤计算、迟到早退判定、容错豁免、结余管理、工作时长 |
| [模块/excel-模块.md](./模块/excel-模块.md) | Excel 处理：文件解析、类型识别、导出 API 调用（Python 后端） |
| [模块/matcher-模块.md](./模块/matcher-模块.md) | 数据匹配：员工映射、OA 到打卡关联、跨表匹配 |
| [模块/auth-模块.md](./模块/auth-模块.md) | 认证系统：localStorage 登录、页面守卫 |
| [模块/export-server-模块.md](./模块/export-server-模块.md) | 导出服务（V2.0）：HTTP 导出 API、XLSX 生成、CORS 支持 |
| [模块/layout-模块.md](./模块/layout-模块.md) *(v2.0)* | 侧边栏导航：AppLayout、移动端汉堡菜单、问候语 |
| [模块/init-模块.md](./模块/init-模块.md) *(v2.0)* | 兼容桥接层：AttendanceDB/AttendanceRules/AttendanceMatcher 向后兼容 |
| [模块/V3.1-后端服务-模块.md](./模块/V3.1-后端服务-模块.md) *(v3.1)* | V3.1 后端服务：server.py 路由、SQLite 数据层、JWT 认证、导出处理器 |
| [模块/V3.1-api-store-模块.md](./模块/V3.1-api-store-模块.md) *(v3.1)* | V3.1 前端数据访问层：api-store.js 替代 db.js，Store 接口保持兼容 |

## 快速导航

- **新用户入门**：先读 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解系统全貌
- **了解 V3.1 架构**：参考 [专有概念/V3.1-数据层迁移.md](./专有概念/V3.1-数据层迁移.md)
- **了解视觉设计**：参考 [专有概念/Big-Sur-设计系统.md](./专有概念/Big-Sur-设计系统.md)
- **修改考勤规则**：参考 [专有概念/考勤规则引擎.md](./专有概念/考勤规则引擎.md)
- **新增数据导入类型**：参考 [专有概念/数据文件类型与格式.md](./专有概念/数据文件类型与格式.md)
- **自定义 CSS 样式**：参考 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) 中的 CSS 定制章节
- **修改数据库结构**：参考 [模块/db-模块.md](./模块/db-模块.md)（V2.0）或 [模块/V3.1-后端服务-模块.md](./模块/V3.1-后端服务-模块.md)（V3.1）

## 版本

当前版本：**v3.1**（SQLite + REST API 数据层迁移，前端代码与 V2.0 保持一致）。标注 `*(v2.0)*` 的文档为 v2.0 新增内容，标注 `*(v3.1)*` 的文档为 v3.1 新增内容。
