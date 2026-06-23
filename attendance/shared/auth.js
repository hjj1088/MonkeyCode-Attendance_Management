// shared/auth.js
// 考勤系统认证模块 - localStorage 形式登录

const AUTH_KEY = 'attendance_auth';
const DEFAULT_CREDENTIALS = { username: 'admin', password: 'admin123' };

const Auth = {
  isLoggedIn() {
    return localStorage.getItem(AUTH_KEY) === 'true';
  },

  login(username, password) {
    if (username === DEFAULT_CREDENTIALS.username && password === DEFAULT_CREDENTIALS.password) {
      localStorage.setItem(AUTH_KEY, 'true');
      return { success: true };
    }
    return { success: false, message: '账号或密码错误' };
  },

  logout() {
    localStorage.removeItem(AUTH_KEY);
    window.location.href = 'index.html';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = 'index.html';
    }
  }
};
