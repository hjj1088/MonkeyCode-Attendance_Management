// shared/constants.js
// 考勤状态 9 态映射（复刻 V3.1 attendance.html）

const STATUS_LABELS = {
  normal: '正常',
  rest: '休息',
  abnormal: '迟到',
  leave: '请假',
  travel: '出差',
  absent: '缺勤',
  overtime: '疑似加班',
  suspect_ot: '疑似加班',
  no_sign_in: '上班未打卡',
  no_sign_out: '下班未打卡',
};

const STATUS_BADGE = {
  normal: 'badge-normal',
  rest: '',
  abnormal: 'badge-late',
  leave: 'badge-leave',
  travel: 'badge-travel',
  absent: 'badge-miss',
  overtime: 'badge-early',
  suspect_ot: 'badge-nosign',
  no_sign_in: 'badge-nosign',
  no_sign_out: 'badge-nosign',
};

const STATUS_COLORS = {
  normal: 'var(--jade)',
  abnormal: 'var(--vermillion)',
  leave: 'var(--indigo)',
  travel: 'var(--sandal)',
  absent: 'var(--vermillion)',
  overtime: 'var(--gold)',
  suspect_ot: 'var(--sandal)',
};

const CAL_CELL_CLASS = {
  normal: 'cal-normal',
  abnormal: 'cal-abnormal',
  absent: 'cal-absent',
  rest: 'cal-rest',
  leave: 'cal-leave',
  travel: 'cal-travel',
  overtime: 'cal-overtime',
  holiday: 'cal-holiday',
  unknown: 'cal-unknown',
};

export function statusLabel(s) {
  return STATUS_LABELS[s] || s || '';
}

export function statusBadgeClass(s) {
  return STATUS_BADGE[s] || 'badge-miss';
}

export function statusColor(s) {
  return STATUS_COLORS[s] || 'var(--text-secondary)';
}

export function remarkText(r) {
  const p = [];
  if (r.leaveType) p.push(r.leaveType + (r.leaveHours ? r.leaveHours + 'h' : ''));
  else if (r.sourceLeaveIds && r.sourceLeaveIds.length) p.push('请假');
  if (r.travelHours > 0 || (r.sourceTravelIds && r.sourceTravelIds.length)) p.push('出差');
  if (r.overtimeHours > 0 && r.status !== 'leave' && r.status !== 'travel') p.push('加班' + r.overtimeHours + 'h');
  else if (r.status === 'overtime') p.push('疑似加班' + (r.overtimeHours ? r.overtimeHours + 'h' : ''));
  else if (r.sourceOvertimeIds && r.sourceOvertimeIds.length) p.push('有加班');
  if (r.status === 'suspect_ot') p.push('疑似加班');
  if (r.sourceMissIds && r.sourceMissIds.length) p.push('补卡');
  if (r.absent) p.push('缺勤');
  return p.join('/');
}

export function reviewStatusLabel(s) {
  const m = {
    pending_review: '待确认',
    confirmed: '已确认',
    submitted: '已提交',
    locked: '已锁定',
    disputed: '申诉中',
  };
  return m[s] || s || '待确认';
}

export { STATUS_LABELS, STATUS_BADGE, STATUS_COLORS, CAL_CELL_CLASS };
