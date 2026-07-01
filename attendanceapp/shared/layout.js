// shared/layout.js — 全局侧边栏导航框架

const AppLayout = {
  menuOpen: false,

  navItems: [
    { id: 'import',    label: '数据导入',   href: 'import.html',             icon: 'upload' },
    { id: 'attendance',label: '考勤计算',   href: 'attendance.html',         icon: 'clock' },
    { id: 'export',    label: '导出中心',   href: 'export.html',             icon: 'download' },
    { id: 'attendance-settings', label: '考勤规则', href: 'attendance-settings.html', icon: 'settings' },
    { id: 'settings',  label: '系统设置',   href: 'settings.html',           icon: 'shield' },
  ],

  init() {
    const page = this._detectPage();
    const nav = document.getElementById('sidebar-nav');
    if (!nav) return;

    this.navItems.forEach(item => {
      const isActive = page === item.id;
      const a = document.createElement('a');
      a.href = item.href;
      a.className = `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
        isActive
          ? 'bg-purple-100 text-purple-700 border-l-3 border-purple-600'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }`;
      a.innerHTML = `
        <span class="w-5 h-5 flex-shrink-0">${this._icon(item.icon, isActive)}</span>
        <span>${item.label}</span>
      `;
      nav.appendChild(a);
    });

    this._updateGreeting();
  },

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) {
      sidebar.classList.toggle('-translate-x-full', !this.menuOpen);
      sidebar.classList.toggle('translate-x-0', this.menuOpen);
    }
    if (overlay) {
      overlay.classList.toggle('hidden', !this.menuOpen);
    }
  },

  closeMenu() {
    this.menuOpen = false;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.add('-translate-x-full');
    if (overlay) overlay.classList.add('hidden');
  },

  _detectPage() {
    const path = window.location.pathname;
    if (path.includes('import')) return 'import';
    if (path.includes('attendance')) return 'attendance';
    if (path.includes('export')) return 'export';
    if (path.includes('attendance-settings')) return 'attendance-settings';
    if (path.includes('settings')) return 'settings';
    return '';
  },

  _updateGreeting() {
    const el = document.getElementById('header-greeting');
    if (!el) return;
    const hour = new Date().getHours();
    let greeting = '上午好';
    if (hour >= 12 && hour < 18) greeting = '下午好';
    if (hour >= 18) greeting = '晚上好';
    const user = localStorage.getItem('attendance_user') || '管理员';
    el.textContent = `${greeting}，${user}`;
  },

  _icon(name, active) {
    const color = active ? '#7C3AED' : '#64748B';
    const icons = {
      upload:   `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
      clock:    `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
      download: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
      settings: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
      shield:   `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    };
    return icons[name] || icons.settings;
  }
};

document.addEventListener('DOMContentLoaded', () => AppLayout.init());
