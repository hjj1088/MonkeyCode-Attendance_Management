# 开发者指南

## 环境搭建

系统为纯前端项目，无需 Node.js 构建环境。

```bash
# 启动本地开发服务器
python3 -m http.server 8000 --directory /workspace/attendance
```

访问 `http://localhost:8000` 即可。

## 项目结构约定

- **shared/ 目录**：所有 HTML 页面共享的业务逻辑模块
- **lib/ 目录**：第三方库本地文件（避免 CDN 不稳定）
- **认证守卫**：所有功能页必须在 `<script>` 顶部调用 `Auth.requireAuth()`
- **版本号**：每个 script 标签通过 `?v=` 参数控制缓存刷新

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
5. `calculateMonth()` - 核心计算流程
6. `_updateCarryOver()` - 加班结余更新

修改规则后必须提升 `?v=` 版本号并硬刷新浏览器。

## 版本号管理

修改文件后，需提升该文件所引用 script 标签的 `?v=` 版本号：

- `rules.js` 修改 → 提升 `attendance.html` 版本号
- `excel.js` 修改 → 提升 `import.html` + `export.html` 版本号
- `db.js` 修改 → 提升所有引用页面的版本号
- `matcher.js` 修改 → 提升 `import.html` 版本号

## 调试方法

所有数据存储在浏览器 IndexedDB 中，通过 DevTools 查看：

1. 打开 Chrome DevTools → Application → IndexedDB → AttendanceDB
2. 可查看各表数据、手动删除或修改
3. 清除全部数据：设置页 → "重置数据库"

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

1. **仅单文件部署**：所有 HTML 在同一目录，通过 `python3 -m http.server` 服务
2. **前端存储**：数据存在于浏览器 IndexedDB，换浏览器/清除缓存后丢失
3. **无后端**：不支持多用户协作、数据同步
4. **Dexie 4.0.8 Bug**：`bulkPut` 会修改传入数组，必须 `JSON.parse(JSON.stringify())` 深拷贝后再写入
5. **CDN 依赖**：Tailwind CSS 通过 CDN 加载，无网络时样式失效
6. **Excel 时间格式**：数字格式时间（<1 的小数）自动转为 HH:MM，字符串时间保持原样
