<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">考勤计算</h2>
        <div class="flex gap-sm">
          <button @click="viewMode = 'list'" :class="viewMode === 'list' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm">列表</button>
          <button @click="viewMode = 'calendar'" :class="viewMode === 'calendar' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm">日历</button>
          <button @click="runCalculation" :disabled="calculating" class="btn btn-primary btn-sm">
            {{ calculating ? '计算中...' : '重新计算' }}
          </button>
          <template v-if="role === 'deptadmin' || role === 'hradmin'">
            <button @click="deptSubmit" :disabled="submitting || calculating" class="btn btn-secondary btn-sm">
              {{ submitting ? '提交中...' : '提交部门数据' }}
            </button>
            <button v-if="role === 'hradmin'" @click="lockMonth" :disabled="locking || calculating" class="btn btn-secondary btn-sm">
              {{ locking ? '锁定中...' : '锁定本月' }}
            </button>
          </template>
        </div>
      </div>

      <div v-if="configChanged" class="alert alert-error" style="display:flex;justify-content:space-between;align-items:center">
        <span>考勤规则已变更，当前结果可能不是最新规则计算的。</span>
        <button @click="runCalculation" class="btn btn-primary btn-sm">重新计算</button>
      </div>

      <div v-if="scheduleMissing" class="alert alert-error">
        未找到{{ currentMonth }}排班数据，所有日期默认视为上班日。请前往 <a @click.prevent="router.push('/import')" href="#" style="color:var(--vermillion);font-weight:600;text-decoration:underline">数据导入</a> 上传排班表。
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
        <input v-model="searchName" type="text" placeholder="搜索姓名" style="width:120px">
      </div>

      <AttendanceTable
        v-if="viewMode === 'list'"
        :rows="filteredResults"
        :holiday-map="holidayMap"
        :can-review="role === 'deptadmin' || role === 'hradmin'"
        @show-detail="showDetail"
        @review="reviewRecord"
        @go-import="router.push('/import')"
      />

      <AttendanceCalendar
        v-else
        :cells="calendarCells"
        :employee="calEmployee"
        :employees="calendarEmployees"
        :employee-info="calEmployeeInfo"
        @change-employee="calEmployee = $event; buildCalendar()"
        @show-detail="showDetail"
      />
    </div>

    <div v-if="detail" class="detail-overlay" @click.self="detail = null">
      <div class="detail-modal">
        <div class="flex-between" style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
          <h3 style="font-size:16px;font-weight:600">{{ detail.name }} - {{ detail.date }} 详情</h3>
          <div class="flex gap-sm">
            <template v-if="role === 'deptadmin' || role === 'hradmin'">
              <button v-if="detail.review_status === 'pending_review'" class="btn btn-primary btn-sm" @click="reviewRecord(detail, 'confirmed')">确认</button>
              <button v-if="detail.review_status === 'disputed'" class="btn btn-primary btn-sm" @click="reviewRecord(detail, 'confirmed')">确认</button>
              <button v-if="detail.review_status === 'pending_review'" class="btn btn-ghost btn-sm" style="color:var(--vermillion)" @click="reviewRecord(detail, 'disputed')">申诉</button>
            </template>
            <button class="btn btn-ghost btn-sm" @click="detail = null">关闭</button>
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
          <table class="source-table"><thead><tr><th>类型</th><th>开始</th><th>结束</th><th>天数</th><th>小时</th></tr></thead>
          <tbody><tr v-for="l in detail.sourceLeaves" :key="l.id"><td>{{ l.leaveType }}</td><td>{{ l.startDate }}</td><td>{{ l.endDate }}</td><td>{{ l.leaveDays }}</td><td>{{ l.leaveHours }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceTravels && detail.sourceTravels.length">
          <div class="section-title">关联出差记录</div>
          <table class="source-table"><thead><tr><th>开始</th><th>结束</th><th>目的地</th><th>事由</th></tr></thead>
          <tbody><tr v-for="t in detail.sourceTravels" :key="t.id"><td>{{ t.startDate }}</td><td>{{ t.endDate }}</td><td>{{ t.destination }}</td><td>{{ t.reason }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceMisses && detail.sourceMisses.length">
          <div class="section-title">关联漏打卡说明</div>
          <table class="source-table"><thead><tr><th>日期</th><th>说明</th></tr></thead>
          <tbody><tr v-for="m in detail.sourceMisses" :key="m.id"><td>{{ m.missDate }}</td><td>{{ m.reason }}</td></tr></tbody></table>
        </div>
        <div v-if="detail.sourceOvertimes && detail.sourceOvertimes.length">
          <div class="section-title">关联加班记录</div>
          <table class="source-table"><thead><tr><th>开始</th><th>结束</th><th>小时</th><th>内容</th></tr></thead>
          <tbody><tr v-for="o in detail.sourceOvertimes" :key="o.id"><td>{{ o.startTime }}</td><td>{{ o.endTime }}</td><td>{{ o.overtimeHours }}</td><td>{{ o.content }}</td></tr></tbody></table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import AttendanceTable from '../components/AttendanceTable.vue';
import AttendanceCalendar from '../components/AttendanceCalendar.vue';
import Store from '../shared/store';
import RulesEngine, { RULES_VERSION } from '../shared/rules';
import { apiRequest } from '../shared/api';
import Auth from '../shared/auth';
import { statusLabel, statusBadgeClass, statusColor, reviewStatusLabel } from '../shared/constants';

const router = useRouter();
const role = Auth.getRole();

const viewMode = ref('list');
const calculating = ref(false);
const submitting = ref(false);
const locking = ref(false);
const configChanged = ref(false);
const scheduleMissing = ref(false);
const currentMonth = ref('');
const filterDept = ref('');
const filterStatus = ref('');
const searchName = ref('');
const results = ref([]);
const detail = ref(null);
const departments = ref([]);
const calendarCells = ref([]);
const calEmployee = ref('');
const calendarEmployees = ref([]);
const holidayMap = ref({});

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

onMounted(async () => {
  currentMonth.value = await detectDataMonth();
  await loadResults();
});

watch(currentMonth, () => loadResults());
watch(viewMode, () => { if (viewMode.value === 'calendar') buildCalendar(); });

async function detectDataMonth() {
  const punches = await Store.getAll('punch_records');
  if (!punches.length) {
    const now = new Date();
    return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
  }
  const dates = punches.map(p => { const m = (p.date || '').match(/^(\d{4})-(\d{2})/); return m ? m[1] + '-' + m[2] : null; }).filter(Boolean).sort();
  return dates[dates.length - 1];
}

async function loadResults() {
  let list = await Store.getByIndex('attendance_results', 'month', currentMonth.value);
  if (role === 'deptadmin') {
    const dept = Auth.getDepartment();
    list = list.filter(r => r.department === dept);
  }
  results.value = list;
  if (!results.value.length) {
    const punches = await Store.getAll('punch_records');
    if (punches.some(p => p.date && p.date.startsWith(currentMonth.value))) await runCalculation();
  } else {
    const configEntry = await Store.getByKey('settings', 'config_updated_at');
    if (configEntry && configEntry.value) {
      const calcTime = await Store.getByKey('settings', 'last_calc_' + currentMonth.value);
      if (!calcTime || calcTime.value < configEntry.value) configChanged.value = true;
    }
    const rvEntry = await Store.getByKey('settings', 'rules_version');
    if (!rvEntry || rvEntry.value !== RULES_VERSION) {
      await Store.put('settings', { key: 'rules_version', value: RULES_VERSION });
      await runCalculation();
      return;
    }
  }
  const [y, m] = currentMonth.value.split('-').map(Number);
  const allSchedules = await Store.getAll('schedules');
  const sc = (allSchedules || []).filter(s => s.year === y && s.month === m).length;
  scheduleMissing.value = sc === 0 && results.value.length > 0;
  const holidays = await Store.getAll('holidays');
  holidayMap.value = {};
  for (const h of holidays) { if (h.date && h.date.startsWith(currentMonth.value)) holidayMap.value[h.date] = h; }
  if (viewMode.value === 'calendar') await buildCalendar();
  const es = new Map();
  for (const r of results.value) { if (!es.has(r.employeeNo)) es.set(r.employeeNo, { employeeNo: r.employeeNo, name: r.name, department: r.department }); }
  calendarEmployees.value = [...es.values()].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  const ds = new Set(results.value.map(r => r.department).filter(Boolean));
  departments.value = [...ds].sort();
}

async function runCalculation() {
  calculating.value = true;
  configChanged.value = false;
  try {
    await RulesEngine.calculateMonth(currentMonth.value);
    await Store.put('settings', { key: 'last_calc_' + currentMonth.value, value: Date.now() });
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
  let scheduleMap = {};
  if (calEmployee.value) {
    const allSchedules = await Store.getByIndex('schedules', 'year', y);
    for (const s of allSchedules) { if (s.month === m && s.employeeNo === calEmployee.value) { scheduleMap[calEmployee.value] = s; break; } }
  } else {
    const allSchedules = await Store.getByIndex('schedules', 'year', y);
    for (const s of allSchedules) { if (s.month === m && !scheduleMap[s.employeeNo]) scheduleMap[s.employeeNo] = s; }
  }
  const holidays = await Store.getAll('holidays');
  const holidayMap2 = {};
  for (const h of holidays) { if (h.date && h.date.startsWith(currentMonth.value)) holidayMap2[h.date] = h; }
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
      const st = dayRecords[0].status;
      if (st === 'normal') sc = 'cal-normal';
      else if (st === 'absent') sc = 'cal-absent';
      else if (st === 'rest') sc = 'cal-rest';
      else if (st === 'leave') sc = 'cal-leave';
      else if (st === 'travel') sc = 'cal-travel';
      else if (st === 'overtime' || st === 'suspect_ot') sc = 'cal-overtime';
      else sc = 'cal-abnormal';
    } else if (isRest || h) { sc = 'cal-rest'; }
    cells.push({ key: ds, day: String(d).padStart(2, '0'), isRest, record: dayRecords[0] || null, statusClass: sc, holidayName });
  }
  calendarCells.value = cells;
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
.cal-cell { min-height: 76px; border-radius: var(--radius-sm); transition: all 0.15s; cursor: pointer; padding: 4px 6px; font-size: 12px; }
.cal-cell:hover { transform: scale(1.03); z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.cal-cell.cal-normal { background: rgba(45,125,70,0.06); border: 1px solid rgba(45,125,70,0.2); }
.cal-cell.cal-abnormal { background: rgba(196,61,61,0.06); border: 1px solid rgba(196,61,61,0.15); }
.cal-cell.cal-absent { background: rgba(196,61,61,0.1); border: 1px solid rgba(196,61,61,0.25); }
.cal-cell.cal-rest { background: rgba(0,0,0,0.03); border: 1px solid var(--border); }
.cal-cell.cal-leave { background: rgba(59,89,152,0.06); border: 1px solid rgba(59,89,152,0.2); }
.cal-cell.cal-travel { background: rgba(139,94,60,0.06); border: 1px solid rgba(139,94,60,0.2); }
.cal-cell.cal-overtime { background: rgba(201,169,110,0.1); border: 1px solid rgba(201,169,110,0.3); }
.cal-cell.cal-unknown { background: rgba(0,0,0,0.02); border: 1px solid var(--border); }
.cal-day { font-size: 13px; font-weight: 600; }
.cal-time { font-size: 11px; color: var(--text-secondary); }
.cal-status { font-size: 10px; font-weight: 600; margin-top: 2px; }
.detail-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 200; }
.detail-modal { background: var(--card-bg); border-radius: var(--radius-xl); box-shadow: 0 16px 48px rgba(44,36,22,0.15); width: 90vw; max-width: 720px; max-height: 85vh; overflow-y: auto; padding: 24px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.detail-grid .dg-label { font-size: 12px; color: var(--text-secondary); }
.detail-grid .dg-value { font-size: 14px; font-weight: 500; }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; margin-top: 16px; }
.source-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.source-table th { background: var(--paper); padding: 4px 8px; text-align: left; border: 1px solid var(--border); font-weight: 600; }
.source-table td { padding: 4px 8px; border: 1px solid var(--border); }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 16px; }
.filter-bar input, .filter-bar select { padding: 6px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 13px; font-family: var(--font-sans); background: var(--card-bg); color: var(--text); }
.filter-bar input:focus, .filter-bar select:focus { outline: none; border-color: var(--vermillion); }
</style>
