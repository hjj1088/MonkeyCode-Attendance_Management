<template>
  <div>
    <div v-if="saved" class="alert alert-info mb-md">配置已保存</div>

    <div class="tabs mb-md">
      <div class="tab" :class="{ active: tab === 'general' }" @click="tab = 'general'">常规配置</div>
      <div class="tab" :class="{ active: tab === 'password' }" @click="tab = 'password'">管理员密码</div>
      <div class="tab" :class="{ active: tab === 'status' }" @click="tab = 'status'">系统状态</div>
      <div class="tab" :class="{ active: tab === 'data' }" @click="tab = 'data'">数据管理</div>
    </div>

    <div v-if="tab === 'general'" class="card">
      <div class="card-header">
        <h2 class="card-title">常规配置</h2>
        <button @click="saveGeneral" class="btn btn-primary">保存设置</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="form-group">
          <label class="form-label">公司名称</label>
          <input v-model="general.company_name" type="text" class="form-input" placeholder="例：某某科技有限公司">
        </div>
        <div class="form-group">
          <label class="form-label">数据保留天数</label>
          <input v-model.number="general.data_retention_days" type="number" min="1" class="form-input">
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'password'" class="card">
      <div class="card-header">
        <h2 class="card-title">管理员密码</h2>
        <button @click="savePassword" class="btn btn-primary">确认修改</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr;gap:16px;max-width:420px">
        <div class="form-group">
          <label class="form-label">当前密码</label>
          <input v-model="pwd.current_password" type="password" class="form-input" autocomplete="current-password">
        </div>
        <div class="form-group">
          <label class="form-label">新密码</label>
          <input v-model="pwd.new_password" type="password" class="form-input" autocomplete="new-password">
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'status'" class="card">
      <h2 class="card-title mb-md">系统状态</h2>
      <div v-if="status" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px">
        <div class="form-group" style="margin:0">
          <label class="form-label">应用版本</label>
          <div class="stat-value">V3.1.0</div>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">数据库大小</label>
          <div class="stat-value">{{ status.db_size_mb }} MB</div>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">运行时长</label>
          <div class="stat-value">{{ uptimeText }}</div>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label">Python 版本</label>
          <div class="stat-value">{{ status.python_version }}</div>
        </div>
      </div>
      <div v-if="status && status.record_counts" class="section-title" style="margin-top:24px">数据表行数</div>
      <div v-if="status && status.record_counts" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">
        <div v-for="(count, name) in status.record_counts" :key="name" class="flex-between" style="padding:6px 10px;background:var(--paper);border-radius:var(--radius-sm);font-size:13px">
          <span>{{ name }}</span>
          <span style="font-weight:600">{{ count }}</span>
        </div>
      </div>
    </div>

    <div v-else class="card">
      <h2 class="card-title mb-md">数据管理</h2>
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">生成演示数据（员工/打卡/请假），或清空所有业务数据（保留用户与配置）。</p>
      <div class="flex gap-sm">
        <button @click="seedTestData" :disabled="seeding" class="btn btn-primary">
          {{ seeding ? '生成中...' : '生成测试数据' }}
        </button>
        <button @click="resetDB" :disabled="resetting" class="btn btn-secondary" style="color:var(--vermillion);border-color:var(--vermillion)">
          {{ resetting ? '重置中...' : '重置数据库' }}
        </button>
      </div>
      <div v-if="dataMsg" style="margin-top:12px;font-size:13px;color:var(--jade)">{{ dataMsg }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { apiRequest } from '../shared/api';

const tab = ref('general');
const saved = ref(false);
const general = ref({ company_name: '', data_retention_days: 365 });
const pwd = ref({ current_password: '', new_password: '' });
const status = ref(null);
const seeding = ref(false);
const resetting = ref(false);
const dataMsg = ref('');

const uptimeText = computed(() => {
  if (!status.value || !status.value.uptime_seconds) return '-';
  const s = status.value.uptime_seconds;
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return d > 0 ? `${d}天${h}小时` : `${h}小时${m}分`;
});

onMounted(async () => {
  await loadGeneral();
  await loadStatus();
});

function showSaved() {
  saved.value = true;
  setTimeout(() => { saved.value = false; }, 4000);
}

async function loadGeneral() {
  try {
    general.value = { ...general.value, ...(await apiRequest('/system/config')) };
  } catch (e) { /* ignore */ }
}

async function loadStatus() {
  try {
    status.value = await apiRequest('/system/status');
  } catch (e) { /* ignore */ }
}

async function saveGeneral() {
  await apiRequest('/system/config', {
    method: 'PUT',
    body: JSON.stringify({
      company_name: general.value.company_name,
      data_retention_days: general.value.data_retention_days,
    }),
  });
  showSaved();
}

async function savePassword() {
  await apiRequest('/system/admin-password', {
    method: 'PUT',
    body: JSON.stringify({
      current_password: pwd.value.current_password,
      new_password: pwd.value.new_password,
    }),
  });
  pwd.value = { current_password: '', new_password: '' };
  showSaved();
}

async function seedTestData() {
  seeding.value = true;
  dataMsg.value = '';
  try {
    const res = await apiRequest('/system/seed-test-data', { method: 'POST' });
    dataMsg.value = res.message || '测试数据生成成功';
  } catch (err) {
    dataMsg.value = err.message;
  }
  seeding.value = false;
  await loadStatus();
}

async function resetDB() {
  if (!confirm('确定要清空所有业务数据吗？用户和配置将保留。此操作不可恢复。')) return;
  resetting.value = true;
  dataMsg.value = '';
  try {
    const res = await apiRequest('/system/reset-data', { method: 'POST' });
    dataMsg.value = res.message || '已重置';
  } catch (err) {
    dataMsg.value = err.message;
  }
  resetting.value = false;
  await loadStatus();
}
</script>

<style scoped>
.stat-value { font-size: 15px; font-weight: 600; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
</style>
