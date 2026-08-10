// shared/layout.js — macOS Big Sur 风格侧边栏导航

const AppLayout = {
  menuOpen: false,

  navItems: [
    { id: 'import',    label: '数据导入',   href: 'import.html',             icon: 'upload' },
    { id: 'attendance',label: '考勤计算',   href: 'attendance.html',         icon: 'clock' },
    { id: 'export',    label: '导出中心',   href: 'export.html',             icon: 'download' },
    { id: 'settings',  label: '系统设置',   href: 'settings.html',           icon: 'settings' },
  ],

  lucideIcons: {
    upload: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
    clock: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    download: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
    settings: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    shield: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.06 1.06 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M9 12l2 2 4-4"/></svg>`,
  },

  logoutIcon: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>`,

  hamburgerIcon: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,

  logoIcon: `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,

  init() {
    if (!Auth.isLoggedIn()) {
      window.location.href = 'index.html';
      return;
    }
    const page = this._detectPage();
    const nav = document.getElementById('sidebar-nav');
    if (!nav) return;

    this.navItems.forEach(item => {
      const isActive = page === item.id;
      const a = document.createElement('a');
      a.href = item.href;
      a.className = 'nav-item' + (isActive ? ' active' : '');
      a.innerHTML = `
        <div class="nav-icon">${this.lucideIcons[item.icon]}</div>
        <span class="nav-label">${item.label}</span>
      `;
      nav.appendChild(a);
    });

    this._updateGreeting();
    this._updateVersion();
  },

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open', this.menuOpen);
    if (overlay) overlay.classList.toggle('hidden', !this.menuOpen);
  },

  closeMenu() {
    this.menuOpen = false;
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
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
    let g = '上午好';
    if (hour >= 12 && hour < 18) g = '下午好';
    if (hour >= 18) g = '晚上好';
    const user = localStorage.getItem('attendance_user') || '管理员';
    el.textContent = g + '，' + user;
  },

  _updateVersion() {
    const footer = document.querySelector('.sidebar-footer');
    if (!footer) return;
    fetch('/api/system/version')
      .then(r => r.json())
      .then(res => {
        const v = res && res.data;
        if (v && v.version_name) {
          const div = document.createElement('div');
          div.className = 'sidebar-version';
          div.style.cssText = 'padding:8px 20px;font-size:11px;color:#8a8f98;text-align:center;';
          div.textContent = 'V3.1 考勤管理系统';
          footer.appendChild(div);
        }
      })
      .catch(() => {});
  }
};

document.addEventListener('DOMContentLoaded', () => AppLayout.init());
