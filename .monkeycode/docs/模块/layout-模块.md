# layout 模块 (v2.0 新增)

**文件**：`shared/layout.js`

## 职能

macOS Big Sur 风格侧边栏导航框架。管理 4 个导航项、移动端响应式菜单和动态问候语。

## 导出

`AppLayout` 对象（挂载到 `window.AppLayout`）。

## API

| 方法 | 说明 |
|------|------|
| `init()` | 初始化导航栏和问候语，自动检测当前页面高亮对应导航项 |
| `toggleMenu()` | 移动端侧边栏开关（显示/隐藏） |
| `closeMenu()` | 关闭移动端侧边栏 |

## 内部方法

### `_detectPage()`

根据 `window.location.pathname` 检测当前页面，返回对应的导航项 index。匹配规则：
- `import.html` -> 数据导入 (index 0)
- `attendance.html` -> 考勤计算 (index 1)
- `export.html` -> 导出中心 (index 2)
- `settings.html` -> 系统设置 (index 3)

### `_updateGreeting()`

根据当前小时数生成问候语：
- 6:00-11:59 -> "上午好"
- 12:00-17:59 -> "下午好"
- 18:00-23:59 + 0:00-5:59 -> "晚上好"

问候语写入 `#header-greeting` 元素。

## 导航结构

```
sidebar-header (Logo + 品牌名称)
    |
nav#sidebar-nav
    ├── 数据导入 (upload 图标) -> import.html
    ├── 考勤计算 (clock 图标)  -> attendance.html
    ├── 导出中心 (download 图标) -> export.html
    └── 系统设置 (settings 图标) -> settings.html
    |
sidebar-footer (退出登录按钮)
```

每个导航项由 `layout.js` 动态创建 DOM 元素，包含 SVG 图标和文字标签。当前页面高亮使用 `.nav-item.active` 样式。

## 移动端响应式

宽度 <= 768px 时：
- 侧边栏通过 `transform: translateX(-100%)` 隐藏
- 顶部栏显示 `.hamburger-btn` 汉堡按钮
- 点击汉堡按钮或调用 `toggleMenu()` 显示侧边栏（`transform: translateX(0)`）
- 侧边栏叠加层 `.sidebar-overlay` 覆盖主内容区，点击关闭菜单

## 依赖

`auth.js` — 读取当前登录用户信息。

## 使用方式

每个功能页在 `<script>` 中加载 `layout.js` 后自动调用 `AppLayout.init()`：

```html
<script src="shared/layout.js"></script>
```

HTML 结构必须包含以下元素：
- `<aside id="sidebar">` — 侧边栏容器
- `<nav id="sidebar-nav">` — 导航项挂载点
- `<span id="header-greeting">` — 问候语显示位置
- `<div id="sidebar-overlay">` — 移动端叠加层（含 `onclick="AppLayout.closeMenu()"`）
- `<button class="hamburger-btn" onclick="AppLayout.toggleMenu()">` — 汉堡按钮
