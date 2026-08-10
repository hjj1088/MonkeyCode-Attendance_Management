// V3.1 api-store integration test (Node 18+)
// Loads client/shared/api-store.js with mocked browser globals and drives the
// real backend (isolated DB + port 8002) through Store CRUD + auth flow.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const PORT = process.env.TEST_PORT || '8002';
const BASE = `http://127.0.0.1:${PORT}/api`;

// ---- browser-global mocks ----
const sessionStorage = {
  _d: {},
  getItem(k) { return this._d[k] ?? null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
  clear() { this._d = {}; },
};
let redirectTarget = null;
const location = {
  _href: 'http://127.0.0.1:8002/attendance.html',
  get href() { return this._href; },
  set href(v) { this._href = v; redirectTarget = v; },
};

// translate relative /api/* to absolute against test server
const realFetch = global.fetch;
global.fetch = (input, init) => {
  let url = input;
  if (typeof input === 'string' && input.startsWith('/api')) {
    url = BASE + input.slice('/api'.length);
  }
  return realFetch(url, init);
};
global.window = { location };
global.location = location;
global.sessionStorage = sessionStorage;

const src = fs.readFileSync(path.join(__dirname, '..', 'client', 'shared', 'api-store.js'), 'utf8');

let passed = 0;
let failed = 0;
function assert(cond, msg) {
  if (cond) { passed++; console.log(`PASS ${msg}`); }
  else { failed++; console.log(`FAIL ${msg}`); }
}
async function section(name) {
  console.log(`\n== ${name} ==`);
}

async function main() {
// ---- auth flow (before loading Store so its auto-init has a token) ----
console.log('== 认证链路 ==');
const loginRes = await realFetch(`${BASE}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'admin123' }),
});
const loginBody = await loginRes.json();
assert(loginBody.code === 0 && loginBody.data && loginBody.data.token, 'admin 登录成功返回 token');
sessionStorage.setItem('token', loginBody.data.token);

// ---- load api-store.js after token is set ----
const ctx = vm.createContext({
  fetch: global.fetch,
  sessionStorage,
  window: global.window,
  location,
  console,
  JSON,
  URLSearchParams,
  encodeURIComponent,
});
vm.runInContext(src, ctx);
const Store = vm.runInContext('Store', ctx);

const rulesSrc = fs.readFileSync(path.join(__dirname, '../client/shared/rules.js'), 'utf8');
vm.runInContext(rulesSrc, ctx);
const RulesEngine = vm.runInContext('RulesEngine', ctx);

  // ---- auth flow ----
  await section('认证链路');
  redirectTarget = null;
  const badLogin = await realFetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'wrong' }),
  });
  const badBody = await badLogin.json();
  assert(badBody.code === 1 && badLogin.status === 400, '错误密码登录被拒绝');

  // ---- CRUD ----
  await section('Store CRUD');

  const emps = [];
  for (let i = 1; i <= 3; i++) {
    emps.push({ employeeNo: `IT${String(i).padStart(3, '0')}`, name: `员工${i}`, department: '技术部' });
  }
  const count = await Store.bulkPut('employees', emps);
  assert(count === 3, `bulkPut 写入 3 条 (got ${count})`);

  const all = await Store.getAll('employees');
  assert(Array.isArray(all) && all.length === 3, `getAll 返回 3 条 (got ${all.length})`);

  const byIdx = await Store.getByIndex('employees', 'name', '员工2');
  assert(byIdx.length === 1 && byIdx[0].employeeNo === 'IT002', `getByIndex 按 name 命中员工2`);

  const byKey = await Store.getByKey('employees', 'IT001');
  assert(byKey && byKey.employeeNo === 'IT001', `getByKey 命中 IT001`);

  const byRange = await Store.getByRange('employees', 'employeeNo', 'IT001', 'IT002');
  assert(byRange.length === 2, `getByRange [IT001,IT002] 返回 2 条 (got ${byRange.length})`);

  await Store.put('employees', { employeeNo: 'IT999', name: '新增', department: '销售部' });
  const afterPut = await Store.getAll('employees');
  assert(afterPut.length === 4, `put 新增后共 4 条 (got ${afterPut.length})`);

  await Store.deleteByKey('employees', 'IT999');
  const afterDel = await Store.getAll('employees');
  assert(afterDel.length === 3, `deleteByKey 删除后共 3 条 (got ${afterDel.length})`);

  // ---- TEXT primary key support ----
  await section('TEXT 主键');
  const emp = await Store.getByKey('employees', 'IT001');
  assert(emp && emp.employeeNo === 'IT001', `getByKey 支持 employees 文本主键`);
  await Store.deleteByKey('employees', 'IT001');
  const afterEmpDel = await Store.getAll('employees');
  assert(afterEmpDel.length === 2, `deleteByKey 支持 employees 文本主键 (got ${afterEmpDel.length})`);

  await Store.clearTable('employees');
  const afterClear = await Store.getAll('employees');
  assert(afterClear.length === 0, `clearTable 清空后 0 条 (got ${afterClear.length})`);

  // ---- JSON field serialization ----
  await section('JSON 字段序列化');
  await Store.put('schedules', {
    employeeNo: 'IT001', year: 2026, month: 2, workDays: ['1', '3', '5'],
  });
  const schedList = await Store.getByIndex('schedules', 'employeeNo', 'IT001');
  assert(schedList.length === 1 && Array.isArray(schedList[0].workDays), `schedule.workDays 序列化为数组`);

  // ---- settings page verification (tasklist 3.4) ----
  await section('设置页：考勤规则保存');
  await Store.put('settings', { key: 'attendance_config', value: { workStartTime: '09:00', workEndTime: '18:00', lateThreshold: 5, earlyThreshold: 5, graceTimes: 3, graceMinutes: 45 } });
  await Store.put('settings', { key: 'config_updated_at', value: 1710000000000 });
  const savedConfig = await Store.getByKey('settings', 'attendance_config');
  assert(savedConfig && savedConfig.value && savedConfig.value.workStartTime === '09:00', `attendance_config 保存后可读回`);
  const savedStamp = await Store.getByKey('settings', 'config_updated_at');
  assert(savedStamp && savedStamp.value === 1710000000000, `config_updated_at 保存后可读回`);

  await section('设置页：假期识别');
  await Store.bulkPut('holidays', [
    { date: '2026-02-02', name: '春节假期', isHoliday: 1, isWorkday: 0 },
    { date: '2026-02-07', name: '调休上班', isHoliday: 0, isWorkday: 1 },
  ]);
  await Store.bulkPut('punch_records', [
    { employeeNo: 'IT001', name: '员工1', department: 'IT', date: '2026-02-07', signIn: '08:50', signOut: '17:40', period: 'day' },
  ]);
  const monthResults = await RulesEngine.calculateMonth('2026-02');
  const day07 = monthResults.find(r => r.date === '2026-02-07');
  const day02 = monthResults.find(r => r.date === '2026-02-02');
  assert(day07 && day07.isRestDay === false && day07.status === 'normal', `调休上班日 02-07 正常计算 (status=${day07 && day07.status})`);
  assert(day02 && day02.isRestDay === true && day02.status === 'rest', `春节假期 02-02 识别为休息 (status=${day02 && day02.status})`);

  // ---- 401 handling ----
  await section('401 未授权跳转');
  sessionStorage.clear();
  redirectTarget = null;
  try {
    await Store.getAll('employees');
  } catch (e) {
    /* expected */
  }
  assert(redirectTarget && redirectTarget.endsWith('index.html'), `401 时跳转登录页 (target=${redirectTarget})`);
  assert(sessionStorage.getItem('token') === null, '401 后清除 token');

  console.log(`\n==== ${passed} passed, ${failed} failed ====`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error('ERROR', e);
  process.exit(1);
});
