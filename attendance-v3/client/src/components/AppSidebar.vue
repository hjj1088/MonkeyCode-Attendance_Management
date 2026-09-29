<template>
  <aside id="sidebar" class="sidebar" :class="{ open }">
    <div class="sidebar-header">
      <div class="sidebar-logo" aria-hidden="true">勤</div>
      <div class="sidebar-brand-wrap">
        <div class="sidebar-brand">考勤系统</div>
        <div class="sidebar-sub">Attendance V3.2</div>
      </div>
    </div>
    <nav id="sidebar-nav">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item" :class="{ active: isActive(item.to) }" @click="$emit('navigate')">
        <div class="nav-icon" v-html="item.icon"></div>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="sidebar-avatar">{{ avatarChar }}</div>
        <div class="sidebar-user-meta">
          <div class="sidebar-user-name">{{ displayName }}</div>
          <div class="sidebar-user-account">{{ accountText }}</div>
        </div>
      </div>
      <button class="logout-btn" @click="handleLogout">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
        退出登录
      </button>
      <div class="sidebar-version">{{ versionText }}</div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Auth from '../shared/auth';
import { apiRequest } from '../shared/api';

defineProps({ open: { type: Boolean, default: false } });
defineEmits(['navigate']);

const route = useRoute();
const router = useRouter();
const versionText = ref('V3.2.0');

onMounted(async () => {
  try {
    const v = await apiRequest('/system/version');
    if (v && v.app_version) {
      const patch = String(v.app_version).split('.')[2] || '';
      versionText.value = (v.version_name || '') + (patch ? '.' + patch : '');
    }
  } catch (e) { /* 保持默认版本号 */ }
});

const ICONS = {
  upload: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><g class="icon-arrow"><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></g></svg>',
  clock: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><g class="icon-hour"><line x1="12" y1="12" x2="12" y2="6"/></g><g class="icon-minute"><line x1="12" y1="12" x2="16" y2="12"/></g></svg>',
  download: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><g class="icon-arrow-down"><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></g></svg>',
  settings: '<svg class="icon-gear" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
  users: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><g class="icon-side"><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></g></svg>',
  shield: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><g class="icon-check"><path d="m9 12 2 2 4-4"/></g></svg>',
  user: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g class="icon-head"><circle cx="12" cy="8" r="5"/></g><g class="icon-body"><path d="M20 21a8 8 0 0 0-16 0"/></g></svg>',
};

const ALL_NAV = [
  { to: '/import', label: '数据导入', icon: ICONS.upload, roles: ['superadmin', 'hradmin'] },
  { to: '/attendance', label: '考勤计算', icon: ICONS.clock, roles: ['superadmin', 'hradmin', 'deptadmin'] },
  { to: '/my', label: '我的考勤', icon: ICONS.user, roles: ['superadmin', 'employee', 'deptadmin'] },
  { to: '/export', label: '导出中心', icon: ICONS.download, roles: ['superadmin', 'hradmin'] },
  { to: '/users', label: '用户管理', icon: ICONS.users, roles: ['superadmin', 'hradmin'] },
  { to: '/settings/rules', label: '考勤规则', icon: ICONS.shield, roles: ['superadmin', 'hradmin'] },
  { to: '/settings', label: '系统设置', icon: ICONS.settings, roles: ['superadmin'] },
];

const user = computed(() => Auth.getUser() || {});
const role = computed(() => Auth.getRole() || 'employee');
const displayName = computed(() => user.value.name || Auth.getUsername() || '员工');
const accountText = computed(() => Auth.getUsername() || user.value.username || '');
const avatarChar = computed(() => String(displayName.value).slice(0, 1));

const navItems = computed(() => ALL_NAV.filter(item => item.roles.includes(role.value)));

function isActive(to) {
  if (to === '/attendance' && route.path.startsWith('/attendance')) return true;
  if (to === '/settings' && route.path.startsWith('/settings') && route.path !== '/settings/rules') return true;
  if (to === '/settings/rules' && route.path === '/settings/rules') return true;
  return route.path === to;
}

function handleLogout() {
  Auth.logout();
  router.push('/login');
}
</script>
