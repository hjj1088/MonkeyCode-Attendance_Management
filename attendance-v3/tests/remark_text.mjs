// 备注文案测试：状态列已展示「疑似加班」，备注不再重复该文案
import assert from 'node:assert';
import { remarkText } from '../client/src/shared/constants.js';

function r(kw) {
  return Object.assign({
    status: 'normal', leaveType: '', leaveHours: 0, travelHours: 0,
    overtimeHours: 0, absent: false,
    sourceLeaveIds: [], sourceTravelIds: [], sourceOvertimeIds: [], sourceMissIds: [],
  }, kw);
}

// 状态列已含「疑似加班」，备注不得重复出现该文案；疑似态的小时数也不在备注重复
assert.strictEqual(remarkText(r({ status: 'overtime' })), '');
assert.strictEqual(remarkText(r({ status: 'suspect_ot' })), '');
assert.ok(!remarkText(r({ status: 'suspect_ot', overtimeHours: 2 })).includes('疑似加班'));
assert.ok(!remarkText(r({ status: 'overtime', sourceOvertimeIds: [1] })).includes('疑似加班'));
assert.strictEqual(remarkText(r({ status: 'overtime', overtimeHours: 2 })), '');
assert.strictEqual(remarkText(r({ status: 'suspect_ot', sourceOvertimeIds: [1] })), '');

// 真实加班（非疑似态）仍保留在备注
assert.strictEqual(remarkText(r({ status: 'normal', overtimeHours: 3 })), '加班3h');
assert.strictEqual(remarkText(r({ status: 'normal', sourceOvertimeIds: [1] })), '有加班');
assert.strictEqual(remarkText(r({ status: 'absent', overtimeHours: 2, absent: true })), '加班2h/缺勤');

// 请假/出差/补卡/缺勤组合不受影响
assert.strictEqual(remarkText(r({ status: 'leave', leaveType: '年假', leaveHours: 8 })), '年假8h');
assert.strictEqual(remarkText(r({ status: 'travel', travelHours: 4 })), '出差');
assert.strictEqual(remarkText(r({ status: 'normal', sourceMissIds: [1] })), '补卡');
assert.strictEqual(remarkText(r({ status: 'normal', absent: true })), '缺勤');
assert.strictEqual(
  remarkText(r({ status: 'leave', leaveType: '年假', leaveHours: 2, overtimeHours: 1 })),
  '年假2h'
);

console.log('remarkText: 全部断言通过');
