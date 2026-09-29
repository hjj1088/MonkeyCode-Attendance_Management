// shared/auth.js
// 认证模块 - V3.1 旧版页面共用，登录入口统一为 V3.2 SPA /login

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
        const u = data.data.user || {};
        sessionStorage.setItem('user', JSON.stringify({ username: u.username, name: u.name, role: u.role, department: u.department }));
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
    window.location.href = '/login';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/login';
    }
  }
};
