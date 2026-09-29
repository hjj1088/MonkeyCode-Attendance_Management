<template>
  <div class="table-root">
    <StickyTable :cols="colWidths" min-width="1100px">
      <template #head>
        <tr>
          <th>考勤号</th>
          <th>姓名</th>
          <th>部门</th>
          <th>日期</th>
          <th>排班</th>
          <th>签到</th>
          <th>签退</th>
          <th class="c-num">迟到(min)</th>
          <th class="c-num">早退(min)</th>
          <th class="c-num">加班(h)</th>
          <th>备注</th>
          <th>状态</th>
          <th>审核</th>
          <th v-if="canReview" class="c-right">操作</th>
        </tr>
      </template>
      <tr v-for="r in rows" :key="r.employeeNo + r.date" @click="showDetail(r)">
        <td>{{ r.employeeNo }}</td>
        <td>{{ r.name }}</td>
        <td>{{ r.department }}</td>
        <td>{{ r.date }}</td>
        <td>{{ holidayMap[r.date] ? holidayMap[r.date].name : (r.isRestDay ? '休息' : '上班') }}</td>
        <td>{{ r.signIn || '--' }}</td>
        <td>{{ r.signOut || '--' }}</td>
        <td class="c-num">{{ r.lateMinutes || 0 }}</td>
        <td class="c-num">{{ r.earlyMinutes || 0 }}</td>
        <td class="c-num">{{ r.overtimeHours || 0 }}</td>
        <td class="c-note-cell">{{ remarkText(r) }}</td>
        <td><span class="badge" :class="statusBadgeClass(r.status)">{{ statusLabel(r.status) }}</span></td>
        <td><span class="badge" :class="reviewBadgeClass(r.review_status)">{{ reviewStatusLabel(r.review_status) }}</span></td>
        <td v-if="canReview" class="c-right" @click.stop>
          <button v-if="r.review_status === 'pending_review'" class="btn btn-secondary btn-sm" @click="review(r, 'confirmed')"><AppIcon name="check" :size="13" /><span>确认</span></button>
          <button v-if="r.review_status === 'disputed'" class="btn btn-secondary btn-sm" @click="review(r, 'confirmed')"><AppIcon name="check" :size="13" /><span>确认</span></button>
          <button v-if="r.review_status === 'pending_review'" class="btn btn-danger btn-sm" @click="review(r, 'disputed')"><AppIcon name="alert" :size="13" /><span>申诉</span></button>
        </td>
      </tr>
    </StickyTable>
    <div v-if="rows.length === 0 && emptyHint !== ''" class="text-center empty-hint">
      <template v-if="emptyHint">{{ emptyHint }}</template>
      <template v-else>暂无数据，请先<a @click.prevent="$emit('go-import')" href="#" class="link-accent">导入数据</a>后计算</template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import StickyTable from './StickyTable.vue';
import AppIcon from './AppIcon.vue';
import { statusLabel, statusBadgeClass, remarkText, reviewStatusLabel } from '../shared/constants';

const props = defineProps({
  rows: { type: Array, default: () => [] },
  holidayMap: { type: Object, default: () => ({}) },
  canReview: { type: Boolean, default: false },
  emptyHint: { type: String, default: undefined },
});

const emit = defineEmits(['show-detail', 'review', 'go-import']);

const colWidths = computed(() => {
  const cols = ['72px', '72px', '88px', '100px', '64px', '72px', '72px', '88px', '88px', '72px', '96px', '72px', '80px'];
  if (props.canReview) cols.push('140px');
  return cols;
});

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

<style scoped>
.table-root {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--card-bg);
}
.c-note-cell { font-size: 12px; }
.c-num { text-align: center; font-variant-numeric: tabular-nums; }
.c-right { text-align: right; }
tr { cursor: pointer; }
.empty-hint { padding: 40px; color: var(--ink-secondary); font-size: 14px; flex-shrink: 0; }
.link-accent { color: var(--celadon); font-weight: 500; cursor: pointer; }
</style>
