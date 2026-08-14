import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, noLayout: true, title: '登录' },
  },
  {
    path: '/setup',
    name: 'setup',
    component: () => import('../views/SetupWizardView.vue'),
    meta: { noLayout: true, title: '设置管理员密码' },
  },
  { path: '/', redirect: defaultPath },
  {
    path: '/my',
    name: 'my',
    component: () => import('../views/MyAttendanceView.vue'),
    meta: { title: '我的考勤' },
  },
  {
    path: '/import',
    name: 'import',
    component: () => import('../views/ImportView.vue'),
    meta: { roles: ['hradmin'], title: '数据导入' },
  },
  {
    path: '/attendance',
    name: 'attendance',
    component: () => import('../views/AttendanceView.vue'),
    meta: { roles: ['hradmin', 'deptadmin'], title: '考勤计算' },
  },
  {
    path: '/export',
    name: 'export',
    component: () => import('../views/ExportView.vue'),
    meta: { roles: ['hradmin'], title: '导出中心' },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('../views/UserManageView.vue'),
    meta: { roles: ['hradmin'], title: '用户管理' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { roles: ['hradmin'], title: '系统设置' },
  },
  {
    path: '/settings/rules',
    name: 'rules',
    component: () => import('../views/RulesSettingsView.vue'),
    meta: { roles: ['hradmin'], title: '考勤规则' },
  },
];

function getUser() {
  try {
    return JSON.parse(sessionStorage.getItem('user') || 'null');
  } catch (e) {
    return null;
  }
}

function defaultPath() {
  const user = getUser();
  if (user && user.role === 'employee') return { path: '/my' };
  return { path: '/attendance' };
}

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const token = sessionStorage.getItem('token');
  const user = getUser();
  const needChange = sessionStorage.getItem('need_change_password') === '1';

  if (!to.meta.public && !token) {
    return { path: '/login' };
  }
  if (to.path === '/login' && token) {
    return defaultPath();
  }
  if (token && needChange && to.path !== '/setup' && !to.meta.public) {
    return { path: '/setup' };
  }
  if (to.meta.roles && user && !to.meta.roles.includes(user.role)) {
    return defaultPath();
  }
  if (to.path === '/setup' && !token) {
    return { path: '/login' };
  }
  return true;
});

router.afterEach((to) => {
  document.title = (to.meta.title ? to.meta.title + ' - ' : '') + '考勤管理系统';
});

export default router;
