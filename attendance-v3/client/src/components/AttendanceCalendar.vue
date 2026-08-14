<template>
  <div>
    <div class="filter-bar">
      <span style="font-size:13px;color:var(--text-secondary)">当前员工:</span>
      <select :value="employee" @change="$emit('change-employee', $event.target.value)">
        <option value="">-- 全部 --</option>
        <option v-for="emp in employees" :key="emp.employeeNo" :value="emp.employeeNo">{{ emp.name }} ({{ emp.employeeNo }})</option>
      </select>
      <span v-if="employee && employeeInfo" style="font-size:13px;color:var(--text-secondary)">{{ employeeInfo.department }}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:4px">
      <div v-for="d in ['一', '二', '三', '四', '五', '六', '日']" :key="d" class="text-center" style="font-size:13px;font-weight:600;color:var(--text-secondary);padding:4px 0">{{ d }}</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px">
      <div v-for="cell in cells" :key="cell.key" class="cal-cell" :class="cell.statusClass" @click="cell.record && $emit('show-detail', cell.record)">
        <div class="cal-day">{{ cell.day }}</div>
        <div v-if="cell.record" style="margin-top:2px">
          <div class="cal-time">{{ cell.record.signIn || '--' }} / {{ cell.record.signOut || '--' }}</div>
          <div v-if="cell.record.isRestDay && !cell.holidayName" style="color:var(--text-secondary);font-size:10px">休息日</div>
          <div v-if="cell.holidayName" style="color:var(--vermillion);font-weight:600;font-size:10px">{{ cell.holidayName }}</div>
          <div v-if="cell.record.status !== 'normal' && cell.record.status !== 'rest'" class="cal-status" :style="{ color: statusColor(cell.record.status) }">{{ statusLabel(cell.record.status) }}</div>
        </div>
        <div v-if="!cell.record && cell.holidayName" style="color:var(--vermillion);font-weight:600;font-size:10px;margin-top:2px">{{ cell.holidayName }}</div>
        <div v-else-if="!cell.record && cell.isRest" style="color:var(--text-secondary);font-size:10px;margin-top:2px">休息</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { statusLabel, statusColor } from '../shared/constants';

defineProps({
  cells: { type: Array, default: () => [] },
  employee: { type: String, default: '' },
  employees: { type: Array, default: () => [] },
  employeeInfo: { type: Object, default: null },
});

defineEmits(['change-employee', 'show-detail']);
</script>
