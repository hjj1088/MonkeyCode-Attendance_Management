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
