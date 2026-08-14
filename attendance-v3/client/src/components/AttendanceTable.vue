<template>
  <div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>考勤号</th>
            <th>姓名</th>
            <th>部门</th>
            <th>日期</th>
            <th>排班</th>
            <th>签到</th>
            <th>签退</th>
            <th>迟到(min)</th>
            <th>早退(min)</th>
            <th>加班(h)</th>
            <th>备注</th>
            <th>状态</th>
            <th>审核</th>
            <th v-if="canReview" style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.employeeNo + r.date" style="cursor:pointer" @click="showDetail(r)">
            <td>{{ r.employeeNo }}</td>
            <td>{{ r.name }}</td>
            <td>{{ r.department }}</td>
            <td>{{ r.date }}</td>
            <td>{{ holidayMap[r.date] ? holidayMap[r.date].name : (r.isRestDay ? '休息' : '上班') }}</td>
            <td>{{ r.signIn || '--' }}</td>
            <td>{{ r.signOut || '--' }}</td>
            <td>{{ r.lateMinutes || 0 }}</td>
            <td>{{ r.earlyMinutes || 0 }}</td>
            <td>{{ r.overtimeHours || 0 }}</td>
            <td style="font-size:12px">{{ remarkText(r) }}</td>
            <td><span class="badge" :class="statusBadgeClass(r.status)">{{ statusLabel(r.status) }}</span></td>
            <td><span class="badge" :class="reviewBadgeClass(r.review_status)">{{ reviewStatusLabel(r.review_status) }}</span></td>
            <td v-if="canReview" style="text-align:right" @click.stop>
              <button v-if="r.review_status === 'pending_review'" class="btn btn-secondary btn-sm" @click="review(r, 'confirmed')">确认</button>
              <button v-if="r.review_status === 'disputed'" class="btn btn-secondary btn-sm" @click="review(r, 'confirmed')">确认</button>
              <button v-if="r.review_status === 'pending_review'" class="btn btn-ghost btn-sm" style="color:var(--vermillion)" @click="review(r, 'disputed')">申诉</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="rows.length === 0" class="text-center" style="padding:40px;color:var(--text-secondary);font-size:14px">
      暂无数据，请先<a @click.prevent="$emit('go-import')" href="#" style="color:var(--vermillion);font-weight:500">导入数据</a>后计算
    </div>
  </div>
</template>

<script setup>
import { statusLabel, statusBadgeClass, remarkText, reviewStatusLabel } from '../shared/constants';

const props = defineProps({
  rows: { type: Array, default: () => [] },
  holidayMap: { type: Object, default: () => ({}) },
  canReview: { type: Boolean, default: false },
});

const emit = defineEmits(['show-detail', 'review', 'go-import']);

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

function showDetail(r) {
  emit('show-detail', r);
}

function review(r, status) {
  emit('review', r, status);
}
</script>
