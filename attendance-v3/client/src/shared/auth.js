// shared/auth.js
// 认证模块 - 调用后端 JWT API，sessionStorage 保存 token + 完整 user

import { _redirectToLogin } from './api';

const Auth = {
  isLoggedIn() {
    return !!sessionStorage.getItem('token');
  },

  getUser() {
    try {
      return JSON.parse(sessionStorage.getItem('user') || 'null');
    } catch (e) {
      return null;
    }
  },

  getRole() {
    const user = this.getUser();
    return user ? user.role : '';
  },

  getUsername() {
    const user = this.getUser();
    return user ? user.username : '';
  },

  getDepartment() {
    const user = this.getUser();
    return user ? user.department : '';
  },

  async login(username, password) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.code === 0 && data.data && data.data.token) {
        sessionStorage.setItem('token', data.data.token);
        sessionStorage.setItem('user', JSON.stringify(data.data.user || { username: data.data.username }));
        return { success: true, needChangePassword: !!data.data.need_change_password };
      }
      return { success: false, message: data.message || '登录失败' };
    } catch (e) {
      return { success: false, message: '网络错误，请检查后端服务' };
    }
  },

  logout() {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    _redirectToLogin();
  },
};

export default Auth;
