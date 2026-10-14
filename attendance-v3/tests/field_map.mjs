import assert from 'node:assert';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const BUNDLE = process.argv[2];
const MATCHER = process.argv[3] || join(dirname(fileURLToPath(import.meta.url)), '..', 'client', 'src', 'shared', 'matcher.js');

const {
  pickField, headerExists, isSelfValue, resolveSubject, mergeFieldMap, DEFAULT_OA_FIELD_MAP,
  uniquifyHeaders, headerBase, pickApplicantAndOther, labelForField,
  TYPE_IDENTIFY, RECORD_SCHEMA, OA_SELF_ALIASES,
} = await import(BUNDLE);
const { Matcher } = await import(MATCHER);

const leave = DEFAULT_OA_FIELD_MAP.types.leave;
const overtime = DEFAULT_OA_FIELD_MAP.types.overtime;
const miss = DEFAULT_OA_FIELD_MAP.types.miss_punch;

const exact = pickField({ 是否本人: '非本人', 申请人: '李四' }, leave.isSelf);
assert.strictEqual(exact.value, '非本人');
assert.strictEqual(exact.fuzzy, false);

const fuzzySelf = pickField({ 是否为本人: '帮他人' }, leave.isSelf);
assert.strictEqual(fuzzySelf.value, '帮他人');
assert.ok(fuzzySelf.score >= 60);

const optionCol = pickField({ 选项: '其它', 申请人: '李四' }, leave.isSelf);
assert.strictEqual(optionCol.value, '其它');
assert.strictEqual(optionCol.header, '选项');

const person = pickField({ 申请人: '李四', 申请部门: '生产部', 请假人员: '张三' }, leave.subjectPerson);
assert.strictEqual(person.value, '张三');

const applicant = pickField({ 申请人: '李四', 申请部门: '生产部' }, leave.applicant);
assert.strictEqual(applicant.value, '李四');

const dept = pickField({ 申请人: '李四', 申请部门: '生产部' }, leave.department);
assert.strictEqual(dept.value, '生产部');

assert.ok(headerExists(['请假类型', '开始日期', '是否为本人'], leave.isSelf));
assert.deepStrictEqual(leave.isSelf, overtime.isSelf);
assert.deepStrictEqual(leave.isSelf, OA_SELF_ALIASES);
assert.ok(TYPE_IDENTIFY.leave.required.includes('leaveType'));
assert.ok(RECORD_SCHEMA.leave.oa);
assert.ok(!RECORD_SCHEMA.punch.oa);
assert.ok(headerExists(['漏打卡日期', '申请人'], miss.missDate));
assert.ok(!headerExists(['姓名', '日期'], leave.leaveType));
assert.ok(!headerExists(['是否为本人'], leave.subjectPerson));

assert.strictEqual(isSelfValue('本人'), true);
assert.strictEqual(isSelfValue('是'), true);
assert.strictEqual(isSelfValue('非本人'), false);
assert.strictEqual(isSelfValue('帮他人'), false);
assert.strictEqual(isSelfValue('其它'), false);
assert.strictEqual(isSelfValue('其他'), false);
assert.strictEqual(isSelfValue('否'), false);
assert.strictEqual(isSelfValue(''), null);

const dupHeaders = uniquifyHeaders(['申请人', '是否本人', '申请人']);
assert.deepStrictEqual(dupHeaders, ['申请人', '是否本人', '申请人#2']);
assert.strictEqual(headerBase('申请人#2'), '申请人');

const dupRow = { 申请人: '李四', 是否本人: '其它', '申请人#2': '张三' };
const people = pickApplicantAndOther(dupRow, leave.applicant, leave.subjectPerson);
assert.strictEqual(people.applicant.value, '李四');
assert.strictEqual(people.other.value, '张三');
assert.strictEqual(resolveSubject('本人', people.applicant.value, people.other.value), '李四');
assert.strictEqual(resolveSubject('其它', people.applicant.value, people.other.value), '张三');

const namedOther = pickApplicantAndOther(
  { 申请人: '李四', 请假人员: '张三' },
  leave.applicant,
  leave.subjectPerson,
);
assert.strictEqual(namedOther.applicant.value, '李四');
assert.strictEqual(namedOther.other.value, '张三');

assert.strictEqual(labelForField('leave', 'applicant'), '申请人');
assert.strictEqual(labelForField('leave', 'subject'), '实际人员');
assert.strictEqual(labelForField('schedule', 'date'), '日期');
assert.strictEqual(labelForField('punch', 'employeeNo'), '考勤号码');

assert.strictEqual(resolveSubject('本人', '李四', '张三'), '李四');
assert.strictEqual(resolveSubject('非本人', '李四', '张三'), '张三');
assert.strictEqual(resolveSubject('帮他人', '李四', '张三'), '张三');
assert.strictEqual(resolveSubject('', '李四', '张三'), '张三');

const merged = mergeFieldMap({
  types: { leave: { isSelf: ['是否代填'] } },
});
assert.ok(merged.types.leave.isSelf.includes('是否代填'));
assert.ok(merged.types.leave.leaveType.includes('请假类型'));

const employeeMap = {
  E001: { name: '张三', department: '本部' },
  E002: { name: '李四', department: '生产部' },
};
const matches = Matcher.matchOAToPunch([
  { applicant: '李四', department: '生产部', subject: '张三' },
], employeeMap);
assert.strictEqual(matches[0].employeeNo, 'E001');
assert.strictEqual(matches[0].subject, '张三');

const sameNameOnly = Matcher.matchOAToPunch([
  { applicant: '王五', department: '生产部', subject: '李四' },
], employeeMap);
assert.strictEqual(sameNameOnly[0].employeeNo, 'E002');

const ambiguous = Matcher.matchOAToPunch([
  { applicant: '李四', department: '市场部', subject: '同名' },
], {
  E003: { name: '同名', department: '本部' },
  E004: { name: '同名', department: '生产部' },
});
assert.strictEqual(ambiguous[0].employeeNo, null);

const emptyPick = pickField({}, leave.leaveType);
assert.strictEqual(emptyPick.value, '');
assert.strictEqual(emptyPick.score, 0);

assert.ok(headerExists(['考勤号码', '签到时间'], DEFAULT_OA_FIELD_MAP.types.punch.employeeNo));
assert.ok(headerExists(['考勤号', '签到时间'], DEFAULT_OA_FIELD_MAP.types.punch.employeeNo));

function requiredHit(headers, aliasesList) {
  return aliasesList.every((aliases) => headerExists(headers, aliases));
}
const types = DEFAULT_OA_FIELD_MAP.types;
assert.ok(requiredHit(['考勤号', '签到时间'], [types.punch.employeeNo, types.punch.signIn]));
assert.ok(requiredHit(['假别', '请假开始日期'], [types.leave.leaveType, types.leave.startDate]));
assert.ok(requiredHit(['加班起止时间'], [types.overtime.overtimeRange]));
assert.ok(requiredHit(['开始时间', '结束时间'], [types.overtime.startTime, types.overtime.endTime]));
assert.ok(requiredHit(['出差起止日期'], [types.travel.travelRange]));
assert.ok(requiredHit(['补卡日期'], [types.miss_punch.missDate]));
assert.ok(!requiredHit(['姓名', '部门'], [types.leave.leaveType, types.leave.startDate]));

const { FieldMap } = await import(BUNDLE);
assert.strictEqual(await FieldMap.learnMany([]), null);
const learned = await FieldMap.learnMany([{ type: 'leave', field: 'isSelf', header: '是否代填' }]);
assert.ok(learned);
assert.strictEqual(learned.types.leave.isSelf[0], '是否代填');
assert.ok(learned.types.leave.isSelf.includes('是否本人'));

console.log('ok');
