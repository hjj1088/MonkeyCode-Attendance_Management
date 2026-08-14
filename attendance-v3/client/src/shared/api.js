// shared/api.js
// fetch 封装 - Bearer token、401 清 token 跳登录

const API_BASE = '/api';

function _redirectToLogin() {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

export async function apiRequest(path, options = {}) {
  const token = sessionStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...(options.headers || {}),
  };

  const fetchOptions = { ...options, headers };

  const res = await fetch(API_BASE + path, fetchOptions);

  if (res.status === 401) {
    _redirectToLogin();
    throw new Error('Unauthorized');
  }

  const contentType = res.headers.get('Content-Type') || '';
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || '请求失败 (' + res.status + ')');
  }

  if (contentType.includes('application/json')) {
    const body = await res.json();
    if (body.code !== 0) {
      throw new Error(body.message || 'API 错误');
    }
    return body.data;
  }

  return await res.text();
}

export { _redirectToLogin };
