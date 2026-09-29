<template>
  <div>
    <div class="stats-row">
      <div class="stat-card"><div class="stat-icon is-jade">正</div><div class="stat-meta"><span class="stat-label">正常出勤</span><span class="stat-value">{{ monthStats.normal }}</span></div></div>
      <div class="stat-card"><div class="stat-icon is-late">迟</div><div class="stat-meta"><span class="stat-label">迟到</span><span class="stat-value">{{ monthStats.late }}</span></div></div>
      <div class="stat-card"><div class="stat-icon is-miss">缺</div><div class="stat-meta"><span class="stat-label">缺卡</span><span class="stat-value">{{ monthStats.miss }}</span></div></div>
      <div class="stat-card"><div class="stat-icon is-leave">假</div><div class="stat-meta"><span class="stat-label">请假出差</span><span class="stat-value">{{ monthStats.leave }}</span></div></div>
    </div>
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">数据导入</h2>
      </div>
      <div class="drop-zone upload-zone" :class="{ dragover: dragging }"
           @click="openFilePicker"
           @dragover.prevent="dragging = true"
           @dragleave="dragging = false"
           @drop.prevent="handleDrop">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
        <div class="dz-title">拖拽 Excel 文件到此处，或点击选择</div>
        <div class="dz-hint">或</div>
        <label class="btn btn-primary btn-sm mt-sm" style="cursor:pointer" @click.stop>
          <AppIcon name="file" /><span>选择文件</span>
          <input ref="fileInput" type="file" accept=".xlsx,.xls" multiple hidden @change="handleFileSelect">
        </label>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title">文件列表 ({{ files.length }})</h2>
        <button @click="importAll" :disabled="importing || files.length === 0" class="btn btn-primary">
          <AppIcon name="upload" /><span>{{ importing ? '导入中...' : '全部入库' }}</span>
        </button>
      </div>
      <div v-if="files.length === 0" class="text-center empty-hint">暂无上传文件，请拖拽 Excel 文件到上方区域</div>
      <div v-else style="display:flex;flex-direction:column;gap:8px">
        <div v-for="(f, idx) in files" :key="idx" class="file-row">
          <span class="fr-name" :title="f.fileName">{{ f.fileName }}</span>
          <span class="type-badge" :class="'type-' + f.fileType">{{ typeLabel(f.fileType) }}</span>
          <span class="muted-text">解析: {{ f.recordCount }} 条</span>
          <button class="btn btn-ghost btn-sm" @click="showPreview(f)"><AppIcon name="eye" :size="13" /><span>预览</span></button>
          <span v-if="f.imported" style="font-size:12px;color:var(--jade);white-space:nowrap">已入库</span>
          <span v-if="f.error" class="error-text">{{ f.error }}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title">导入日志</h2>
      </div>
      <div v-if="importLog.length === 0" class="text-center empty-hint">暂无导入记录</div>
      <div v-else>
        <div v-for="(log, i) in importLog" :key="i" class="log-item">
          <span class="log-time">{{ log.time }}</span>
          <span class="type-badge" :class="'type-' + log.type">{{ typeLabel(log.type) }}</span>
          <span class="log-file">{{ log.file }}</span>
          <span v-if="log.action === 'ok'" class="ok-text">+{{ log.count }} 条</span>
          <span v-else class="muted-text nowrap">{{ log.msg }}</span>
        </div>
      </div>
    </div>

    <div v-if="previewFile" class="preview-overlay" @click.self="previewFile = null">
      <div class="preview-modal">
        <div class="pm-header">
          <h3 style="font-size:16px;font-weight:600">数据预览 - {{ previewFile.fileName }}</h3>
          <button class="btn btn-ghost btn-sm" @click="previewFile = null"><AppIcon name="close" /><span>关闭</span></button>
        </div>
        <div class="pm-body">
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th v-for="col in previewColumns" :key="col">{{ col }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in previewRows" :key="ri">
                  <td v-for="col in previewColumns" :key="col">{{ row[col] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="previewFile.records.length > previewRows.length" class="muted-text" style="margin-top:8px">
            仅显示前 {{ previewRows.length }} 条，共 {{ previewFile.records.length }} 条
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject } from 'vue';
import Excel from '../shared/excel';
import AppIcon from '../components/AppIcon.vue';
import { apiRequest } from '../shared/api';
import Store from '../shared/store';
import Auth from '../shared/auth';

const fileInput = ref(null);
const dragging = ref(false);
const importing = ref(false);
const files = ref([]);
const previewFile = ref(null);
const previewColumns = ref([]);
const previewRows = ref([]);
const importLog = ref([]);
const monthStats = ref({ normal: 0, late: 0, miss: 0, leave: 0 });
const statsMonth = ref('');
const setContextChip = inject('setContextChip', () => {});

const TYPE_LABELS = { punch: '打卡', leave: '请假', overtime: '加班', travel: '出差', miss_punch: '漏打卡', schedule: '排班', unknown: '未知' };

function typeLabel(type) {
  return TYPE_LABELS[type] || type;
}

onMounted(loadStats);
onUnmounted(() => setContextChip(''));

async function loadStats() {
  const settingsList = await Store.getAll('settings');
  const settingsMap = {};
  for (const s of settingsList || []) settingsMap[s.key] = s.value;
  let m = settingsMap.last_punch_month;
  if (!m) {
    const now = new Date();
    m = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
  }
  statsMonth.value = m;
  setContextChip(m);
  let list = await Store.getByIndex('attendance_results', 'month', m);
  list = list || [];
  const role = Auth.getRole();
  if (role === 'deptadmin') {
    const dept = Auth.getDepartment();
    list = list.filter(r => r.department === dept);
  }
  const s = { normal: 0, late: 0, miss: 0, leave: 0 };
  for (const r of list) {
    if (r.status === 'normal') s.normal++;
    else if (r.status === 'abnormal') s.late++;
    else if (r.status === 'no_sign_in' || r.status === 'no_sign_out' || r.status === 'absent') s.miss++;
    else if (r.status === 'leave' || r.status === 'travel') s.leave++;
  }
  monthStats.value = s;
}

function openFilePicker() {
  fileInput.value && fileInput.value.click();
}

async function handleFileSelect(e) {
  await processFiles(Array.from(e.target.files));
  e.target.value = '';
}

async function handleDrop(e) {
  dragging.value = false;
  await processFiles(Array.from(e.dataTransfer.files));
}

async function processFiles(fileList) {
  const excelFiles = fileList.filter(f => /\.xlsx?$/i.test(f.name));
  for (const file of excelFiles) {
    const existing = files.value.find(f => f.fileName === file.name);
    if (existing) continue;
    try {
      const wb = await Excel.parseExcelFile(file);
      const ident = await Excel.identifyFileType(wb);
      const records = await Excel.parseRecords(wb, ident.type);
      const recordCount = ident.type === 'schedule'
        ? Excel.flattenScheduleDays(records).length
        : records.length;
      const entry = {
        fileName: file.name,
        fileType: ident.type,
        recordCount,
        records,
        imported: false,
        error: null,
      };
      if (ident.type === 'unknown') {
        const firstSheet = wb.Sheets[wb.SheetNames[0]];
        const headers = (await Excel.sheetToArray(firstSheet))[0] || [];
        entry.error = '未识别类型，表头: ' + headers.filter(Boolean).slice(0, 5).join(', ');
      }
      files.value.push(entry);
    } catch (err) {
      files.value.push({
        fileName: file.name,
        fileType: 'unknown',
        recordCount: 0,
        records: [],
        imported: false,
        error: '解析失败: ' + (err.message || err),
      });
    }
  }
}

function showPreview(f) {
  previewFile.value = f;
  if (f.fileType === 'schedule') {
    const days = Excel.flattenScheduleDays(f.records);
    previewColumns.value = days.length ? ['date', 'work'] : [];
    previewRows.value = days.slice(0, 10);
    previewFile.value = { ...f, records: days };
    return;
  }
  previewColumns.value = f.records.length > 0 ? Object.keys(f.records[0]) : [];
  previewRows.value = f.records.slice(0, 10);
}

async function importAll() {
  importing.value = true;
  let scheduleFile = null;
  try {
    for (const f of files.value) {
      if (f.imported) continue;
      if (f.fileType === 'schedule') { scheduleFile = f; continue; }
      if (f.fileType === 'unknown') { continue; }
      try {
        const res = await apiRequest('/attendance/import', {
          method: 'POST',
          body: JSON.stringify({ type: f.fileType, records: f.records, file_name: f.fileName }),
        });
        f.imported = true;
        if (res.skipped) {
          importLog.value.unshift({ time: new Date().toLocaleTimeString(), file: f.fileName, type: f.fileType, count: 0, action: 'skip', msg: '已存在，跳过' });
        } else {
          importLog.value.unshift({ time: new Date().toLocaleTimeString(), file: f.fileName, type: f.fileType, count: res.imported, action: 'ok', msg: '导入 ' + res.imported + ' 条' });
        }
      } catch (innerErr) {
        f.error = innerErr.message;
        importLog.value.unshift({ time: new Date().toLocaleTimeString(), file: f.fileName, type: f.fileType, count: 0, action: 'err', msg: innerErr.message });
      }
    }
    if (scheduleFile && !scheduleFile.imported) {
      try {
        const res = await apiRequest('/attendance/import', {
          method: 'POST',
          body: JSON.stringify({ type: 'schedule', records: scheduleFile.records, file_name: scheduleFile.fileName }),
        });
        scheduleFile.imported = true;
        importLog.value.unshift({ time: new Date().toLocaleTimeString(), file: scheduleFile.fileName, type: 'schedule', count: res.imported, action: 'ok', msg: res.detail || ('导入 ' + res.imported + ' 条') });
      } catch (innerErr) {
        scheduleFile.error = innerErr.message;
        importLog.value.unshift({ time: new Date().toLocaleTimeString(), file: scheduleFile.fileName, type: 'schedule', count: 0, action: 'err', msg: innerErr.message });
      }
    }
    if (files.value.length > 0 && files.value.every(f => f.imported || f.fileType === 'unknown')) {
      alert('所有数据导入完成！可前往考勤计算页面运行计算。');
    }
  } catch (err) {
    alert('导入出错: ' + err.message);
  }
  importing.value = false;
}
</script>

<style scoped>
.drop-zone { margin-bottom: 20px; }
.drop-zone:hover, .drop-zone.dragover {
  border-color: var(--celadon);
  background: color-mix(in srgb, var(--celadon-light) 50%, transparent);
}
.drop-zone svg { color: var(--ink-muted); margin-bottom: 10px; }
.dz-title { font-size: 14px; color: var(--ink-secondary); margin-bottom: 4px; }
.dz-hint { font-size: 12px; color: var(--ink-muted); }
.empty-hint { padding: 24px; font-size: 13px; color: var(--ink-secondary); }
.muted-text { font-size: 12px; color: var(--ink-secondary); }
.error-text { font-size: 12px; color: var(--vermillion); white-space: nowrap; }
.ok-text { color: var(--jade); white-space: nowrap; }
.nowrap { white-space: nowrap; }
.log-file { flex: 1; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; background: var(--paper);
  border-radius: var(--radius-md); border: 1px solid var(--border);
}
.file-row .fr-name { flex: 1; font-size: 13px; font-weight: 500; color: var(--ink); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-badge {
  display: inline-flex; align-items: center; padding: 2px 10px; border-radius: var(--radius-sm);
  font-size: 12px; font-weight: 500; white-space: nowrap;
}
.type-punch { background: var(--jade-light); color: var(--jade); }
.type-leave { background: var(--gold-muted-light); color: var(--gold-muted); }
.type-overtime { background: var(--vermillion-light); color: var(--vermillion); }
.type-travel { background: var(--celadon-light); color: var(--celadon); }
.type-miss_punch { background: var(--gold-muted-light); color: var(--gold-muted); }
.type-schedule { background: var(--jade-light); color: var(--jade); }
.type-unknown { background: var(--paper); color: var(--ink-muted); }
.log-item {
  display: flex; align-items: center; gap: 10px; padding: 6px 0;
  border-bottom: 1px solid var(--border); font-size: 12px;
}
.log-item:last-child { border-bottom: none; }
.log-time { color: var(--ink-secondary); width: 70px; flex-shrink: 0; }
.preview-overlay {
  position: fixed; inset: 0; background: rgba(43, 58, 66, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: var(--z-modal);
}
.preview-modal {
  background: var(--card-bg); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  width: 90vw; max-width: 900px; max-height: 80vh;
  display: flex; flex-direction: column;
}
.preview-modal .pm-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--border);
}
.preview-modal .pm-body { overflow: auto; padding: 16px 24px 24px; }
</style>
