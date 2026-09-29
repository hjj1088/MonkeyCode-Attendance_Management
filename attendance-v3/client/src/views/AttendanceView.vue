<template>
  <div class="attendance-page" :class="{ 'is-calendar': viewMode === 'calendar', 'is-list': viewMode === 'list' }">
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">考勤计算</h2>
        <div class="flex gap-sm">
          <button @click="viewMode = 'list'" :class="viewMode === 'list' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm">
            <AppIcon name="list" /><span>列表</span>
          </button>
          <button @click="viewMode = 'calendar'" :class="viewMode === 'calendar' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm">
            <AppIcon name="calendar" /><span>日历</span>
          </button>
          <button @click="runCalculation" :disabled="calculating" class="btn btn-primary btn-sm">
            <AppIcon name="refresh" /><span>{{ calculating ? '计算中...' : '重新计算' }}</span>
          </button>
          <template v-if="role === 'deptadmin' || role === 'hradmin' || role === 'superadmin'">
            <button @click="deptSubmit" :disabled="submitting || calculating" class="btn btn-secondary btn-sm">
              <AppIcon name="upload" /><span>{{ submitting ? '提交中...' : '提交部门数据' }}</span>
            </button>
            <button v-if="role === 'hradmin' || role === 'superadmin'" @click="lockMonth" :disabled="locking || calculating" class="btn btn-secondary btn-sm">
              <AppIcon name="lock" /><span>{{ locking ? '锁定中...' : '锁定本月' }}</span>
            </button>
          </template>
        </div>
      </div>

      <div v-if="configChanged" class="alert alert-error" style="display:flex;justify-content:space-between;align-items:center">
        <span>考勤规则已变更，当前结果可能不是最新规则计算的。</span>
        <button @click="runCalculation" class="btn btn-primary btn-sm"><AppIcon name="refresh" /><span>重新计算</span></button>
      </div>

      <div v-if="noResults" class="alert alert-error" style="display:flex;justify-content:space-between;align-items:center">
        <span>{{ currentMonth }} {{ role === 'deptadmin' ? '暂无本部门考勤数据' : '尚未计算考勤结果，请点击重新计算' }}</span>
        <button @click="runCalculation" class="btn btn-primary btn-sm"><AppIcon name="refresh" /><span>重新计算</span></button>
      </div>

      <div v-if="scheduleMissing" class="alert alert-error">
        未找到{{ currentMonth }}排班数据，所有日期默认视为上班日。请前往 <a @click.prevent="router.push('/import')" href="#" class="link-accent">数据导入</a> 上传排班表。
      </div>

      <div class="filter-bar">
        <input v-model="currentMonth" type="month">
        <select v-model="filterDept">
          <option value="">全部部门</option>
          <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="filterStatus">
          <option value="">全部状态</option>
          <option value="normal">正常</option>
          <option value="rest">休息</option>
          <option value="abnormal">迟到</option>
          <option value="leave">请假</option>
          <option value="travel">出差</option>
          <option value="absent">缺勤</option>
          <option value="overtime">疑似加班</option>
          <option value="suspect_ot">疑似加班</option>
        </select>
        <input v-model="searchInput" type="text" placeholder="搜索姓名" style="width:120px">
        <button @click="applySearch" class="btn btn-primary btn-sm"><AppIcon name="search" /><span>查询</span></button>
        <template v-if="viewMode === 'calendar'">
          <span class="filter-label">当前员工:</span>
          <button class="cal-nav" :disabled="!calendarEmployees.length" aria-label="上一个员工" @click="moveCalEmployee(-1)"><AppIcon name="chevron-left" :size="16" /></button>
          <select v-model="calEmployee" @change="buildCalendar">
            <option value="">-- 全部 --</option>
            <option v-for="emp in calendarEmployees" :key="emp.employeeNo" :value="emp.employeeNo">{{ emp.name }} ({{ emp.employeeNo }})</option>
          </select>
          <button class="cal-nav" :disabled="!calendarEmployees.length" aria-label="下一个员工" @click="moveCalEmployee(1)"><AppIcon name="chevron-right" :size="16" /></button>
          <span v-if="calEmployee && calEmployeeInfo" class="filter-label">{{ calEmployeeInfo.department }}</span>
        </template>
      </div>

      <AttendanceTable
        v-if="viewMode === 'list'"
        class="table-panel"
        :rows="pagedResults"
        :holiday-map="holidayMap"
        :can-review="role === 'deptadmin' || role === 'hradmin' || role === 'superadmin'"
        :empty-hint="tableEmptyHint"
        @show-detail="showDetail"
        @review="reviewRecord"
        @go-import="router.push('/import')"
      />
      <div v-if="viewMode === 'list' && filteredResults.length" class="pager">
        <span class="pager-info">共 {{ filteredResults.length }} 条</span>
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

      <AttendanceCalendar
        v-else
        class="cal-panel"
        :cells="calendarCells"
        @show-detail="showDetail"
      />
    </div>

    <div v-if="detail" class="detail-overlay" @click.self="detail = null">
      <div class="detail-modal">
        <div class="flex-between" style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
          <h3 style="font-size:16px;font-weight:600">{{ detail.name }} - {{ detail.date }} 详情</h3>
          <div class="flex gap-sm">
            <template v-if="role === 'deptadmin' || role === 'hradmin' || role === 'superadmin'">
              <button v-if="detail.review_status === 'pending_review'" class="btn btn-primary btn-sm" @click="reviewRecord(detail, 'confirmed')"><AppIcon name="check" /><span>确认</span></button>
              <button v-if="detail.review_status === 'disputed'" class="btn btn-primary btn-sm" @click="reviewRecord(detail, 'confirmed')"><AppIcon name="check" /><span>确认</span></button>
              <button v-if="detail.review_status === 'pending_review'" class="btn btn-danger btn-sm" @click="reviewRecord(detail, 'disputed')"><AppIcon name="alert" /><span>申诉</span></button>
            </template>
            <button class="btn btn-ghost btn-sm" @click="detail = null"><AppIcon name="close" /><span>关闭</span></button>
          </div>
        </div>
        <div class="detail-grid">
          <div><span class="dg-label">考勤号</span><div class="dg-value">{{ detail.employeeNo }}</div></div>
          <div><span class="dg-label">部门</span><div class="dg-value">{{ detail.department }}</div></div>
          <div><span class="dg-label">签到</span><div class="dg-value">{{ detail.signIn || '--' }}</div></div>
          <div><span class="dg-label">签退</span><div class="dg-value">{{ detail.signOut || '--' }}</div></div>
          <div><span class="dg-label">迟到</span><div class="dg-value">{{ detail.lateMinutes }}min</div></div>
          <div><span class="dg-label">早退</span><div class="dg-value">{{ detail.earlyMinutes }}min</div></div>
          <div><span class="dg-label">加班</span><div class="dg-value">{{ detail.overtimeHours }}h</div></div>
          <div><span class="dg-label">出差</span><div class="dg-value">{{ detail.travelHours }}h</div></div>
          <div><span class="dg-label">请假类型</span><div class="dg-value">{{ detail.leaveType || '--' }} <span v-if="detail.leaveHours">({{ detail.leaveHours }}h)</span></div></div>
          <div><span class="dg-label">状态</span><div class="dg-value"><span class="badge" :class="statusBadgeClass(detail.status)">{{ statusLabel(detail.status) }}</span></div></div>
          <div><span class="dg-label">排班</span><div class="dg-value">{{ detail.isRestDay ? '休息' : '上班' }}</div></div>
          <div><span class="dg-label">审核状态</span><div class="dg-value"><span class="badge" :class="reviewBadgeClass(detail.review_status)">{{ reviewStatusLabel(detail.review_status) }}</span></div></div>
        </div>
        <div v-if="detail.sourcePunches && detail.sourcePunches.length">
          <div class="section-title">关联打卡记录</div>
          <table class="source-table"><thead><tr><th>签到</th><th>签退</th><th>迟到</th><th>早退</th></tr></thead>
          <tbody><tr v-for="p in detail.sourcePunches" :key="p.id"><td>{{ p.signIn }}</td><td>{{ p.signOut }}</td><td>{{ p.lateMinutes }}</td><td>{{ p.earlyMinutes }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceLeaves && detail.sourceLeaves.length">
          <div class="section-title">关联请假记录</div>
          <table class="source-table"><thead><tr><th>类型</th><th>申请人</th><th>受益人</th><th>开始</th><th>结束</th><th>天数</th><th>小时</th></tr></thead>
          <tbody><tr v-for="l in detail.sourceLeaves" :key="l.id"><td>{{ l.leaveType }}</td><td>{{ l.applicant }}</td><td>{{ l.subject || l.applicant }}</td><td>{{ l.startDate }}</td><td>{{ l.endDate }}</td><td>{{ l.leaveDays }}</td><td>{{ l.leaveHours }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceTravels && detail.sourceTravels.length">
          <div class="section-title">关联出差记录</div>
          <table class="source-table"><thead><tr><th>申请人</th><th>受益人</th><th>开始</th><th>结束</th><th>目的地</th><th>事由</th></tr></thead>
          <tbody><tr v-for="t in detail.sourceTravels" :key="t.id"><td>{{ t.applicant }}</td><td>{{ t.subject || t.travelers || t.applicant }}</td><td>{{ t.startDate }}</td><td>{{ t.endDate }}</td><td>{{ t.destination }}</td><td>{{ t.reason }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceMisses && detail.sourceMisses.length">
          <div class="section-title">关联漏打卡说明</div>
          <table class="source-table"><thead><tr><th>申请人</th><th>受益人</th><th>日期</th><th>说明</th></tr></thead>
          <tbody><tr v-for="m in detail.sourceMisses" :key="m.id"><td>{{ m.applicant }}</td><td>{{ m.subject || m.missPerson || m.applicant }}</td><td>{{ m.missDate }}</td><td>{{ m.reason }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceOvertimes && detail.sourceOvertimes.length">
          <div class="section-title">关联加班记录</div>
          <table class="source-table"><thead><tr><th>申请人</th><th>受益人</th><th>开始</th><th>结束</th><th>小时</th><th>内容</th></tr></thead>
          <tbody><tr v-for="o in detail.sourceOvertimes" :key="o.id"><td>{{ o.applicant }}</td><td>{{ o.subject || o.applicant }}</td><td>{{ o.startTime }}</td><td>{{ o.endTime }}</td><td>{{ o.overtimeHours }}</td><td>{{ o.content }}</td></tr></tbody></table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject } from 'vue';
import { useRouter } from 'vue-router';
import AttendanceTable from '../components/AttendanceTable.vue';
import AttendanceCalendar from '../components/AttendanceCalendar.vue';
import AppIcon from '../components/AppIcon.vue';
import Store from '../shared/store';
import RulesEngine, { RULES_VERSION } from '../shared/rules';
import { apiRequest } from '../shared/api';
import Auth from '../shared/auth';
import { statusLabel, statusBadgeClass, statusColor, reviewStatusLabel, calCellClass } from '../shared/constants';

const router = useRouter();
const role = Auth.getRole();

const viewMode = ref('list');
const calculating = ref(false);
const submitting = ref(false);
const locking = ref(false);
const configChanged = ref(false);
const scheduleMissing = ref(false);
const noResults = ref(false);
const currentMonth = ref('');
const filterDept = ref('');
const filterStatus = ref('');
const searchName = ref('');
const searchInput = ref('');
const initialCalSet = ref(false);
const results = ref([]);
const detail = ref(null);
const departments = ref([]);
const calendarCells = ref([]);
const calEmployee = ref('');
const calendarEmployees = ref([]);
const holidayMap = ref({});
const allSchedules = ref([]);
const holidaysData = ref([]);

const filteredResults = computed(() => {
  let list = results.value;
  if (filterDept.value) list = list.filter(r => r.department === filterDept.value);
  if (filterStatus.value) list = list.filter(r => r.status === filterStatus.value);
  if (searchName.value) list = list.filter(r => r.name.includes(searchName.value));
  list = [...list].sort((a, b) => {
    if (a.employeeNo !== b.employeeNo) {
      const na = parseInt(a.employeeNo) || 0;
      const nb = parseInt(b.employeeNo) || 0;
      if (na !== nb) return na - nb;
      return String(a.employeeNo).localeCompare(String(b.employeeNo));
    }
    if (a.department !== b.department) return a.department.localeCompare(b.department);
    return a.date.localeCompare(b.date);
  });
  return list;
});

const calEmployeeInfo = computed(() => {
  if (!calEmployee.value) return null;
  const r = results.value.find(r => r.employeeNo === calEmployee.value);
  return r ? { name: r.name, department: r.department } : null;
});

const PREF_KEY = 'attendance.listPrefs';
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
if (prefs.viewMode === 'list' || prefs.viewMode === 'calendar') viewMode.value = prefs.viewMode;

const totalPages = computed(() => Math.max(1, Math.ceil(filteredResults.value.length / pageSize.value)));
const pagedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredResults.value.slice(start, start + pageSize.value);
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
  localStorage.setItem(PREF_KEY, JSON.stringify({ pageSize: pageSize.value, viewMode: viewMode.value }));
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

const tableEmptyHint = computed(() => {
  if (noResults.value) return '';
  return undefined;
});

const setContextChip = inject('setContextChip', () => {});

function applySearch() {
  searchName.value = searchInput.value.trim();
  currentPage.value = 1;
}

function moveCalEmployee(dir) {
  const list = calendarEmployees.value;
  if (!list.length) return;
  let i = list.findIndex(e => e.employeeNo === calEmployee.value);
  if (i < 0) i = dir > 0 ? -1 : list.length;
  calEmployee.value = list[(i + dir + list.length) % list.length].employeeNo;
  buildCalendar();
}

onMounted(async () => {
  const settingsList = await Store.getAll('settings');
  const settingsMap = {};
  for (const s of settingsList || []) settingsMap[s.key] = s.value;
  currentMonth.value = await detectDataMonth(settingsMap);
  setContextChip(currentMonth.value || '');
  await loadResults(settingsMap);
});

watch(currentMonth, (m) => { setContextChip(m || ''); currentPage.value = 1; loadResults(); });
watch(viewMode, () => {
  savePrefs();
  if (viewMode.value === 'calendar') buildCalendar();
});
watch([filterDept, filterStatus], () => { currentPage.value = 1; });
watch(totalPages, (n) => { if (currentPage.value > n) currentPage.value = n; });
onUnmounted(() => setContextChip(''));

async function detectDataMonth(settingsMap) {
  let m = null;
  if (settingsMap && settingsMap.last_punch_month) m = settingsMap.last_punch_month;
  if (!m) {
    const files = await Store.getAll('raw_files');
    const punchFile = (files || [])
      .filter(f => f.fileType === 'punch')
      .sort((a, b) => String(b.importTime || '').localeCompare(String(a.importTime || '')))[0];
    if (punchFile && punchFile.fileName) {
      const mm = String(punchFile.fileName).match(/(\d{4})\s*年\s*(\d{1,2})\s*月/);
      if (mm) m = mm[1] + '-' + String(Number(mm[2])).padStart(2, '0');
    }
  }
  if (!m) {
    const punches = await Store.getAll('punch_records');
    if (!punches.length) {
      const now = new Date();
      m = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
    } else {
      const dates = punches.map(p => { const mm = (p.date || '').match(/^(\d{4})-(\d{2})/); return mm ? mm[1] + '-' + mm[2] : null; }).filter(Boolean).sort();
      m = dates[dates.length - 1];
    }
  }
  if (role === 'deptadmin') {
    const dept = Auth.getDepartment();
    const monthResults = await Store.getByIndex('attendance_results', 'month', m);
    const hasDept = (monthResults || []).some(r => r.department === dept);
    if (!hasDept) {
      const all = await Store.getAll('attendance_results');
      const months = [...new Set(all.filter(r => r.department === dept).map(r => r.month))].sort();
      if (months.length) m = months[months.length - 1];
    }
  }
  return m;
}

async function loadResults(settingsMap) {
  if (!settingsMap) {
    const settingsList = await Store.getAll('settings');
    settingsMap = {};
    for (const s of settingsList || []) settingsMap[s.key] = s.value;
  }
  const [list, schedules, holidays] = await Promise.all([
    Store.getByIndex('attendance_results', 'month', currentMonth.value),
    Store.getAll('schedules'),
    Store.getAll('holidays'),
  ]);
  allSchedules.value = schedules || [];
  holidaysData.value = holidays || [];
  let filtered = list || [];
  if (role === 'deptadmin') {
    const dept = Auth.getDepartment();
    filtered = filtered.filter(r => r.department === dept);
  }
  results.value = filtered;

  configChanged.value = false;
  noResults.value = false;
  if (filtered.length) {
    const cfgTime = settingsMap.config_updated_at;
    if (cfgTime) {
      const calcTime = settingsMap['last_calc_' + currentMonth.value];
      if (!calcTime || calcTime < cfgTime) configChanged.value = true;
    }
    if (!settingsMap.rules_version || settingsMap.rules_version !== RULES_VERSION) {
      configChanged.value = true;
    }
  } else {
    const punches = await Store.getByRange('punch_records', 'date', currentMonth.value + '-01', currentMonth.value + '-31');
    if (punches && punches.length) noResults.value = true;
  }

  const [y, m] = currentMonth.value.split('-').map(Number);
  const sc = allSchedules.value.filter(s => s.year === y && s.month === m).length;
  scheduleMissing.value = sc === 0 && results.value.length > 0;
  holidayMap.value = {};
  for (const h of holidaysData.value) { if (h.date && h.date.startsWith(currentMonth.value)) holidayMap.value[h.date] = h; }
  if (viewMode.value === 'calendar') buildCalendar();
  const es = new Map();
  for (const r of results.value) { if (!es.has(r.employeeNo)) es.set(r.employeeNo, { employeeNo: r.employeeNo, name: r.name, department: r.department }); }
  calendarEmployees.value = [...es.values()].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  if (!initialCalSet.value) {
    if (calendarEmployees.value.length) { calEmployee.value = calendarEmployees.value[0].employeeNo; initialCalSet.value = true; }
  } else if (calEmployee.value && !calendarEmployees.value.some(e => e.employeeNo === calEmployee.value)) {
    calEmployee.value = calendarEmployees.value.length ? calendarEmployees.value[0].employeeNo : '';
  }
  const ds = new Set(results.value.map(r => r.department).filter(Boolean));
  departments.value = [...ds].sort();
}

async function runCalculation() {
  calculating.value = true;
  configChanged.value = false;
  noResults.value = false;
  try {
    await RulesEngine.calculateMonth(currentMonth.value);
    await Store.put('settings', { key: 'last_calc_' + currentMonth.value, value: Date.now() });
    await Store.put('settings', { key: 'rules_version', value: RULES_VERSION });
    await loadResults();
  } catch (err) {
    alert('计算出错: ' + err.message);
  }
  calculating.value = false;
}

async function buildCalendar() {
  const [y, m] = currentMonth.value.split('-').map(Number);
  const firstDay = new Date(y, m - 1, 1);
  const lastDate = new Date(y, m, 0).getDate();
  const startDow = firstDay.getDay() || 7;
  const cells = [];
  const scheduleMap = {};
  const yearSchedules = allSchedules.value.filter(s => s.year === y && s.month === m);
  if (calEmployee.value) {
    for (const s of yearSchedules) { if (s.employeeNo === calEmployee.value) { scheduleMap[calEmployee.value] = s; break; } }
  } else {
    for (const s of yearSchedules) { if (!scheduleMap[s.employeeNo]) scheduleMap[s.employeeNo] = s; }
  }
  const holidayMap2 = {};
  for (const h of holidaysData.value) { if (h.date && h.date.startsWith(currentMonth.value)) holidayMap2[h.date] = h; }
  const today = new Date();
  for (let i = 1; i < startDow; i++) cells.push({ key: 'prev-' + i, day: '', isRest: false, record: null, statusClass: 'cal-unknown' });
  for (let d = 1; d <= lastDate; d++) {
    const ds = currentMonth.value + '-' + String(d).padStart(2, '0');
    const dayRecords = results.value.filter(r => { if (calEmployee.value && r.employeeNo !== calEmployee.value) return false; return r.date === ds; });
    const dayStr = String(d).padStart(2, '0');
    let isRest = false, holidayName = null;
    const h = holidayMap2[ds];
    if (h) { isRest = !h.isWorkday; holidayName = h.name; }
    else if (calEmployee.value) { const sch = scheduleMap[calEmployee.value]; if (sch && sch.workDays) isRest = sch.workDays[dayStr] !== true; }
    else { let allRest = true, hasSched = false; const enos = [...new Set(results.value.map(r => r.employeeNo))]; for (const eno of enos) { const sch = scheduleMap[eno]; if (sch && sch.workDays) { hasSched = true; if (sch.workDays[dayStr]) allRest = false; } } isRest = hasSched && allRest; }
    let sc = 'cal-unknown';
    if (dayRecords.length) {
      sc = calCellClass(dayRecords[0].status);
    } else if (isRest || h) { sc = 'cal-rest'; }
    const isToday = today.getFullYear() === y && today.getMonth() + 1 === m && today.getDate() === d;
    cells.push({ key: ds, day: String(d).padStart(2, '0'), isRest, record: dayRecords[0] || null, statusClass: sc, holidayName, isToday });
  }
  calendarCells.value = cells;
}

function reviewBadgeClass(s) {
  const m = {
    pending_review: '',
    confirmed: 'badge-normal',
    submitted: 'badge-travel',
    locked: 'badge-late',
    disputed: 'badge-nosign',
  };
  return m[s] || '';
}

async function showDetail(r) {
  detail.value = await RulesEngine.getResultDetail(r.employeeNo, r.date);
}

async function reviewRecord(r, newStatus) {
  if (!r.id) { alert('该记录缺少 ID，无法操作'); return; }
  try {
    await apiRequest('/attendance/' + r.id + '/review', {
      method: 'PATCH',
      body: JSON.stringify({ review_status: newStatus }),
    });
    await loadResults();
    if (detail.value && detail.value.id === r.id) {
      detail.value.review_status = newStatus;
    }
  } catch (err) {
    alert(err.message || '操作失败');
  }
}

async function deptSubmit() {
  if (!confirm('确认将 ' + currentMonth.value + ' 已确认记录提交为部门数据？提交后不可再修改。')) return;
  submitting.value = true;
  try {
    const res = await apiRequest('/attendance/dept/submit', {
      method: 'PATCH',
      body: JSON.stringify({ month: currentMonth.value }),
    });
    alert('已提交 ' + res.submitted + ' 条记录');
    await loadResults();
  } catch (err) {
    alert(err.message || '提交失败');
  }
  submitting.value = false;
}

async function lockMonth() {
  if (!confirm('确定锁定 ' + currentMonth.value + ' 数据？锁定后所有记录不可再变更。')) return;
  locking.value = true;
  try {
    const res = await apiRequest('/attendance/lock', {
      method: 'PATCH',
      body: JSON.stringify({ month: currentMonth.value }),
    });
    alert('已锁定 ' + res.locked + ' 条记录');
    await loadResults();
  } catch (err) {
    alert(err.message || '锁定失败');
  }
  locking.value = false;
}
</script>

<style scoped>
.attendance-page.is-calendar,
.attendance-page.is-list { flex: 1; width: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.attendance-page.is-calendar .card,
.attendance-page.is-list .card { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; margin-bottom: 0; }
.attendance-page.is-calendar .card-header,
.attendance-page.is-calendar .filter-bar,
.attendance-page.is-list .card-header,
.attendance-page.is-list .filter-bar,
.attendance-page.is-list .alert,
.attendance-page.is-list .pager { flex-shrink: 0; }
.cal-panel,
.table-panel { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
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
.detail-modal { background: var(--card-bg); border-radius: var(--radius-xl); box-shadow: var(--shadow-lg); width: 90vw; max-width: 720px; max-height: 85vh; overflow-y: auto; padding: 24px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.detail-grid .dg-label { font-size: 12px; color: var(--ink-secondary); }
.detail-grid .dg-value { font-size: 14px; font-weight: 500; }
.section-title { font-size: 13px; font-weight: 600; color: var(--ink-secondary); margin-bottom: 8px; margin-top: 16px; }
.source-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.source-table th { background: var(--table-head); padding: 4px 8px; text-align: left; border: 1px solid var(--border); font-weight: 600; }
.source-table td { padding: 4px 8px; border: 1px solid var(--border); }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 16px; }
.filter-bar input, .filter-bar select { padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-md); font-size: 14px; font-family: var(--font-sans); background: var(--card-bg); color: var(--ink); }
.filter-bar input:focus, .filter-bar select:focus { outline: none; border-color: var(--celadon); box-shadow: 0 0 0 3px rgba(61, 90, 102, 0.12); }
.filter-label { font-size: 13px; color: var(--ink-secondary); }
.cal-nav { width: 26px; height: 30px; line-height: 1; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--card-bg); color: var(--ink); font-size: 18px; cursor: pointer; font-family: var(--font-sans); display: inline-flex; align-items: center; justify-content: center; padding: 0; }
.cal-nav:hover:not(:disabled) { border-color: var(--celadon); color: var(--celadon); }
.cal-nav:disabled { opacity: 0.4; cursor: not-allowed; }
.link-accent { color: var(--celadon); font-weight: 600; text-decoration: underline; cursor: pointer; }
</style>
