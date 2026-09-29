<template>
  <div class="my-attendance" :class="{ 'is-calendar': viewMode === 'calendar' }">
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">我的考勤</h2>
        <div class="flex gap-sm">
          <button @click="viewMode = 'list'" :class="viewMode === 'list' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm"><AppIcon name="list" /><span>列表</span></button>
          <button @click="viewMode = 'calendar'" :class="viewMode === 'calendar' ? 'btn-primary' : 'btn-secondary'" class="btn btn-sm"><AppIcon name="calendar" /><span>日历</span></button>
          <input v-model="currentMonth" type="month" class="form-input" style="width:auto">
        </div>
      </div>

      <div v-if="summary" class="stats-row">
        <div class="stat-card"><div class="stat-icon is-jade">出</div><div class="stat-meta"><span class="stat-label">正常出勤</span><span class="stat-value">{{ summary.workDays }}</span></div></div>
        <div class="stat-card"><div class="stat-icon is-late">迟</div><div class="stat-meta"><span class="stat-label">迟到</span><span class="stat-value">{{ summary.lateCount }}</span></div></div>
        <div class="stat-card"><div class="stat-icon is-miss">缺</div><div class="stat-meta"><span class="stat-label">缺卡</span><span class="stat-value">{{ summary.absentDays }}</span></div></div>
        <div class="stat-card"><div class="stat-icon is-leave">假</div><div class="stat-meta"><span class="stat-label">请假出差</span><span class="stat-value">{{ summary.leaveDays + summary.travelDays }}</span></div></div>
      </div>

      <div v-if="viewMode === 'list'" class="table-wrap">
        <StickyTable :cols="myCols" min-width="960px">
          <template #head>
            <tr>
              <th>日期</th><th>排班</th><th>签到</th><th>签退</th>
              <th>迟到(min)</th><th>早退(min)</th><th>加班(h)</th><th>备注</th><th>状态</th><th>审核</th>
            </tr>
          </template>
          <tr v-for="r in rows" :key="r.date" class="row-click" @click="showDetail(r)">
            <td>{{ r.date }}</td>
            <td>{{ r.isRestDay ? '休息' : '上班' }}</td>
            <td>{{ r.signIn || '--' }}</td>
            <td>{{ r.signOut || '--' }}</td>
            <td>{{ r.lateMinutes || 0 }}</td>
            <td>{{ r.earlyMinutes || 0 }}</td>
            <td>{{ r.overtimeHours || 0 }}</td>
            <td class="c-note">{{ remarkText(r) }}</td>
            <td><span class="badge" :class="statusBadgeClass(r.status)">{{ statusLabel(r.status) }}</span></td>
            <td><span class="badge" :class="reviewBadgeClass(r.review_status)">{{ reviewStatusLabel(r.review_status) }}</span></td>
          </tr>
        </StickyTable>
      </div>
      <AttendanceCalendar
        v-else
        class="cal-panel"
        :cells="calendarCells"
        :employee="''"
        :employees="[]"
        :employee-info="null"
        :show-filter="false"
        @show-detail="showDetail"
      />
      <div v-if="rows.length === 0" class="text-center empty-hint">
        {{ currentMonth }} 暂无考勤数据，请联系管理员处理。
      </div>
    </div>

    <div v-if="detail" class="detail-overlay" @click.self="detail = null">
      <div class="detail-modal">
        <div class="flex-between" style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
          <h3 style="font-size:16px;font-weight:600">{{ detail.date }} 详情</h3>
          <button class="btn btn-ghost btn-sm" @click="detail = null"><AppIcon name="close" /><span>关闭</span></button>
        </div>
        <div class="detail-grid">
          <div><span class="dg-label">签到</span><div class="dg-value">{{ detail.signIn || '--' }}</div></div>
          <div><span class="dg-label">签退</span><div class="dg-value">{{ detail.signOut || '--' }}</div></div>
          <div><span class="dg-label">迟到</span><div class="dg-value">{{ detail.lateMinutes }}min</div></div>
          <div><span class="dg-label">早退</span><div class="dg-value">{{ detail.earlyMinutes }}min</div></div>
          <div><span class="dg-label">加班</span><div class="dg-value">{{ detail.overtimeHours }}h</div></div>
          <div><span class="dg-label">状态</span><div class="dg-value"><span class="badge" :class="statusBadgeClass(detail.status)">{{ statusLabel(detail.status) }}</span></div></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject } from 'vue';
import { apiRequest } from '../shared/api';
import Store from '../shared/store';
import { statusLabel, statusBadgeClass, remarkText, reviewStatusLabel, calCellClass } from '../shared/constants';
import AttendanceCalendar from '../components/AttendanceCalendar.vue';
import StickyTable from '../components/StickyTable.vue';
import AppIcon from '../components/AppIcon.vue';

const myCols = ['100px', '64px', '72px', '72px', '88px', '88px', '72px', '120px', '72px', '80px'];
const currentMonth = ref('');
const viewMode = ref('calendar');
const rows = ref([]);
const detail = ref(null);
const calendarCells = ref([]);
const holidaysData = ref([]);
const setContextChip = inject('setContextChip', () => {});

const summary = computed(() => {
  const rs = rows.value;
  const s = { workDays: 0, restDays: 0, lateCount: 0, leaveDays: 0, travelDays: 0, absentDays: 0, overtimeHours: 0 };
  for (const r of rs) {
    if (r.isRestDay) s.restDays++;
    else s.workDays++;
    if (r.status === 'abnormal') s.lateCount++;
    if (r.status === 'leave') s.leaveDays++;
    if (r.status === 'travel') s.travelDays++;
    if (r.absent) s.absentDays++;
    s.overtimeHours += r.overtimeHours || 0;
  }
  s.overtimeHours = Math.round(s.overtimeHours * 100) / 100;
  return s;
});

onMounted(async () => {
  currentMonth.value = await detectDataMonth();
});

async function detectDataMonth() {
  try {
    const data = await apiRequest('/attendance/data-month');
    if (data && data.month) return data.month;
  } catch (e) { /* 回退当月 */ }
  const now = new Date();
  return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
}

watch(currentMonth, (m) => { setContextChip(m || ''); if (m) load(); });
watch(viewMode, () => { if (viewMode.value === 'calendar') buildCalendar(); });
onUnmounted(() => setContextChip(''));

async function load() {
  try {
    const [list, holidays] = await Promise.all([
      apiRequest('/attendance/my?month=' + encodeURIComponent(currentMonth.value)),
      Store.getAll('holidays'),
    ]);
    rows.value = list || [];
    holidaysData.value = holidays || [];
  } catch (err) {
    rows.value = [];
  }
  if (viewMode.value === 'calendar') buildCalendar();
}

function buildCalendar() {
  const [y, m] = currentMonth.value.split('-').map(Number);
  const firstDay = new Date(y, m - 1, 1);
  const lastDate = new Date(y, m, 0).getDate();
  const startDow = firstDay.getDay() || 7;
  const byDate = new Map(rows.value.map(r => [r.date, r]));
  const holidayMap = {};
  for (const h of holidaysData.value) {
    if (h.date && h.date.startsWith(currentMonth.value) && h.name) holidayMap[h.date] = h.name;
  }
  const cells = [];
  for (let i = 1; i < startDow; i++) cells.push({ key: 'prev-' + i, day: '', isRest: false, record: null, statusClass: 'cal-unknown' });
  for (let d = 1; d <= lastDate; d++) {
    const ds = currentMonth.value + '-' + String(d).padStart(2, '0');
    const rec = byDate.get(ds) || null;
    let sc = rec ? calCellClass(rec.status) : 'cal-unknown';
    const today = new Date();
    const isToday = today.getFullYear() === y && today.getMonth() + 1 === m && today.getDate() === d;
    cells.push({ key: ds, day: String(d).padStart(2, '0'), isRest: rec ? !!rec.isRestDay : false, record: rec, statusClass: sc, holidayName: holidayMap[ds] || null, isToday });
  }
  calendarCells.value = cells;
}

function reviewBadgeClass(s) {
  const m = { pending_review: '', confirmed: 'badge-normal', submitted: 'badge-travel', locked: 'badge-late', disputed: 'badge-nosign' };
  return m[s] || '';
}

async function showDetail(r) {
  detail.value = r;
}
</script>

<style scoped>
.my-attendance { flex: 1; width: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.my-attendance .card { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; margin-bottom: 0; }
.my-attendance .card-header,
.my-attendance .stats-row { flex-shrink: 0; }
.cal-panel { flex: 1; min-height: 0; }
.table-wrap { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.row-click { cursor: pointer; }
.c-note { font-size: 12px; }
.empty-hint { padding: 40px; color: var(--ink-secondary); font-size: 14px; }
.detail-overlay { position: fixed; inset: 0; background: rgba(43, 58, 66, 0.45); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); }
.detail-modal { background: var(--card-bg); border-radius: var(--radius-xl); box-shadow: var(--shadow-lg); width: 90vw; max-width: 520px; max-height: 85vh; overflow-y: auto; padding: 24px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-grid .dg-label { font-size: 12px; color: var(--ink-secondary); }
.detail-grid .dg-value { font-size: 14px; font-weight: 500; }
</style>
