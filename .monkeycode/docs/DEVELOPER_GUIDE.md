# 开发者指南

## 环境搭建

系统为前后端分离项目。前端为纯静态页面，后端为 Python 导出服务。

```bash
# 安装 Python 依赖
pip install openpyxl

# 启动服务（同时提供静态文件与导出 API）
python3 /workspace/attendanceapp/export_server.py
```

访问 `http://localhost:8000` 即可。服务默认监听 8000 端口，可通过 `PORT` 环境变量修改（如 `PORT=8001 python3 export_server.py`）。

## Docker 部署

项目支持容器化部署，通过 GitHub Actions 自动构建镜像并发布到 GitHub Container Registry：

```bash
# 拉取并运行
docker run -d -p 8000:8000 ghcr.io/hjj1088/monkeycode-attendance_management:latest

# 验证运行版本（确认是否为最新镜像）
curl http://localhost:8000/health

# 查看访问日志（含客户端 IP、请求路径、响应码）
docker logs <container_id>

# 本地构建
cd attendanceapp && docker build -t attendanceapp:latest .
```

CI/CD 配置位于 `.github/workflows/docker-publish.yml`，代码推送到 `main` 分支后自动触发。构建时注入 Git 提交 SHA 和时间戳到 `version.py`，启动后在日志中打印版本横幅，可通过 `/health` 端点确认当前运行的镜像版本。

Docker daemon 重启后若 curl 超时（TCP 握手成功但 HTTP 无响应），可能是 docker-proxy 进程卡死，执行 `systemctl restart docker && docker start <容器>` 即可修复。

## 项目结构约定

- **shared/ 目录**：所有 HTML 页面共享的业务逻辑模块和本地化第三方库
- **bigsur.css**：全局设计系统（472行），定义 CSS 变量、组件类和响应式规则，所有页面通过 `<link>` 引入
- **layout.js**：侧边栏导航框架，各页面通过 `<script>` 加载后自动初始化
- **认证守卫**：所有功能页必须在 `<script>` 顶部调用 `Auth.requireAuth()`
- **Vue Options API**：所有页面统一使用 `data()` + `methods` 风格（非 Composition API）
- **本地化依赖**：Vue.js、Dexie.js、SheetJS 均从 `shared/` 目录本地加载，无 CDN 依赖

## 新增数据导入类型

1. 在 `excel.js` 的 `identifyFileType()` 中添加新的 `typeRules` 条目
2. 在 `excel.js` 的 `_normalizeRecord()` 中添加字段映射
3. 在 `db.js` 的 `DB.version(1).stores()` 中添加新表
4. 在 `import.html` 的 `importAll()` 中添加入库逻辑
5. 在 `import.html` 的 `typeLabel()` 和 `typeClass()` 中添加标签/样式

## 修改考勤规则

主要修改文件为 `shared/rules.js`：

1. `getConfig()` - 获取和返回默认配置
2. `_timeToMinutes()` - 时间字符串转分钟
3. `_calcDeviation()` - 迟到/早退偏差计算
4. `_isWorkDay()` - 判断某天是否为上班日（排班表 + 假期）
5. `calculateMonth()` - 核心计算流程（含工作时长计算和来源记录ID）
6. `_updateCarryOver()` - 加班结余更新（含调休抵扣）

## CSS 定制

`shared/bigsur.css` 是全局设计系统。修改视觉外观时应优先修改其中的 CSS 变量：

```css
:root {
  --vermillion: #C43D3D;   /* 主色调 */
  --paper: #FAF8F5;        /* 页面背景 */
  --ink: #2C2416;          /* 标题文字 */
  --card-bg: #FFFFFF;      /* 卡片背景 */
  --border: #E8E4DD;       /* 边框颜色 */
}
```

各页面通过内嵌 `<style>` 处理页面特有的布局细节（如 export.html 的三列布局），不应在 `bigsur.css` 中添加页面特异样式。

## 调试方法

所有数据存储在浏览器 IndexedDB 中，通过 DevTools 查看：

1. 打开 Chrome DevTools -> Application -> IndexedDB -> AttendanceDB
2. 可查看各表数据、手动删除或修改
3. 清除全部数据：设置页 -> "重置数据库"

## 数据库版本升级

在 `db.js` 中通过 Dexie 的 `version(n).stores()` 处理：

```js
DB.version(2).stores({
  travel_records: '++id, applicant, startDate'
}).upgrade(async tx => {
  await tx.table('travel_records').clear();
});
```

版本号递增，`.upgrade()` 中执行迁移逻辑。旧表不在新版本 schema 中会自动保留（需手动 clean）。

## 已知限制

1. **Python 依赖**：导出功能需要 `openpyxl` 库，未安装时导出失败
2. **前端存储**：数据存在于浏览器 IndexedDB，换浏览器/清除缓存后丢失
3. **单用户存储**：IndexedDB 数据无法跨设备同步，不支持多用户协作
4. **Dexie 4.0.8 Bug**：`bulkPut` 会修改传入数组，必须 `JSON.parse(JSON.stringify())` 深拷贝后再写入
5. **Excel 时间格式**：数字格式时间（<1 的小数）自动转为 HH:MM，字符串时间保持原样
6. **SheetJS 社区版限制**：不支持单元格样式写入，导出样式由 Python openpyxl 实现
7. **登录账号**：仅支持内置 admin/admin123 单一账号
8. **跨页功能**：v2.0 的 bigsur.css 和 layout.js 与 v1.0 (attendance/) 页面不兼容，两套代码独立部署
9. **Docker 镜像**：构建于 `python:3.12-slim` 基础镜像，仅支持 amd64 架构，无 arm64 支持。旧版 Docker daemon 的 docker-proxy 偶发僵尸状态，需 `systemctl restart docker` 恢复
10. **条件格式兼容性**：迟到/早退条件格式依赖 Excel 原生公式（`TIMEVALUE`/`MOD(ROW())`），部分非 Microsoft 软件（如 WPS 旧版）可能不完全支持

---

# V3.1 开发指南（数据层迁移）

> 本节描述 v3.1（`attendance-v3/`）的运行、开发与排错方法。V3.1 是前后端分离架构：前端静态页面 + Python http.server + SQLite 后端。

## 环境搭建（V3.1）

```bash
# 安装 Python 依赖（openpyxl 用于导出）
pip install openpyxl

# 启动后端（端口 8001，同时提供 API + 静态文件托管）
python3 /workspace/attendance-v3/server/server.py
```

访问 `http://localhost:8001` 即可。首次启动时 `database.py` 自动建库建表并写入默认数据（attendance_config + 默认导出模板）。数据库文件位于 `server/data/attendance.db`。

**登录账号**：`admin` / `admin123`（后端校验，非前端硬编码）。

## V3.1 架构速览

- **前端** `attendance-v3/client/`：与 V2.0 逐文件对应，`shared/db.js` 替换为 `shared/api-store.js`
- **后端** `attendance-v3/server/server.py`：HTTP 服务 + JWT 认证 + 通用 store CRUD + 静态托管
- **数据层** `attendance-v3/server/database.py`：SQLite 13 张表（字段 camelCase 与 V2.0 IndexedDB 一致）
- **导出** `attendance-v3/server/handlers/export.py`：V2.0 `export_server.py` 逻辑移植

## 数据访问约定（V3.1）

所有前端数据操作经 `Store` 对象（`shared/api-store.js`），内部 `fetch` 调用后端 REST API：

```js
await Store.getAll('punch_records');                    // GET /api/store/punch_records
await Store.bulkPut('punch_records', records);          // POST /api/store/punch_records/bulk
await Store.getByIndex('schedules', 'employeeNo', '001'); // GET ?index=employeeNo&value=001
await Store.getByKey('settings', 'attendance_config');   // GET /api/store/settings/attendance_config
await Store.clearTable('attendance_results');            // DELETE /api/store/attendance_results
await Store.resetAllData();                              // POST /api/store/reset
```

认证 token 存 `sessionStorage.token`，`api-store.js` 的 `_request()` 自动附加 `Authorization: Bearer` 头；401 时自动登出跳转 `index.html`。

## 新增数据导入类型（V3.1）

步骤与 V2.0 相同（`excel.js` 的 `identifyFileType()` / `_normalizeRecord()`），仅数据写入由 `Store.bulkPut` 走 REST API。V3.1 无需在 `db.js` 中建表——表结构在 `server/database.py` 的 DDL 中维护。

## 修改数据库结构（V3.1）

1. 编辑 `server/database.py` 的 `init_db()` DDL，新增/修改表或字段
2. 若字段是 JSON 对象（如 `workDays`），确认 `server.py` 的 `json_serialize` 覆盖序列化
3. 删除旧 `server/data/attendance.db` 重建（或手动 `ALTER TABLE`）
4. 重启服务

## 调试方法（V3.1）

- **查看后端日志**：`server.py` 输出到 stdout，前台运行时直接可见
- **查看 SQLite 数据**：`sqlite3 server/data/attendance.db '.tables'` 或直接查询
- **测试 API**：`curl -X POST http://localhost:8001/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'` 获取 token 后带 Bearer 访问
- **重置数据**：设置页"重置数据库"按钮或 `POST /api/store/reset`

## V3.1 已知限制与遗留问题

1. **login.html 不可用**：`login.html` 仍按 V2.0 同步风格调用异步 `Auth.login()`（未 await），登录报错；实际入口应使用 `index.html`
2. **未接入的 handler**：`handlers/` 下 auth/attendance/rules/system/users/migrate 及 `middleware.py` 未挂载到任何路由，依赖的 `users`/`operation_logs` 表与 snake_case 字段在当前 schema 中不存在
3. **测试不通过**：`tests/` 部分测试与当前实现不符（`init_tables()` vs `init_db()`、15 表 vs 13 表）
4. **跨设备同步**：SQLite 单文件存储，多用户同时写入依赖 WAL 模式（已启用），但无锁/无并发控制

## V3.1 与 V2.0 并存部署

```bash
# V2.0（端口 8000，IndexedDB）
python3 /workspace/attendanceapp/export_server.py

# V3.1（端口 8001，SQLite + REST API）
python3 /workspace/attendance-v3/server/server.py
```

两套代码独立部署、数据相互隔离（V2.0 数据在浏览器 IndexedDB，V3.1 数据在后端 SQLite），可并行运行对比验证。
