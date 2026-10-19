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
  // 短假豁免：8-13 迟到 56min，代请假 1h（subject 王五）→ 正常
  { employeeNo: 'E002', name: '王五', department: '技术部', date: '2026-08-13',
    period: '正常班', signIn: '09:26', signOut: '17:30', overtimeHours: 0 },
  // 漏打卡时段匹配：8-18 缺上午打卡，漏打卡说明「上午」→ 正常
  { employeeNo: 'E002', name: '王五', department: '技术部', date: '2026-08-18',
    period: '正常班', signIn: '', signOut: '17:30', overtimeHours: 0 },
  // 漏打卡时段不匹配：8-19 缺上午打卡，漏打卡说明「下午」→ 旷工
  { employeeNo: 'E002', name: '王五', department: '技术部', date: '2026-08-19',
    period: '正常班', signIn: '', signOut: '17:30', overtimeHours: 0 },
  // 漏打卡具体时间：8-20 缺上午打卡，漏打卡说明 09:00 → 覆盖上午 → 正常
  { employeeNo: 'E002', name: '王五', department: '技术部', date: '2026-08-20',
    period: '正常班', signIn: '', signOut: '17:30', overtimeHours: 0 },
  // 短假不足抵扣：8-21 迟到 86min，请假 30min → 迟到 56min 异常（超出容错 30min）
  { employeeNo: 'E002', name: '王五', department: '技术部', date: '2026-08-21',
    period: '正常班', signIn: '09:56', signOut: '17:30', overtimeHours: 0 },
];

const LEAVES = [
  { applicant: '张三', department: '技术部', leaveType: '年假',
    startDate: '2026-08-15', endDate: '2026-08-15', leaveDays: 1, leaveHours: 0, reason: '' },
  { applicant: '张三', department: '技术部', leaveType: '调休',
    startDate: '2026-08-16', endDate: '2026-08-16', leaveDays: 0, leaveHours: 1, reason: '' },
  { applicant: '李四', department: '技术部', leaveType: '年假',
    startDate: '2026-08-17', endDate: '2026-08-17', leaveDays: 1, leaveHours: 0, reason: '',
    isSelf: '非本人', subject: '张三' },
  { applicant: '李四', department: '技术部', leaveType: '事假',
    startDate: '2026-08-13', endDate: '2026-08-13', leaveDays: 0, leaveHours: 1, reason: '',
    isSelf: '非本人', subject: '王五' },
  { applicant: '李四', department: '技术部', leaveType: '事假',
    startDate: '2026-08-21', endDate: '2026-08-21', leaveDays: 0, leaveHours: 0.5, reason: '',
    isSelf: '非本人', subject: '王五' },
  // 连续 2 天调休 16h：分摊后每天 8h（修复前每天全量 16h、结余多扣）
  { applicant: '王五', department: '技术部', leaveType: '调休',
    startDate: '2026-08-25', endDate: '2026-08-26', leaveDays: 2, leaveHours: 16, reason: '',
    isSelf: '本人', subject: '王五' },
];

const MISS_PUNCH = [
  { applicant: '王五', department: '技术部', missDate: '2026-08-18', missPerson: '王五',
    missTime: '上午', cardTime: '', reason: '', isSelf: '本人', subject: '王五' },
  { applicant: '王五', department: '技术部', missDate: '2026-08-19', missPerson: '王五',
    missTime: '下午', cardTime: '', reason: '', isSelf: '本人', subject: '王五' },
  { applicant: '王五', department: '技术部', missDate: '2026-08-20', missPerson: '王五',
    missTime: '09:00', cardTime: '', reason: '', isSelf: '本人', subject: '王五' },
];

const SCHEDULES = [
  { employeeNo: 'E001', name: '张三', department: '技术部', year: 2026, month: 8, workDays: ALL_WORKDAYS },
];

const captured = { calc: null, fetches: [] };

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
  captured.fetches.push(method + ' ' + url);

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
      miss_punch_records: MISS_PUNCH,
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
assert.strictEqual(results.length, 62, 'should generate 31 day rows per employee (E001 + E002)');

function rowFor(date, employeeNo = 'E001') {
  const r = results.find(x => x.date === date && x.employeeNo === employeeNo);
  assert.ok(r, 'no result for ' + employeeNo + ' ' + date);
  return r;
}

// 1. 排班工作日 + 请假 → leave（年假/调休）
const leaveDay = rowFor('2026-08-15');
assert.strictEqual(leaveDay.status, 'leave', 'leave day should be leave');
assert.strictEqual(leaveDay.leaveType, '年假');
const tiaoDay = rowFor('2026-08-16');
assert.strictEqual(tiaoDay.status, 'leave', 'comp-off day should be leave');
assert.strictEqual(tiaoDay.leaveType, '调休');
const proxyDay = rowFor('2026-08-17');
assert.strictEqual(proxyDay.status, 'leave', 'proxy leave should match subject');
assert.strictEqual(proxyDay.leaveType, '年假');

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

// 4. 短假豁免：8-13 代请假 1h（subject 王五）覆盖迟到 56min → 正常
const shortLeaveDay = rowFor('2026-08-13', 'E002');
assert.strictEqual(shortLeaveDay.status, 'normal', '1h proxy leave should waive 56min late');
assert.strictEqual(shortLeaveDay.lateMinutes, 0);
assert.strictEqual(shortLeaveDay.leaveType, '事假');
assert.strictEqual(shortLeaveDay.leaveHours, 1);

// 5. 短假不足抵扣：8-21 迟到 86min - 请假 30min = 56min（超出容错，异常保留）
const partialLeaveDay = rowFor('2026-08-21', 'E002');
assert.strictEqual(partialLeaveDay.status, 'abnormal', '30min leave cannot cover 86min late');
assert.strictEqual(partialLeaveDay.lateMinutes, 56);

// 6. 漏打卡时段匹配：缺上午打卡 + 说明「上午」→ 正常
const missAmDay = rowFor('2026-08-18', 'E002');
assert.strictEqual(missAmDay.status, 'normal', 'miss-punch note covers missing AM');
assert.strictEqual(missAmDay.signIn, '');

// 7. 漏打卡时段不匹配：缺上午打卡 + 说明「下午」→ 旷工
const missPmNoteDay = rowFor('2026-08-19', 'E002');
assert.strictEqual(missPmNoteDay.absent, true, 'PM note cannot cover missing AM');

// 8. 漏打卡具体时间 09:00 → 覆盖上午 → 正常
const missTimeDay = rowFor('2026-08-20', 'E002');
assert.strictEqual(missTimeDay.status, 'normal', '09:00 note covers missing AM');

// 9. 连续 2 天调休 16h → 每天分摊 8h（修复前每天全量 16h）
const split1 = rowFor('2026-08-25', 'E002');
const split2 = rowFor('2026-08-26', 'E002');
assert.strictEqual(split1.status, 'leave');
assert.strictEqual(split2.status, 'leave');
assert.strictEqual(split1.leaveHours, 8, 'multi-day leave should split per day');
assert.strictEqual(split2.leaveHours, 8);
assert.strictEqual(split1.leaveHours + split2.leaveHours, 16, 'split total equals record total');

// 10. 结余：E001 加班 3h - 调休 1h = 2h；E002 无加班 - 调休 16h → 0（不为负，且不因多日重复扣减而异常）
const e001Carry = captured.calc.carry_over.find(c => c.employeeNo === 'E001');
assert.ok(e001Carry, 'carry_over should include E001');
assert.strictEqual(e001Carry.overtimeBalance, 2, 'balance = 3 - 1');
const e002Carry = captured.calc.carry_over.find(c => c.employeeNo === 'E002');
assert.ok(e002Carry, 'carry_over should include E002');
assert.strictEqual(e002Carry.overtimeBalance, 0, 'balance floors at 0');

// 5. Store 往返是常数：禁止按人串行 getByIndex
assert.ok(captured.fetches.length <= 12, 'store roundtrips should be O(1), got ' + captured.fetches.length);
assert.ok(!captured.fetches.some(u => u.includes('index=employeeNo') || u.includes('index=year')), 'must not query store by per-employee index');

console.log('PASS calc_flow: leave/travel, grace waiver, overtime, carry-over balance');
