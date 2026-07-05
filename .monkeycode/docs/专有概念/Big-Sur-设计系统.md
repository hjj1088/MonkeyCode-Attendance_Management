# Big Sur 设计系统

## 概述

v2.0 使用自定义 `shared/bigsur.css`（472行）替代 v1.0 的 Tailwind CDN。设计系统融合了 macOS Big Sur 毛玻璃风格与中国传统色彩体系，定义了完整的 CSS 变量、组件类和响应式规则。

## 设计色彩

| 色彩名称 | CSS 变量 | 色值 | 用途 |
|---------|---------|------|------|
| 宣纸白 | `--paper` | #FAF8F5 | 页面背景色 |
| 墨色 | `--ink` | #2C2416 | 标题和正文文字 |
| 朱砂红 | `--vermillion` | #C43D3D | 主色调：主要按钮、链接、错误状态 |
| 金色 | `--gold` | #C9A96E | 侧边栏图标、装饰元素 |
| 翠玉绿 | `--jade` | #2D7D46 | 成功状态、正常出勤徽章 |
| 靛蓝 | `--indigo` | #3B5998 | 信息提示、请假状态、链接 |
| 檀木棕 | `--sandal` | #8B5E3C | 早退/出差状态、次要按钮描边 |
| 灰白 | `--card-bg` | #FFFFFF | 卡片背景 |
| 浅灰 | `--border` | #E8E4DD | 边框分割线 |
| 深灰 | `--text-secondary` | #6B5E4F | 次要文字 |

## 毛玻璃效果

两个关键位置使用 CSS `backdrop-filter` 实现毛玻璃：

**侧边栏** (`.sidebar`)：
```css
backdrop-filter: blur(40px) saturate(180%);
background: rgba(250, 248, 245, 0.75);
```

**登录卡片** (`.login-card`)：
```css
backdrop-filter: blur(24px) saturate(180%);
background: rgba(255, 255, 255, 0.7);
```

## 布局组件

### `.app-shell`
主布局容器，侧边栏 + 主内容区的双栏结构：
```css
.app-shell { display: flex; min-height: 100vh; }
.sidebar { width: 200px; flex-shrink: 0; }
.main-content { flex: 1; min-width: 0; }
```

### `.topbar`
顶部栏，含汉堡按钮和问候语。移动端（<=768px）显示汉堡按钮。

### `.page-container`
页面内容区，提供标准内边距。**无最大宽度限制**，内容撑满主区域。

## 卡片组件

```css
.card { background: var(--card-bg); border-radius: var(--radius-md); box-shadow: ...; padding: 20px; }
.card-header { ... }
.card-title { ... }
```

所有功能页统一使用 `.card` 作为内容容器。

## 按钮组件

| 类名 | 样式 | 用途 |
|------|------|------|
| `.btn` | 基础按钮（内边距、圆角、过渡） | 按钮基础 |
| `.btn-primary` | 朱砂红背景 + 白色文字 + 悬停加深 | 主要操作 |
| `.btn-secondary` | 檀木棕描边 + 透明背景 | 次要操作 |
| `.btn-ghost` | 无边框无背景 + 悬停灰色底 | 轻量操作 |
| `.btn-sm` | 小尺寸内边距 | 紧凑布局 |

## 表单组件

```css
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.form-input { padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); }
.form-select { /* 同 form-input 样式 */ }
```

## 表格组件

```css
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { padding: 10px 12px; font-weight: 600; text-align: left; border-bottom: 2px solid var(--border); }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
```

## 状态徽章

| 类名 | 颜色 | 状态 |
|------|------|------|
| `.badge-normal` | 翠玉绿 | 正常出勤 |
| `.badge-late` | 朱砂红 | 迟到 |
| `.badge-early` | 檀木棕 | 早退 |
| `.badge-miss` | 朱砂红 | 未打卡 |
| `.badge-leave` | 靛蓝 | 请假 |
| `.badge-travel` | 金色 | 出差 |
| `.badge-nosign` | 朱砂红 | 未打卡 |

## 标签页

```css
.tabs { display: flex; border-bottom: 2px solid var(--border); margin-bottom: 16px; }
.tab { padding: 8px 16px; cursor: pointer; border-bottom: 2px solid transparent; }
.tab.active { color: var(--vermillion); border-bottom-color: var(--vermillion); }
```

用于 attendance.html 的列表/日历视图切换和 settings.html 的 Tab 切换。

## 工具类

| 类名 | 样式 |
|------|------|
| `.flex` | `display: flex` |
| `.flex-between` | `display: flex; justify-content: space-between; align-items: center` |
| `.flex-center` | `display: flex; align-items: center; justify-content: center` |
| `.gap-sm` | `gap: 8px` |
| `.text-center` | `text-align: center` |
| `.hidden` | `display: none` |
| `.mt-sm` / `.mt-md` / `.mt-lg` | `margin-top: 8px / 16px / 24px` |
| `.mb-sm` / `.mb-md` | `margin-bottom: 8px / 16px` |

## flex-wrap 工具类

各页面内嵌 `<style>` 中定义 `.flex-wrap { flex-wrap: wrap }`，用于响应式换行。

## 响应式设计

```css
@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); }
  .hamburger-btn { display: flex; }
}
```

移动端侧边栏默认隐藏，通过汉堡按钮激活后从左侧滑入显示。叠加层覆盖主内容区用于关闭菜单。

## 与 v1.0 的区别

| 方面 | v1.0 | v2.0 |
|------|------|------|
| CSS 来源 | Tailwind CDN + 内联 style | bigsur.css 统一设计系统 |
| 网络依赖 | 依赖 tailwindcss.com CDN | 无（本地文件） |
| 颜色体系 | Tailwind 默认色板 | 中国风色彩（朱砂红/宣纸白/金色等） |
| 组件规范 | 内联工具类（无统一组件） | 预定义 .card/.btn/.badge 等组件 |
| 毛玻璃效果 | 无 | 侧边栏 + 登录卡片高斯大模糊 |
| 自定义门槛 | 较高（需理解 Tailwind 类名映射） | 较低（直接修改 CSS 变量） |
