<template>
  <div>
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">我的考勤</h2>
        <input v-model="currentMonth" type="month" style="padding:6px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:var(--font-sans);background:var(--card-bg);color:var(--text)">
      </div>

      <div v-if="summary" class="flex gap-md" style="margin-bottom:16px;flex-wrap:wrap">
        <div class="stat-chip"><span class="sc-label">出勤天数</span><span class="sc-value">{{ summary.workDays }}</span></div>
        <div class="stat-chip"><span class="sc-label">休息天数</span><span class="sc-value">{{ summary.restDays }}</span></div>
        <div class="stat-chip"><span class="sc-label">迟到</span><span class="sc-value">{{ summary.lateCount }}</span></div>
        <div class="stat-chip"><span class="sc-label">请假</span><span class="sc-value">{{ summary.leaveDays }}</span></div>
        <div class="stat-chip"><span class="sc-label">出差</span><span class="sc-value">{{ summary.travelDays }}</span></div>
        <div class="stat-chip"><span class="sc-label">缺勤</span><span class="sc-value">{{ summary.absentDays }}</span></div>
        <div class="stat-chip"><span class="sc-label">加班</span><span class="sc-value">{{ summary.overtimeHours }}h</span></div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th><th>排班</th><th>签到</th><th>签退</th>
              <th>迟到(min)</th><th>早退(min)</th><th>加班(h)</th><th>备注</th><th>状态</th><th>审核</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.date" style="cursor:pointer" @click="showDetail(r)">
              <td>{{ r.date }}</td>
              <td>{{ r.isRestDay ? '休息' : '上班' }}</td>
              <td>{{ r.signIn || '--' }}</td>
              <td>{{ r.signOut || '--' }}</td>
              <td>{{ r.lateMinutes || 0 }}</td>
              <td>{{ r.earlyMinutes || 0 }}</td>
              <td>{{ r.overtimeHours || 0 }}</td>
              <td style="font-size:12px">{{ remarkText(r) }}</td>
              <td><span class="badge" :class="statusBadgeClass(r.status)">{{ statusLabel(r.status) }}</span></td>
              <td><span class="badge" :class="reviewBadgeClass(r.review_status)">{{ reviewStatusLabel(r.review_status) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="rows.length === 0" class="text-center" style="padding:40px;color:var(--text-secondary);font-size:14px">
        {{ currentMonth }} 暂无考勤数据，请联系管理员处理。
      </div>
    </div>

    <div v-if="detail" class="detail-overlay" @click.self="detail = null">
      <div class="detail-modal">
        <div class="flex-between" style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
          <h3 style="font-size:16px;font-weight:600">{{ detail.date }} 详情</h3>
          <button class="btn btn-ghost btn-sm" @click="detail = null">关闭</button>
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
import { ref, computed, onMounted, watch } from 'vue';
import { apiRequest } from '../shared/api';
import { statusLabel, statusBadgeClass, remarkText, reviewStatusLabel } from '../shared/constants';

const currentMonth = ref('');
const rows = ref([]);
const detail = ref(null);

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

onMounted(() => {
  const now = new Date();
  currentMonth.value = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
  load();
});

watch(currentMonth, load);

async function load() {
  try {
    rows.value = await apiRequest('/attendance/my?month=' + encodeURIComponent(currentMonth.value));
  } catch (err) {
    rows.value = [];
  }
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
.stat-chip { display: flex; flex-direction: column; align-items: center; padding: 10px 18px; background: var(--paper); border-radius: var(--radius-md); border: 1px solid var(--border); }
.stat-chip .sc-label { font-size: 11px; color: var(--text-secondary); }
.stat-chip .sc-value { font-size: 18px; font-weight: 600; margin-top: 2px; }
.detail-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 200; }
.detail-modal { background: var(--card-bg); border-radius: var(--radius-xl); box-shadow: 0 16px 48px rgba(44,36,22,0.15); width: 90vw; max-width: 520px; max-height: 85vh; overflow-y: auto; padding: 24px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-grid .dg-label { font-size: 12px; color: var(--text-secondary); }
.detail-grid .dg-value { font-size: 14px; font-weight: 500; }
</style>
