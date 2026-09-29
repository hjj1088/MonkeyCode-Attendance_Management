<template>
  <div class="users-page">
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">用户管理</h2>
        <div class="flex gap-sm">
          <button class="btn btn-secondary" @click="importFromPunch" :disabled="importing">
            <AppIcon name="upload" /><span>{{ importing ? '导入中...' : '从考勤数据导入账号' }}</span>
          </button>
          <button class="btn btn-primary" @click="openCreate"><AppIcon name="user-plus" /><span>新建用户</span></button>
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-card"><div class="stat-icon is-jade">总</div><div class="stat-meta"><span class="stat-label">总用户</span><span class="stat-value">{{ users.length }}</span></div></div>
        <div class="stat-card"><div class="stat-icon is-leave">管</div><div class="stat-meta"><span class="stat-label">管理员</span><span class="stat-value">{{ adminCount }}</span></div></div>
        <div class="stat-card"><div class="stat-icon is-miss">员</div><div class="stat-meta"><span class="stat-label">普通用户</span><span class="stat-value">{{ employeeCount }}</span></div></div>
      </div>
      <div class="table-wrap">
        <StickyTable :cols="userCols" min-width="980px">
          <template #head>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>考勤号</th>
              <th>姓名</th>
              <th>部门</th>
              <th>角色</th>
              <th>状态</th>
              <th>登录尝试</th>
              <th class="c-right">操作</th>
            </tr>
          </template>
          <tr v-for="u in pagedUsers" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.employee_no || u.username }}</td>
            <td>{{ u.name }}</td>
            <td>{{ u.department }}</td>
            <td>{{ roleLabel(u.role) }}</td>
            <td>
              <span class="badge" :class="u.enabled ? 'badge-normal' : 'badge-late'">{{ u.enabled ? '启用' : '禁用' }}</span>
            </td>
            <td>{{ u.login_attempts || 0 }}</td>
            <td class="c-right">
              <button class="btn btn-secondary btn-sm" @click="openEdit(u)"><AppIcon name="pencil" :size="13" /><span>编辑</span></button>
              <button class="btn btn-secondary btn-sm" @click="openReset(u)"><AppIcon name="key" :size="13" /><span>重置密码</span></button>
              <button v-if="u.username !== 'admin'" class="btn btn-ghost btn-sm" :class="u.enabled ? 'btn-danger-text' : 'btn-ok-text'" @click="toggleEnabled(u)">
                <AppIcon :name="u.enabled ? 'ban' : 'check'" :size="13" /><span>{{ u.enabled ? '禁用' : '启用' }}</span>
              </button>
              <button v-if="u.username !== 'admin'" class="btn btn-danger btn-sm" @click="removeUser(u)"><AppIcon name="trash" :size="13" /><span>删除</span></button>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="9" class="empty-cell">暂无用户</td>
          </tr>
        </StickyTable>
      </div>
      <div v-if="users.length" class="pager">
        <span class="pager-info">共 {{ users.length }} 条</span>
        <label class="pager-size">
          每页
          <select v-model.number="pageSize" @change="onPageSizeChange">
            <option v-for="n in pageSizeOptions" :key="n" :value="n">{{ n }}</option>
          </select>
          条
        </label>
        <div class="pager-nav">
          <button class="btn btn-ghost btn-sm pager-step" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)"><AppIcon name="chevron-left" /><span>上一页</span></button>
          <div class="pager-pages">
            <button
              v-for="(p, pi) in visiblePages"
              :key="pi"
              class="pager-num"
              :class="{ active: p === currentPage }"
              :disabled="p === '...'"
              @click="p !== '...' && goPage(p)"
            >{{ p }}</button>
          </div>
          <button class="btn btn-ghost btn-sm pager-step" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)"><span>下一页</span><AppIcon name="chevron-right" /></button>
          <span class="pager-info pager-status">{{ currentPage }} / {{ totalPages }}</span>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="detail-overlay" @click.self="closeModal">
      <div class="detail-modal" style="max-width:440px">
        <h3 class="card-title mb-md">{{ modalMode === 'create' ? '新建用户' : '编辑用户' }}</h3>
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input v-model="form.username" type="text" class="form-input" :disabled="modalMode === 'edit'" placeholder="登录账号">
        </div>
        <div class="form-group">
          <label class="form-label">考勤号</label>
          <input v-model="form.employee_no" type="text" class="form-input" placeholder="考勤号（默认同用户名）">
        </div>
        <div class="form-group">
          <label class="form-label">姓名</label>
          <input v-model="form.name" type="text" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">部门</label>
          <input v-model="form.department" type="text" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">角色</label>
          <select v-model="form.role" class="form-select">
            <option value="employee">员工</option>
            <option value="deptadmin">部门管理员</option>
            <option value="hradmin">人事管理员</option>
            <option v-if="myRole === 'superadmin'" value="superadmin">超级管理员</option>
          </select>
        </div>
        <div v-if="modalMode === 'create'" class="form-group">
          <label class="form-label">初始密码</label>
          <input v-model="form.password" type="text" class="form-input" placeholder="默认 123456">
        </div>
        <div class="flex gap-sm" style="justify-content:flex-end">
          <button class="btn btn-ghost" @click="closeModal"><AppIcon name="close" /><span>取消</span></button>
          <button class="btn btn-primary" @click="submitForm"><AppIcon :name="modalMode === 'create' ? 'user-plus' : 'save'" /><span>{{ modalMode === 'create' ? '创建' : '保存' }}</span></button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import StickyTable from '../components/StickyTable.vue';
import AppIcon from '../components/AppIcon.vue';
import { apiRequest } from '../shared/api';
import Auth from '../shared/auth';

const users = ref([]);
const importing = ref(false);
const myRole = Auth.getRole();
const showModal = ref(false);
const modalMode = ref('create');
const form = ref({ id: null, username: '', name: '', department: '', role: 'employee', employee_no: '', password: '123456' });

const userCols = ['56px', '88px', '88px', '72px', '88px', '108px', '64px', '80px', '240px'];
const ROLE_LABELS = { employee: '员工', deptadmin: '部门管理员', hradmin: '人事管理员', superadmin: '超级管理员' };
const adminCount = computed(() => users.value.filter(u => u.role && u.role !== 'employee').length);
const employeeCount = computed(() => users.value.filter(u => u.role === 'employee').length);

const PREF_KEY = 'users.listPrefs';
const pageSizeOptions = [10, 20, 30, 50, 100];
function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
  } catch (e) {
    return {};
  }
}
const prefs = loadPrefs();
const pageSize = ref(pageSizeOptions.includes(prefs.pageSize) ? prefs.pageSize : 10);
const currentPage = ref(1);
const totalPages = computed(() => Math.max(1, Math.ceil(users.value.length / pageSize.value)));
const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return users.value.slice(start, start + pageSize.value);
});
const visiblePages = computed(() => {
  const total = totalPages.value;
  const cur = currentPage.value;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (cur <= 4) return [1, 2, 3, 4, 5, '...', total];
  if (cur >= total - 3) return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
  return [1, '...', cur - 1, cur, cur + 1, '...', total];
});

function savePrefs() {
  localStorage.setItem(PREF_KEY, JSON.stringify({ pageSize: pageSize.value }));
}
function goPage(p) {
  const n = Number(p);
  if (!n || n < 1 || n > totalPages.value) return;
  currentPage.value = n;
}
function onPageSizeChange() {
  currentPage.value = 1;
  savePrefs();
}

watch(totalPages, (n) => { if (currentPage.value > n) currentPage.value = n; });

onMounted(loadUsers);

function roleLabel(r) {
  return ROLE_LABELS[r] || r;
}

async function loadUsers() {
  users.value = await apiRequest('/users');
}

async function importFromPunch() {
  if (!confirm('将从考勤数据中按考勤号自动创建员工账号（默认密码 123456，角色：员工）。已存在的账号将跳过，是否继续？')) return;
  importing.value = true;
  try {
    const res = await apiRequest('/users/import-from-punch', { method: 'POST' });
    alert(res.message || '导入完成');
    await loadUsers();
  } catch (err) {
    alert(err.message || '导入失败');
  }
  importing.value = false;
}

function openCreate() {
  modalMode.value = 'create';
  form.value = { id: null, username: '', name: '', department: '', role: 'employee', employee_no: '', password: '123456' };
  showModal.value = true;
}

function openEdit(u) {
  modalMode.value = 'edit';
  form.value = { id: u.id, username: u.username, name: u.name, department: u.department, role: u.role, employee_no: u.employee_no || '' };
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
}

async function submitForm() {
  try {
    if (modalMode.value === 'create') {
      await apiRequest('/users', {
        method: 'POST',
        body: JSON.stringify({
          username: form.value.username,
          name: form.value.name,
          department: form.value.department,
          role: form.value.role,
          employee_no: form.value.employee_no || '',
          password: form.value.password || '123456',
        }),
      });
    } else {
      await apiRequest('/users/' + form.value.id, {
        method: 'PUT',
        body: JSON.stringify({
          name: form.value.name,
          department: form.value.department,
          role: form.value.role,
          employee_no: form.value.employee_no || '',
        }),
      });
    }
    closeModal();
    await loadUsers();
  } catch (err) {
    alert(err.message || '操作失败');
  }
}

async function toggleEnabled(u) {
  try {
    await apiRequest('/users/' + u.id + '/status', {
      method: 'PUT',
      body: JSON.stringify({ enabled: u.enabled ? 0 : 1 }),
    });
    await loadUsers();
  } catch (err) {
    alert(err.message || '操作失败');
  }
}

async function removeUser(u) {
  if (!confirm('确定删除用户 ' + u.name + ' (' + u.username + ') 吗？其历史考勤数据将保留，仅删除登录账号。')) return;
  try {
    await apiRequest('/users/' + u.id, { method: 'DELETE' });
    await loadUsers();
  } catch (err) {
    alert(err.message || '删除失败');
  }
}

async function openReset(u) {
  const newPassword = prompt('为 ' + u.name + ' (' + u.username + ') 设置新密码：', '123456');
  if (newPassword === null) return;
  if (!newPassword) { alert('密码不能为空'); return; }
  try {
    const res = await apiRequest('/users/reset-password', {
      method: 'POST',
      body: JSON.stringify({ user_id: u.id, new_password: newPassword }),
    });
    alert('密码已重置为：' + (res.new_password || newPassword));
  } catch (err) {
    alert(err.message || '重置失败');
  }
}
</script>

<style scoped>
.users-page { flex: 1; width: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.users-page .card { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; margin-bottom: 0; }
.users-page .card-header,
.users-page .stats-row,
.users-page .pager { flex-shrink: 0; }
.users-page .table-wrap { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.c-right { text-align: right; }
.pager {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
  padding-top: 12px; margin-top: 8px; border-top: 1px solid var(--border);
}
.pager-nav { display: inline-flex; align-items: center; gap: 8px; margin-left: auto; flex-wrap: wrap; }
.pager-pages { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-width: 0; }
.pager-step { min-width: 52px; }
.pager-info { font-size: 12px; color: var(--ink-secondary); }
.pager-status { min-width: 4.5em; text-align: right; font-variant-numeric: tabular-nums; }
.pager-size { font-size: 12px; color: var(--ink-secondary); display: inline-flex; align-items: center; gap: 6px; }
.pager-size select {
  padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--card-bg); color: var(--ink); font-family: var(--font-sans); font-size: 12px;
}
.pager-num {
  width: 32px; min-width: 32px; height: 28px; padding: 0; border: 1px solid var(--border);
  border-radius: var(--radius-sm); background: var(--card-bg); color: var(--ink);
  font-size: 12px; cursor: pointer; font-family: var(--font-sans); text-align: center; box-sizing: border-box;
}
.pager-num.active { background: var(--indigo-dark); color: var(--paper-white); border-color: var(--indigo-dark); }
.pager-num:disabled { opacity: 0.5; cursor: default; }
.detail-overlay { position: fixed; inset: 0; background: rgba(43, 58, 66, 0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); }
.detail-modal { background: var(--card-bg); border-radius: var(--radius-xl); box-shadow: var(--shadow-lg); width: 90vw; max-width: 440px; max-height: 85vh; overflow-y: auto; padding: 24px; }
.btn-danger-text { color: var(--vermillion); }
.btn-ok-text { color: var(--jade); }
.empty-cell { text-align: center; color: var(--ink-secondary); padding: 24px; }
</style>
