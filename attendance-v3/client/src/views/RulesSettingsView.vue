<template>
  <div>
    <div v-if="saved" class="alert alert-info mb-md">设置已保存，请前往考勤计算页点击「重新计算」使新规则生效。</div>

    <div class="tabs mb-md">
      <div class="tab" :class="{ active: tab === 'time' }" @click="tab = 'time'">考勤时段</div>
      <div class="tab" :class="{ active: tab === 'tolerance' }" @click="tab = 'tolerance'">容错规则</div>
      <div class="tab" :class="{ active: tab === 'holidays' }" @click="tab = 'holidays'">假期管理</div>
      <div class="tab" :class="{ active: tab === 'fields' }" @click="tab = 'fields'">OA 字段</div>
    </div>

    <div v-if="tab === 'time'" class="card">
      <div class="card-header">
        <h2 class="card-title">考勤时段配置</h2>
        <button @click="saveTime" class="btn btn-primary"><AppIcon name="save" /><span>保存设置</span></button>
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
        <div class="form-group">
          <label class="form-label">加班起算 (分钟)</label>
          <input v-model.number="config.overtimeThreshold" type="number" min="0" class="form-input">
        </div>
      </div>
    </div>

    <div v-else-if="tab === 'tolerance'" class="card">
      <div class="card-header">
        <h2 class="card-title">容错规则配置</h2>
        <button @click="saveTolerance" class="btn btn-primary"><AppIcon name="save" /><span>保存设置</span></button>
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

    <div v-else-if="tab === 'fields'" class="card">
      <div class="card-header">
        <h2 class="card-title">OA 字段映射</h2>
        <button @click="saveFieldMap" class="btn btn-primary"><AppIcon name="save" /><span>保存映射</span></button>
      </div>
      <p class="hint-text">OA 表头改名后，在此补别名或等下次导入时自动学到相近列名。逗号分隔多个别名。</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
        <div class="form-group">
          <label class="form-label">视为本人</label>
          <input v-model="selfTrueText" type="text" class="form-input" placeholder="本人,是,Y">
        </div>
        <div class="form-group">
          <label class="form-label">视为帮他人</label>
          <input v-model="selfFalseText" type="text" class="form-input" placeholder="非本人,否,帮他人">
        </div>
      </div>
      <div class="tabs mb-md" style="margin-bottom:12px">
        <div v-for="t in fieldTypes" :key="t.key" class="tab" :class="{ active: fieldType === t.key }" @click="fieldType = t.key">{{ t.label }}</div>
      </div>
      <div v-for="row in currentFieldRows" :key="row.field" class="form-group">
        <label class="form-label">{{ row.label }}</label>
        <input v-model="fieldDraft[fieldType][row.field]" type="text" class="form-input" :placeholder="row.placeholder">
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
        <button @click="addHolidays" class="btn btn-primary"><AppIcon name="plus" /><span>批量添加</span></button>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <div v-for="h in holidays" :key="h.id" class="flex-between" style="padding:8px 12px;background:var(--paper);border-radius:var(--radius-sm)">
          <span style="font-size:13px">{{ h.date }} - {{ h.name }} <span class="badge" :class="h.isWorkday ? 'badge-normal' : 'badge-late'">{{ h.isWorkday ? '上班' : '休息' }}</span></span>
          <button @click="deleteHoliday(h)" class="btn btn-danger btn-sm"><AppIcon name="trash" :size="13" /><span>删除</span></button>
        </div>
        <div v-if="holidays.length === 0" class="empty-hint">暂无假期设置</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import AppIcon from '../components/AppIcon.vue';
import { apiRequest } from '../shared/api';
import Store from '../shared/store';
import { FieldMap, mergeFieldMap, FIELD_LABELS } from '../shared/fieldMap';
import Excel from '../shared/excel';

const tab = ref('time');
const saved = ref(false);
const config = ref({ workStartTime: '08:30', workEndTime: '17:30', lateThreshold: 0, earlyThreshold: 0, graceTimes: 2, graceMinutes: 30, overtimeThreshold: 30 });
const holidays = ref([]);
const newHoliday = ref({ startDate: '', endDate: '', name: '', type: 'holiday' });
const fieldType = ref('leave');
const selfTrueText = ref('');
const selfFalseText = ref('');
const fieldDraft = ref({ punch: {}, leave: {}, miss_punch: {}, overtime: {}, travel: {} });
const fieldTypes = [
  { key: 'leave', label: '请假' },
  { key: 'miss_punch', label: '漏打卡' },
  { key: 'overtime', label: '加班' },
  { key: 'travel', label: '出差' },
  { key: 'punch', label: '打卡' },
];
const currentFieldRows = computed(() => {
  const labels = FIELD_LABELS[fieldType.value] || {};
  const draft = fieldDraft.value[fieldType.value] || {};
  return Object.keys(labels).map((field) => ({
    field,
    label: labels[field],
    aliases: draft[field] || '',
    placeholder: labels[field],
  }));
});

onMounted(async () => {
  await loadConfig();
  await loadHolidays();
  await loadFieldMap();
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
  try {
    holidays.value = await apiRequest('/rules/holidays');
  } catch (e) {
    holidays.value = [];
  }
}

function splitAliases(text) {
  return String(text || '').split(/[,，、;；]/).map(s => s.replace(/\s+/g, '').trim()).filter(Boolean);
}

function applyFieldMap(map) {
  const merged = mergeFieldMap(map);
  selfTrueText.value = (merged.selfTrueValues || []).join(',');
  selfFalseText.value = (merged.selfFalseValues || []).join(',');
  const draft = {};
  for (const type of Object.keys(FIELD_LABELS)) {
    draft[type] = {};
    const src = (merged.types && merged.types[type]) || {};
    for (const field of Object.keys(FIELD_LABELS[type])) {
      draft[type][field] = (src[field] || []).join(',');
    }
  }
  fieldDraft.value = draft;
}

async function loadFieldMap() {
  try {
    applyFieldMap(await FieldMap.getMap());
  } catch (e) {
    applyFieldMap(null);
  }
}

async function saveFieldMap() {
  const types = {};
  for (const type of Object.keys(FIELD_LABELS)) {
    types[type] = {};
    const rows = fieldDraft.value[type] || {};
    for (const field of Object.keys(FIELD_LABELS[type])) {
      types[type][field] = splitAliases(rows[field]);
    }
  }
  await FieldMap.saveMap({
    selfTrueValues: splitAliases(selfTrueText.value),
    selfFalseValues: splitAliases(selfFalseText.value),
    types,
  });
  Excel._fieldMapCache = null;
  showSaved();
}

function showSaved() {
  saved.value = true;
  setTimeout(() => { saved.value = false; }, 4000);
}

async function touchConfigUpdatedAt() {
  await Store.put('settings', { key: 'config_updated_at', value: Date.now() });
}

async function saveTime() {
  const cur = await apiRequest('/rules/config');
  const changed = ['workStartTime', 'workEndTime', 'lateThreshold', 'earlyThreshold', 'overtimeThreshold']
    .some(k => String(cur[k] ?? '') !== String(config.value[k] ?? ''));
  await apiRequest('/rules/config', {
    method: 'PUT',
    body: JSON.stringify({
      workStartTime: config.value.workStartTime,
      workEndTime: config.value.workEndTime,
      lateThreshold: config.value.lateThreshold,
      earlyThreshold: config.value.earlyThreshold,
      overtimeThreshold: config.value.overtimeThreshold,
    }),
  });
  if (changed) await touchConfigUpdatedAt();
  showSaved();
}

async function saveTolerance() {
  const cur = await apiRequest('/rules/tolerance');
  const changed = ['graceTimes', 'graceMinutes']
    .some(k => String(cur[k] ?? '') !== String(config.value[k] ?? ''));
  await apiRequest('/rules/tolerance', {
    method: 'PUT',
    body: JSON.stringify({
      graceTimes: config.value.graceTimes,
      graceMinutes: config.value.graceMinutes,
    }),
  });
  if (changed) await touchConfigUpdatedAt();
  showSaved();
}

function pad2(n) {
  return String(n).padStart(2, '0');
}

function localDateStr(d) {
  return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
}

async function addHolidays() {
  const start = newHoliday.value.startDate;
  const end = newHoliday.value.endDate || start;
  if (!start) {
    alert('请选择开始日期');
    return;
  }
  if (start > end) {
    alert('结束日期不能早于开始日期');
    return;
  }
  const isWorkday = newHoliday.value.type === 'workday';
  const name = newHoliday.value.name || (isWorkday ? '调休上班' : '假期');
  const dates = [];
  const sd = new Date(start + 'T00:00:00');
  const ed = new Date(end + 'T00:00:00');
  for (let d = new Date(sd); d <= ed; d.setDate(d.getDate() + 1)) {
    dates.push(localDateStr(d));
  }
  try {
    await apiRequest('/rules/holidays', {
      method: 'PUT',
      body: JSON.stringify({ dates, name, is_workday: isWorkday ? 1 : 0 }),
    });
    try { await touchConfigUpdatedAt(); } catch (e) { /* 写入时间戳失败不影响假期列表 */ }
    await loadHolidays();
    newHoliday.value = { startDate: '', endDate: '', name: '', type: 'holiday' };
    showSaved();
  } catch (err) {
    alert(err.message || '添加假期失败');
  }
}

async function deleteHoliday(h) {
  try {
    await apiRequest('/rules/holidays/' + h.id, { method: 'DELETE' });
    await touchConfigUpdatedAt();
    await loadHolidays();
  } catch (err) {
    alert(err.message || '删除假期失败');
  }
}
</script>

<style scoped>
.empty-hint { padding: 16px; text-align: center; font-size: 13px; color: var(--ink-secondary); }
.hint-text { font-size: 13px; color: var(--ink-secondary); margin-bottom: 12px; }
</style>
