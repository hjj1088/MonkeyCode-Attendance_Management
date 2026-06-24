# auth 模块

**文件**：`shared/auth.js`

## 职能

简单的浏览器端认证系统，通过 `localStorage` 实现登录状态持久化。

## API

### `Auth.isLoggedIn()`

检查 localStorage 中 `attendance_auth` 键是否为 `'true'`。

### `Auth.login(username, password)`

验证账号密码。默认凭据：`admin / admin123`。

返回 `{ success: true }` 或 `{ success: false, message: '账号或密码错误' }`。

### `Auth.logout()`

清除 localStorage 中的认证状态，跳转回 `index.html` 登录页。

### `Auth.requireAuth()`

页面守卫函数。若未登录则 `window.location.href = 'index.html'`。

## 使用方式

所有功能页在 `<script>` 顶部调用：

```js
Auth.requireAuth();
```

## 安全说明

这仅是一个前端轻量级认证，不适用于需要强安全认证的场景：
- 凭据以明文存储在前端代码中
- 认证状态存储在浏览器 localStorage
- 无 token、session、加密机制
- 清除浏览器数据可绕过认证
