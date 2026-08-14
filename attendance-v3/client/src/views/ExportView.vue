<template>
  <div class="export-layout">
    <div class="export-left">
      <div class="card">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">模板列表</h3>
        <div style="display:flex;flex-direction:column;gap:2px;margin-bottom:12px">
          <div v-for="t in templates" :key="t.id" @click="selectTemplate(t)" class="template-item" :class="{ active: selectedTemplate && selectedTemplate.id === t.id }">{{ t.name }}</div>
        </div>
        <button @click="saveAsTemplate" class="btn btn-primary btn-sm" style="width:100%">另存为模板</button>
      </div>
    </div>

    <div class="export-main">
      <div class="card">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">模板字段编辑</h3>
        <div>
          <div v-for="(field, idx) in editingFields" :key="idx" class="field-row">
            <input v-model="field.label" placeholder="列名" style="width:100px">
            <select v-model="field.field" style="flex:1">
              <option v-for="col in availableColumns" :key="col.field" :value="col.field">{{ col.label }}</option>
            </select>
            <button @click="removeField(idx)" class="btn btn-ghost btn-sm" style="color:var(--vermillion)">删除</button>
          </div>
        </div>
        <button @click="addField" class="btn btn-secondary btn-sm mt-sm">添加字段</button>
      </div>

      <div class="card">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">导出设置</h3>
        <div class="flex gap-sm flex-wrap" style="align-items:center">
          <select v-model="exportMonth" style="padding:6px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:var(--font-sans);background:var(--card-bg);color:var(--text)">
            <option value="">导出: 全部月份</option>
            <option v-for="m in availableMonths" :key="m" :value="m">{{ m }}</option>
          </select>
          <button @click="doExport" class="btn btn-primary btn-sm">导出 Excel</button>
          <button @click="doCalendarExport" :disabled="!exportMonth" class="btn btn-primary btn-sm">导出考勤明细</button>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:8px">
          考勤明细：日历格式，按模板字段输出。每天两行（上午/下午），上班打卡和下班打卡分列，含排班标注
        </div>
      </div>
    </div>

    <div class="export-right">
      <div class="card">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">实时预览 (前5条)</h3>
        <div v-if="previewData.length > 0" class="table-wrap">
          <table style="font-size:11px">
            <thead><tr><th v-for="f in editingFields" :key="f.field" style="white-space:nowrap">{{ f.label }}</th></tr></thead>
            <tbody>
              <tr v-for="(row, ri) in previewData" :key="ri">
                <td v-for="f in editingFields" :key="f.field" style="white-space:nowrap">
                  {{ f.field === '_index' ? ri + 1 : (row[f.field] !== undefined ? row[f.field] : '') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else style="padding:24px;text-align:center;font-size:13px;color:var(--text-secondary)">暂无数据预览</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import Store from '../shared/store';
import Excel from '../shared/excel';

const templates = ref([]);
const selectedTemplate = ref(null);
const editingFields = ref([]);
const previewData = ref([]);
const exportMonth = ref('');
const availableMonths = ref([]);

const availableColumns = [
  { label: '序号(自动)', field: '_index' },
  { label: '考勤号码', field: 'employeeNo' },
  { label: '姓名', field: 'name' },
  { label: '部门', field: 'department' },
  { label: '日期', field: 'date' },
  { label: '对应时段', field: 'period' },
  { label: '上班时间', field: 'scheduleStart' },
  { label: '下班时间', field: 'scheduleEnd' },
  { label: '签到时间', field: 'signIn' },
  { label: '签退时间', field: 'signOut' },
  { label: '迟到时间', field: 'lateMinutes' },
  { label: '早退时间', field: 'earlyMinutes' },
  { label: '加班时间', field: 'overtimeHours' },
  { label: '出差时间', field: 'travelHours' },
  { label: '是否旷工', field: 'absent' },
  { label: '状态', field: 'status' },
  { label: '请假类型', field: 'leaveType' },
  { label: '请假小时', field: 'leaveHours' },
  { label: '工作时长', field: 'workHours' },
];

onMounted(async () => {
  await loadTemplates();
  await loadMonths();
});

watch(editingFields, () => updatePreview(), { deep: true });

async function loadTemplates() {
  templates.value = await Store.getAll('export_templates');
  if (templates.value.length) selectTemplate(templates.value[0]);
}

function selectTemplate(t) {
  selectedTemplate.value = t;
  editingFields.value = JSON.parse(JSON.stringify(t.fields || []));
  updatePreview();
}

function addField() {
  if (availableColumns.length) editingFields.value.push({ label: '', field: availableColumns[0].field });
}

function removeField(idx) {
  editingFields.value.splice(idx, 1);
  updatePreview();
}

async function saveAsTemplate() {
  const name = prompt('请输入模板名称:');
  if (!name) return;
  await Store.put('export_templates', { name, isDefault: 0, fields: JSON.parse(JSON.stringify(editingFields.value)) });
  await loadTemplates();
}

async function updatePreview() {
  const all = await Store.getAll('attendance_results');
  previewData.value = (all || []).slice(0, 5);
}

async function loadMonths() {
  const results = await Store.getAll('attendance_results');
  const months = new Set(results.filter(r => r.month).map(r => r.month));
  availableMonths.value = [...months].sort();
  if (availableMonths.value.length) exportMonth.value = availableMonths.value[availableMonths.value.length - 1];
}

async function doExport() {
  if (!editingFields.value.length) { alert('请至少添加一个导出字段'); return; }
  const records = exportMonth.value
    ? await Store.getByIndex('attendance_results', 'month', exportMonth.value)
    : await Store.getAll('attendance_results');
  if (!records.length) { alert('没有可导出的数据'); return; }
  const template = { fields: editingFields.value };
  const filename = exportMonth.value ? '考勤记录_' + exportMonth.value + '.xlsx' : '考勤记录_全部.xlsx';
  Excel.exportToExcel(records, template, filename);
}

async function doCalendarExport() {
  if (!exportMonth.value) { alert('请先选择导出月份'); return; }
  if (!editingFields.value.length) { alert('请至少添加一个导出字段'); return; }
  try {
    await Excel.exportCalendarReport(exportMonth.value, editingFields.value);
  } catch (err) {
    alert('导出失败: ' + err.message);
  }
}
</script>

<style scoped>
.export-layout { display: flex; gap: 20px; }
.export-left { width: 200px; flex-shrink: 0; }
.export-main { flex: 1; min-width: 0; }
.export-right { width: 360px; flex-shrink: 0; }
.template-item { padding: 8px 12px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; transition: all 0.15s; }
.template-item:hover { background: rgba(0,0,0,0.04); }
.template-item.active { background: rgba(196,61,61,0.08); color: var(--vermillion); font-weight: 500; }
.field-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.field-row input, .field-row select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 13px; font-family: var(--font-sans); background: var(--card-bg); color: var(--text); }
.field-row input:focus, .field-row select:focus { outline: none; border-color: var(--vermillion); }
@media (max-width: 900px) { .export-layout { flex-direction: column; } .export-left, .export-right { width: 100%; } }
</style>
