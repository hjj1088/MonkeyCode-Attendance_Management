<template>
  <div>
    <div v-if="saved" class="alert alert-info mb-md">设置已保存，请前往考勤计算页点击「重新计算」使新规则生效。</div>

    <div class="tabs mb-md">
      <div class="tab" :class="{ active: tab === 'time' }" @click="tab = 'time'">考勤时段</div>
      <div class="tab" :class="{ active: tab === 'tolerance' }" @click="tab = 'tolerance'">容错规则</div>
      <div class="tab" :class="{ active: tab === 'holidays' }" @click="tab = 'holidays'">假期管理</div>
    </div>

    <div v-if="tab === 'time'" class="card">
      <div class="card-header">
        <h2 class="card-title">考勤时段配置</h2>
        <button @click="saveTime" class="btn btn-primary">保存设置</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="form-group">
          <label class="form-label">上班时间</label>
          <input v-model="config.workStartTime" type="time" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">下班时间</label>
          <input v-model="config.workEndTime" type="time" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">迟到阈值 (分钟)</label>
          <input v-model.number="config.lateThreshold" type="number" min="0" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">早退阈值 (分钟)</label>
          <input v-model.number="config.earlyThreshold" type="number" min="0" class="form-input">
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'tolerance'" class="card">
      <div class="card-header">
        <h2 class="card-title">容错规则配置</h2>
        <button @click="saveTolerance" class="btn btn-primary">保存设置</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="form-group">
          <label class="form-label">每月豁免次数</label>
          <input v-model.number="config.graceTimes" type="number" min="0" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">累计豁免时长 (分钟)</label>
          <input v-model.number="config.graceMinutes" type="number" min="0" class="form-input">
        </div>
      </div>
    </div>

    <div v-else class="card">
      <h2 class="card-title mb-md">假期管理</h2>
      <div class="flex flex-wrap gap-sm mb-md" style="align-items:flex-end">
        <div class="form-group" style="margin-bottom:0">
          <label class="form-label">开始日期</label>
          <input v-model="newHoliday.startDate" type="date" class="form-input">
        </div>
        <div class="form-group" style="margin-bottom:0">
          <label class="form-label">结束日期</label>
          <input v-model="newHoliday.endDate" type="date" class="form-input">
        </div>
        <div class="form-group" style="margin-bottom:0">
          <label class="form-label">假期名称</label>
          <input v-model="newHoliday.name" type="text" placeholder="例：春节" class="form-input" style="width:130px">
        </div>
        <div class="form-group" style="margin-bottom:0">
          <label class="form-label">类型</label>
          <select v-model="newHoliday.type" class="form-select">
            <option value="holiday">休息日</option>
            <option value="workday">调休上班日</option>
          </select>
        </div>
        <button @click="addHolidays" class="btn btn-primary">批量添加</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <div v-for="h in holidays" :key="h.id" class="flex-between" style="padding:8px 12px;background:var(--paper);border-radius:var(--radius-sm)">
          <span style="font-size:13px">{{ h.date }} - {{ h.name }} <span class="badge" :class="h.isWorkday ? 'badge-normal' : 'badge-late'">{{ h.isWorkday ? '上班' : '休息' }}</span></span>
          <button @click="deleteHoliday(h)" class="btn btn-ghost btn-sm" style="color:var(--vermillion)">删除</button>
        </div>
        <div v-if="holidays.length === 0" style="padding:16px;text-align:center;font-size:13px;color:var(--text-secondary)">暂无假期设置</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { apiRequest } from '../shared/api';
import Store from '../shared/store';

const tab = ref('time');
const saved = ref(false);
const config = ref({ workStartTime: '08:30', workEndTime: '17:30', lateThreshold: 0, earlyThreshold: 0, graceTimes: 2, graceMinutes: 30 });
const holidays = ref([]);
const newHoliday = ref({ startDate: '', endDate: '', name: '', type: 'holiday' });

onMounted(async () => {
  await loadConfig();
  await loadHolidays();
});

async function loadConfig() {
  try {
    const cfg = await apiRequest('/rules/config');
    const tol = await apiRequest('/rules/tolerance');
    config.value = { ...config.value, ...cfg, ...tol };
  } catch (e) {
    const entry = await Store.getByKey('settings', 'attendance_config');
    if (entry && entry.value) Object.assign(config.value, entry.value);
  }
}

async function loadHolidays() {
  holidays.value = await apiRequest('/rules/holidays');
}

function showSaved() {
  saved.value = true;
  setTimeout(() => { saved.value = false; }, 4000);
}

async function touchConfigUpdatedAt() {
  await Store.put('settings', { key: 'config_updated_at', value: Date.now() });
}

async function saveTime() {
  await apiRequest('/rules/config', {
    method: 'PUT',
    body: JSON.stringify({
      workStartTime: config.value.workStartTime,
      workEndTime: config.value.workEndTime,
      lateThreshold: config.value.lateThreshold,
      earlyThreshold: config.value.earlyThreshold,
    }),
  });
  await touchConfigUpdatedAt();
  showSaved();
}

async function saveTolerance() {
  await apiRequest('/rules/tolerance', {
    method: 'PUT',
    body: JSON.stringify({
      graceTimes: config.value.graceTimes,
      graceMinutes: config.value.graceMinutes,
    }),
  });
  await touchConfigUpdatedAt();
  showSaved();
}

async function addHolidays() {
  const start = newHoliday.value.startDate;
  const end = newHoliday.value.endDate || start;
  if (!start) return;
  if (start > end) { alert('结束日期不能早于开始日期'); return; }
  const isWorkday = newHoliday.value.type === 'workday';
  const name = newHoliday.value.name || (isWorkday ? '调休上班' : '假期');
  const dates = [];
  const sd = new Date(start + 'T00:00:00');
  const ed = new Date(end + 'T00:00:00');
  for (let d = new Date(sd); d <= ed; d.setDate(d.getDate() + 1)) {
    dates.push(d.toISOString().slice(0, 10));
  }
  await apiRequest('/rules/holidays', {
    method: 'PUT',
    body: JSON.stringify({ dates, name, is_workday: isWorkday ? 1 : 0 }),
  });
  await touchConfigUpdatedAt();
  await loadHolidays();
  newHoliday.value = { startDate: '', endDate: '', name: '', type: 'holiday' };
}

async function deleteHoliday(h) {
  await apiRequest('/rules/holidays/' + h.id, { method: 'DELETE' });
  await touchConfigUpdatedAt();
  await loadHolidays();
}
</script>
