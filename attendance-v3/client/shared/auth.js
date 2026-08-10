// shared/auth.js V3.1
// 认证模块 - 调用后端 JWT API

const AUTH_KEY = 'attendance_auth';

const Auth = {
  isLoggedIn() {
    return !!sessionStorage.getItem('token');
  },

  async login(username, password) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.code === 0 && data.data && data.data.token) {
        sessionStorage.setItem('token', data.data.token);
        sessionStorage.setItem('user', JSON.stringify({ username: data.data.username }));
        return { success: true };
      }
      return { success: false, message: data.message || '登录失败' };
    } catch (e) {
      return { success: false, message: '网络错误，请检查后端服务' };
    }
  },

  logout() {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    window.location.href = 'index.html';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = 'index.html';
    }
  }
};
