// D3 考勤计算测试：驱动前端 rules.js（esbuild bundle + mock store fetch）
// 覆盖：排班+请假→leave、容错豁免（月2次≤30min）、加班调休结余
import assert from 'node:assert';

const BUNDLE = process.argv[2] || '/tmp/opencode/rules.bundle.mjs';

const CONFIG = JSON.stringify({
  workStartTime: '08:30',
  workEndTime: '17:30',
  lateThreshold: 0,
  earlyThreshold: 0,
  graceTimes: 2,
  graceMinutes: 30,
});

const ALL_WORKDAYS = {};
for (let d = 1; d <= 31; d++) ALL_WORKDAYS[String(d).padStart(2, '0')] = true;

const PUNCH = [
  { employeeNo: 'E001', name: '张三', department: '技术部', date: '2026-08-10',
    period: '正常班', signIn: '08:50', signOut: '17:30', overtimeHours: 0 },
  { employeeNo: 'E001', name: '张三', department: '技术部', date: '2026-08-11',
    period: '正常班', signIn: '08:35', signOut: '17:30', overtimeHours: 0 },
  { employeeNo: 'E001', name: '张三', department: '技术部', date: '2026-08-12',
    period: '正常班', signIn: '08:30', signOut: '19:30', overtimeHours: 3 },
];

const LEAVES = [
  { applicant: '张三', department: '技术部', leaveType: '年假',
    startDate: '2026-08-15', endDate: '2026-08-15', leaveDays: 1, leaveHours: 0, reason: '' },
  { applicant: '张三', department: '技术部', leaveType: '调休',
    startDate: '2026-08-16', endDate: '2026-08-16', leaveDays: 0, leaveHours: 1, reason: '' },
];

const SCHEDULES = [
  { employeeNo: 'E001', name: '张三', department: '技术部', year: 2026, month: 8, workDays: ALL_WORKDAYS },
];

const captured = { calc: null };

const sessionStorage = {
  _d: {},
  getItem(k) { return k in this._d ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};
globalThis.sessionStorage = sessionStorage;
globalThis.window = { location: { pathname: '/attendance' } };

function jsonRes(data) {
  return new Response(JSON.stringify({ code: 0, data }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

globalThis.fetch = (input, init) => {
  const url = String(input);
  const method = (init && init.method) || 'GET';

  if (method === 'POST' && url === '/api/attendance/calculate') {
    captured.calc = JSON.parse(init.body);
    return Promise.resolve(jsonRes({ message: 'ok', saved: 0 }));
  }

  if (url.startsWith('/api/store/')) {
    const rest = url.slice('/api/store/'.length);
    const [path, qs] = rest.split('?');
    const parts = path.split('/').filter(Boolean);
    const table = parts[0];

    if (table === 'settings' && parts[1] === 'attendance_config') {
      // 后端 json_serialize 会将 value 反序列化为对象
      return Promise.resolve(jsonRes({ key: 'attendance_config', value: JSON.parse(CONFIG) }));
    }
    const tableData = {
      holidays: [],
      punch_records: PUNCH,
      leave_records: LEAVES,
      travel_records: [],
      miss_punch_records: [],
      overtime_records: [],
      schedules: SCHEDULES,
      carry_over: [],
    }[table] || [];
    return Promise.resolve(jsonRes(tableData));
  }

  return Promise.reject(new Error('unexpected fetch: ' + method + ' ' + url));
};

const { RulesEngine } = await import(BUNDLE);

const results = await RulesEngine.calculateMonth('2026-08');
assert.strictEqual(results.length, 31, 'should generate 31 day rows');

function rowFor(date) {
  const r = results.find(x => x.date === date);
  assert.ok(r, 'no result for ' + date);
  return r;
}

// 1. 排班工作日 + 请假 → leave（年假/调休）
const leaveDay = rowFor('2026-08-15');
assert.strictEqual(leaveDay.status, 'leave', 'leave day should be leave');
assert.strictEqual(leaveDay.leaveType, '年假');
const tiaoDay = rowFor('2026-08-16');
assert.strictEqual(tiaoDay.status, 'leave', 'comp-off day should be leave');
assert.strictEqual(tiaoDay.leaveType, '调休');

// 2. 容错豁免：月内 2 次迟到共 25min ≤ 30min → 恢复 normal 且 lateMinutes 归零
const late1 = rowFor('2026-08-10');
assert.strictEqual(late1.status, 'normal', 'grace waiver should clear first late');
assert.strictEqual(late1.lateMinutes, 0);
const late2 = rowFor('2026-08-11');
assert.strictEqual(late2.status, 'normal', 'grace waiver should clear second late');
assert.strictEqual(late2.lateMinutes, 0);

// 3. 加班记录保留 overtimeHours
const otDay = rowFor('2026-08-12');
assert.strictEqual(otDay.status, 'normal');
assert.strictEqual(otDay.overtimeHours, 3);

// 4. 结余：加班 3h - 调休 1h = 2h
assert.ok(captured.calc, 'should POST /attendance/calculate');
const e001Carry = captured.calc.carry_over.find(c => c.employeeNo === 'E001');
assert.ok(e001Carry, 'carry_over should include E001');
assert.strictEqual(e001Carry.overtimeBalance, 2, 'balance = 3 - 1');

console.log('PASS calc_flow: leave/travel, grace waiver, overtime, carry-over balance');
