<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">用户管理</h2>
        <button class="btn btn-primary" @click="openCreate">新建用户</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>姓名</th>
              <th>部门</th>
              <th>角色</th>
              <th>状态</th>
              <th>登录尝试</th>
              <th style="text-align:right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.name }}</td>
              <td>{{ u.department }}</td>
              <td>{{ roleLabel(u.role) }}</td>
              <td>
                <span class="badge" :class="u.enabled ? 'badge-normal' : 'badge-late'">{{ u.enabled ? '启用' : '禁用' }}</span>
              </td>
              <td>{{ u.login_attempts || 0 }}</td>
              <td style="text-align:right">
                <button class="btn btn-secondary btn-sm" @click="openEdit(u)">编辑</button>
                <button class="btn btn-secondary btn-sm" @click="openReset(u)">重置密码</button>
                <button class="btn btn-ghost btn-sm" :style="u.enabled ? 'color:var(--vermillion)' : 'color:var(--jade)'" @click="toggleEnabled(u)">
                  {{ u.enabled ? '禁用' : '启用' }}
                </button>
              </td>
            </tr>
            <tr v-if="users.length === 0">
              <td colspan="8" style="text-align:center;color:var(--text-secondary);padding:24px">暂无用户</td>
            </tr>
          </tbody>
        </table>
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
          </select>
        </div>
        <div v-if="modalMode === 'create'" class="form-group">
          <label class="form-label">初始密码</label>
          <input v-model="form.password" type="text" class="form-input" placeholder="默认 123456">
        </div>
        <div class="flex gap-sm" style="justify-content:flex-end">
          <button class="btn btn-ghost" @click="closeModal">取消</button>
          <button class="btn btn-primary" @click="submitForm">{{ modalMode === 'create' ? '创建' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { apiRequest } from '../shared/api';

const users = ref([]);
const showModal = ref(false);
const modalMode = ref('create');
const form = ref({ id: null, username: '', name: '', department: '', role: 'employee', password: '123456' });

const ROLE_LABELS = { employee: '员工', deptadmin: '部门管理员', hradmin: '人事管理员' };

onMounted(loadUsers);

function roleLabel(r) {
  return ROLE_LABELS[r] || r;
}

async function loadUsers() {
  users.value = await apiRequest('/users');
}

function openCreate() {
  modalMode.value = 'create';
  form.value = { id: null, username: '', name: '', department: '', role: 'employee', password: '123456' };
  showModal.value = true;
}

function openEdit(u) {
  modalMode.value = 'edit';
  form.value = { id: u.id, username: u.username, name: u.name, department: u.department, role: u.role };
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
