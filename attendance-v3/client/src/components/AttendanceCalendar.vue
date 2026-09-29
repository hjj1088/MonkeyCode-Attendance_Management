<template>
  <div class="calendar-root">
    <div class="cal-weekdays">
      <div v-for="d in ['一', '二', '三', '四', '五', '六', '日']" :key="d" class="cal-weekday">{{ d }}</div>
    </div>
    <div class="cal-grid">
      <div v-for="cell in cells" :key="cell.key" class="cal-cell" :class="[cell.statusClass, { 'is-today': cell.isToday }]" @click="cell.record && $emit('show-detail', cell.record)">
        <span class="cal-day">{{ cell.day }}</span>
        <span v-if="cell.holidayName" class="cal-holiday-name" :title="cell.holidayName">{{ cell.holidayName }}</span>
        <template v-if="cell.record && cell.record.status !== 'rest'">
          <span class="cal-time-line cal-signin"><span class="cal-time-label">上班</span><span class="cal-time">{{ cell.record.signIn || '--' }}</span></span>
          <span class="cal-time-line cal-signout"><span class="cal-time-label">下班</span><span class="cal-time">{{ cell.record.signOut || '--' }}</span></span>
          <span class="cal-badge" :class="statusBadgeClass(cell.record.status) || 'cal-badge-rest'">{{ statusWithTime(cell.record) }}</span>
        </template>
        <template v-else-if="cell.record">
          <span class="cal-badge cal-badge-full" :class="statusBadgeClass(cell.record.status) || 'cal-badge-rest'">{{ statusWithTime(cell.record) }}</span>
        </template>
        <template v-else>
          <span v-if="cell.isRest" class="cal-badge cal-badge-full cal-badge-rest">休息</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { statusLabel, statusBadgeClass } from '../shared/constants';

function formatMinutes(min) {
  if (min < 60) return min + 'm';
  const h = Math.round(min / 60 * 10) / 10;
  return h + 'h';
}

function statusWithTime(r) {
  const label = statusLabel(r.status);
  if (r.status === 'abnormal' && r.lateMinutes) return label + formatMinutes(r.lateMinutes);
  if (r.status === 'leave' && r.leaveHours) return label + (Math.round(r.leaveHours * 10) / 10) + 'h';
  return label;
}

defineProps({
  cells: { type: Array, default: () => [] },
});

defineEmits(['show-detail']);
</script>

<style scoped>
.calendar-root { display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; }
.cal-weekdays { display: grid; grid-template-columns: repeat(7,1fr); gap: 2px; margin-bottom: 2px; flex-shrink: 0; }
.cal-weekday { text-align: center; font-size: 13px; font-weight: 600; color: var(--ink-secondary); padding: 4px 0; }
.cal-grid { display: grid; grid-template-columns: repeat(7,1fr); gap: 2px; flex: 1; min-height: 0; grid-auto-rows: minmax(0, 1fr); }
.cal-cell { position: relative; border-radius: var(--radius-sm); transition: box-shadow 0.15s, background 0.15s; cursor: pointer; padding: 6px 8px; font-size: 12px; line-height: 1.25; overflow: hidden; display: grid; grid-template-columns: 1fr auto; grid-template-rows: auto auto auto; column-gap: 6px; }
.cal-cell:hover { z-index: 10; box-shadow: var(--shadow-md); }
.cal-cell.cal-normal { background: var(--jade-light); border: 1px solid color-mix(in srgb, var(--jade) 25%, transparent); }
.cal-cell.cal-abnormal { background: var(--vermillion-light); border: 1px solid color-mix(in srgb, var(--vermillion) 20%, transparent); }
.cal-cell.cal-absent { background: var(--vermillion-light); border: 1px solid color-mix(in srgb, var(--vermillion) 30%, transparent); }
.cal-cell.cal-rest { background: var(--paper); border: 1px solid var(--border); }
.cal-cell.cal-leave { background: var(--celadon-light); border: 1px solid color-mix(in srgb, var(--celadon) 25%, transparent); }
.cal-cell.cal-travel { background: var(--celadon-light); border: 1px solid color-mix(in srgb, var(--celadon) 25%, transparent); }
.cal-cell.cal-overtime { background: var(--gold-muted-light); border: 1px solid color-mix(in srgb, var(--gold-muted) 30%, transparent); }
.cal-cell.cal-unknown { background: var(--paper); border: 1px solid var(--border); }
.cal-cell.is-today { box-shadow: inset 0 0 0 2px var(--celadon); }
.cal-cell.is-today .cal-day::after {
  content: "";
  display: inline-block;
  width: 6px; height: 6px;
  margin-left: 6px;
  border-radius: 50%;
  background: var(--vermillion);
  vertical-align: middle;
}
.cal-day { grid-column: 1 / -1; justify-self: start; font-size: 18px; font-weight: 700; color: var(--ink); margin-bottom: 2px; padding-right: 52px; }
.cal-holiday-name {
  position: absolute; top: 6px; right: 8px;
  max-width: 48%;
  font-size: 11px; font-weight: 500; line-height: 1.2;
  color: var(--vermillion);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  pointer-events: none;
}
.cal-time-line { display: flex; align-items: baseline; gap: 6px; }
.cal-signin { grid-row: 2; grid-column: 1; }
.cal-signout { grid-row: 3; grid-column: 1; }
.cal-time-label { font-size: 12px; color: var(--ink-secondary); }
.cal-time { font-size: 18px; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.cal-badge { grid-row: 2 / 4; grid-column: 2; align-self: center; justify-self: center; font-size: 14px; font-weight: 600; line-height: 1; padding: 4px 8px; border-radius: var(--radius-sm); white-space: nowrap; }
.cal-badge-full { grid-column: 1 / -1; grid-row: 2 / 4; justify-self: center; }
.cal-badge-rest { background: var(--paper); color: var(--ink-muted); }
.cal-badge-holiday { background: var(--vermillion-light); color: var(--vermillion); }
</style>
