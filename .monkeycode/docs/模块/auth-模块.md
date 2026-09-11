# auth 模块

**文件（V2.0）**：`shared/auth.js`  
**文件（V3.2）**：`attendance-v3/client/src/shared/auth.js`

## 职能

V2.0：浏览器端 `localStorage` 登录状态。  
V3.2：调用后端 JWT，`sessionStorage` 存 `token` + `user`。

## V3.2 API

| 方法 | 说明 |
|------|------|
| `isLoggedIn()` | `sessionStorage.token` 是否存在 |
| `getUser()` / `getRole()` / `getUsername()` / `getDepartment()` | 读 `sessionStorage.user` |
| `login(username, password)` | `POST /api/auth/login`，成功写 token/user，返回 `{success, needChangePassword}` |
| `logout()` | 清 session，跳 `login` |

页面守卫在 `router/index.js` 的 `beforeEach`，不再用 `Auth.requireAuth()`。

无 token：`defaultPath()` → `/login`。`admin` 默认密码触发 `need_change_password` → `/setup`。

后端锁定：连错 5 次锁 24 小时（`locked_until`）；`last_failed_login` 超 1 天清零。见 [V3.2-多角色与审核工作流](../专有概念/V3.2-多角色与审核工作流.md)。

## V2.0 API（对照）

`Auth.isLoggedIn()` 检查 `localStorage.attendance_auth`。`Auth.login` 前端硬编码凭据。`Auth.requireAuth()` 未登录跳 `index.html`。

## 安全说明（V3.2）

- 密码 bcrypt 存 SQLite，JWT HS256 24h
- token 在 `sessionStorage`，关标签失效
- 角色以后端 token payload 为准，前端 `meta.roles` 只拦导航
