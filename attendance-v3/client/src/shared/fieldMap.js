import Store from './store';

export const OA_FIELD_MAP_KEY = 'oa_field_map';

export const DEFAULT_TRUE_VALUES = ['本人', '是', 'Y', 'YES', 'TRUE', '是本人'];
export const DEFAULT_FALSE_VALUES = ['非本人', '否', 'N', 'NO', 'FALSE', '帮他人', '代申请', '其它', '其他', '其它人', '其他人', '帮其它人'];

export const OA_SELF_ALIASES = ['是否本人', '本人申请', '选项', '是否为本人', '申请类型'];
export const OA_APPLICANT_ALIASES = ['申请人'];
export const OA_DEPT_ALIASES = ['申请部门', '部门'];

export const DEFAULT_OA_FIELD_MAP = {
  selfTrueValues: DEFAULT_TRUE_VALUES.slice(),
  selfFalseValues: DEFAULT_FALSE_VALUES.slice(),
  types: {
    punch: {
      employeeNo: ['考勤号码', '考勤号'],
      customNo: ['自定义编号'],
      name: ['姓名'],
      date: ['日期'],
      period: ['对应时段'],
      scheduleStart: ['上班时间'],
      scheduleEnd: ['下班时间'],
      signIn: ['签到时间'],
      signOut: ['签退时间'],
      lateMinutes: ['迟到时间'],
      earlyMinutes: ['早退时间'],
      absent: ['是否旷工'],
      overtimeHours: ['加班时间'],
      workHours: ['工作时间'],
      department: ['部门'],
      isWeekday: ['平日'],
      isWeekend: ['周末'],
      isHoliday: ['节假日'],
      weekdayOT: ['平日加班'],
      weekendOT: ['周末加班'],
      holidayOT: ['节假日加班'],
    },
    leave: {
      leaveType: ['请假类型', '假别', '假期类型'],
      startDate: ['开始日期', '请假开始日期', '开始时间'],
      endDate: ['结束日期', '请假结束日期', '结束时间'],
      leaveDays: ['请假天数', '天数'],
      leaveHours: ['小时', '请假小时', '请假时长'],
      applicant: OA_APPLICANT_ALIASES.slice(),
      department: OA_DEPT_ALIASES.slice(),
      reason: ['请假事由', '事由', '原因'],
      isSelf: OA_SELF_ALIASES.slice(),
      subjectPerson: ['请假人员', '被请假人', '请假人', '实际请假人', '受益人'],
    },
    overtime: {
      overtimeRange: ['加班起止时间'],
      startTime: ['开始时间'],
      endTime: ['结束时间'],
      overtimeHours: ['小时', '加班小时', '加班时长'],
      applicant: OA_APPLICANT_ALIASES.slice(),
      department: OA_DEPT_ALIASES.slice(),
      content: ['加班内容', '内容'],
      isSelf: OA_SELF_ALIASES.slice(),
      subjectPerson: ['加班人员', '被加班人', '实际加班人', '受益人'],
    },
    travel: {
      travelRange: ['出差起止日期'],
      applicant: OA_APPLICANT_ALIASES.slice(),
      department: OA_DEPT_ALIASES.slice(),
      destination: ['目的地'],
      travelers: ['出差人员'],
      travelType: ['出差类型'],
      reason: ['出差事由', '事由'],
      isSelf: OA_SELF_ALIASES.slice(),
      subjectPerson: ['出差人员', '被出差人', '实际出差人', '受益人'],
    },
    miss_punch: {
      missDate: ['忘打卡日期', '漏打卡日期', '补卡日期'],
      applicant: OA_APPLICANT_ALIASES.slice(),
      department: OA_DEPT_ALIASES.slice(),
      subjectPerson: ['忘打卡人员', '漏打卡人员', '补卡人员', '未打卡人员', '被申请人', '受益人'],
      missTime: ['未打卡时间', '漏打卡时间'],
      cardTime: ['当天刷卡时间', '刷卡时间'],
      reason: ['事由', '原因', '说明'],
      isSelf: OA_SELF_ALIASES.slice(),
    },
  },
};

export const TYPE_IDENTIFY = {
  punch: { required: ['employeeNo', 'signIn'], bonus: ['signOut', 'lateMinutes', 'department', 'date', 'scheduleStart', 'scheduleEnd'] },
  leave: { required: ['leaveType', 'startDate'], bonus: ['endDate', 'leaveDays', 'applicant', 'department', 'isSelf', 'subjectPerson'] },
  overtime: { required: ['overtimeRange'], requiredAlt: ['startTime', 'endTime'], bonus: ['applicant', 'department', 'content', 'isSelf', 'subjectPerson', 'overtimeHours'] },
  travel: { required: ['travelRange'], bonus: ['applicant', 'destination', 'reason', 'travelers', 'isSelf'] },
  miss_punch: { required: ['missDate'], bonus: ['applicant', 'subjectPerson', 'missTime', 'reason', 'isSelf'] },
};

export const RECORD_SCHEMA = {
  punch: {
    oa: false,
    fields: {
      employeeNo: 'str', customNo: 'str', name: 'str', date: 'date', period: 'str',
      scheduleStart: 'time', scheduleEnd: 'time', signIn: 'time', signOut: 'time',
      lateMinutes: 'num', earlyMinutes: 'num', absent: 'bool', overtimeHours: 'num',
      workHours: 'num', department: 'str', isWeekday: 'str', isWeekend: 'str',
      isHoliday: 'str', weekdayOT: 'num', weekendOT: 'num', holidayOT: 'num',
    },
  },
  leave: {
    oa: true,
    after: 'leaveEndFallback',
    fields: {
      department: 'str', leaveType: 'str', startDate: 'date', endDate: 'date',
      leaveDays: 'num', leaveHours: 'num', reason: 'str',
    },
    order: ['applicant', 'department', 'leaveType', 'startDate', 'endDate', 'leaveDays', 'leaveHours', 'reason', 'isSelf', 'subject'],
  },
  overtime: {
    oa: true,
    after: 'overtimeRange',
    fields: { department: 'str', overtimeHours: 'num', content: 'str' },
    order: ['applicant', 'department', 'startTime', 'endTime', 'overtimeHours', 'content', 'isSelf', 'subject'],
  },
  travel: {
    oa: true,
    after: 'travelRange',
    fields: { department: 'str', destination: 'str', travelType: 'str', reason: 'str' },
    order: ['applicant', 'department', 'destination', 'travelers', 'startDate', 'endDate', 'travelType', 'reason', 'isSelf', 'subject'],
  },
  miss_punch: {
    oa: true,
    after: 'missPerson',
    fields: { department: 'str', missDate: 'date', missTime: 'time', cardTime: 'time', reason: 'str' },
    order: ['applicant', 'department', 'missDate', 'missPerson', 'missTime', 'cardTime', 'reason', 'isSelf', 'subject'],
  },
};

export const FIELD_LABELS = {
  punch: {
    employeeNo: '考勤号码', customNo: '自定义编号', name: '姓名', date: '日期',
    period: '对应时段', scheduleStart: '上班时间', scheduleEnd: '下班时间',
    signIn: '签到时间', signOut: '签退时间', lateMinutes: '迟到时间',
    earlyMinutes: '早退时间', absent: '是否旷工', overtimeHours: '加班时间',
    workHours: '工作时间', department: '部门', isWeekday: '平日',
    isWeekend: '周末', isHoliday: '节假日', weekdayOT: '平日加班',
    weekendOT: '周末加班', holidayOT: '节假日加班',
  },
  leave: {
    leaveType: '请假类型', startDate: '开始日期', endDate: '结束日期', leaveDays: '请假天数',
    leaveHours: '请假小时', applicant: '申请人', department: '申请部门', reason: '请假事由',
    isSelf: '是否本人', subjectPerson: '请假人员',
  },
  miss_punch: {
    missDate: '忘打卡日期', applicant: '申请人', department: '申请部门',
    subjectPerson: '忘打卡人员', missTime: '未打卡时间', cardTime: '当天刷卡时间',
    reason: '事由', isSelf: '是否本人',
  },
  overtime: {
    overtimeRange: '加班起止时间', startTime: '开始时间', endTime: '结束时间', overtimeHours: '加班小时',
    applicant: '申请人', department: '申请部门', content: '加班内容',
    isSelf: '是否本人', subjectPerson: '加班人员',
  },
  travel: {
    travelRange: '出差起止日期', applicant: '申请人', department: '申请部门',
    destination: '目的地', travelers: '出差人员', travelType: '出差类型',
    reason: '出差事由', isSelf: '是否本人', subjectPerson: '实际出差人',
  },
};

export const PREVIEW_LABELS = {
  punch: Object.assign({}, FIELD_LABELS.punch),
  leave: Object.assign({}, FIELD_LABELS.leave, { subject: '实际人员' }),
  overtime: Object.assign({}, FIELD_LABELS.overtime, { subject: '实际人员' }),
  travel: Object.assign({}, FIELD_LABELS.travel, { subject: '实际人员' }),
  miss_punch: Object.assign({}, FIELD_LABELS.miss_punch, { subject: '实际人员', missPerson: '忘打卡人员' }),
  schedule: { date: '日期', work: '班次', year: '年', month: '月', day: '日' },
};

export function labelForField(fileType, field) {
  const map = PREVIEW_LABELS[fileType] || FIELD_LABELS[fileType] || {};
  return map[field] || field;
}

export function normalizeHeader(h) {
  return String(h || '').replace(/\s+/g, '').trim();
}

export function uniquifyHeaders(headerRow) {
  const seen = Object.create(null);
  return (headerRow || []).map((h) => {
    const base = normalizeHeader(h);
    if (!base) return '';
    seen[base] = (seen[base] || 0) + 1;
    return seen[base] === 1 ? base : `${base}#${seen[base]}`;
  });
}

export function headerBase(h) {
  return normalizeHeader(h).replace(/#\d+$/, '');
}

export function compactHeader(h) {
  return normalizeHeader(h).replace(/[是否为的了吧呢啊_\-]/g, '');
}

export function mergeFieldMap(saved) {
  const base = JSON.parse(JSON.stringify(DEFAULT_OA_FIELD_MAP));
  if (!saved || typeof saved !== 'object') return base;
  if (Array.isArray(saved.selfTrueValues) && saved.selfTrueValues.length) {
    base.selfTrueValues = saved.selfTrueValues.map(normalizeHeader).filter(Boolean);
  }
  if (Array.isArray(saved.selfFalseValues) && saved.selfFalseValues.length) {
    base.selfFalseValues = saved.selfFalseValues.map(normalizeHeader).filter(Boolean);
  }
  const types = saved.types && typeof saved.types === 'object' ? saved.types : saved;
  for (const type of Object.keys(base.types)) {
    const src = types[type];
    if (!src || typeof src !== 'object') continue;
    for (const field of Object.keys(base.types[type])) {
      if (Array.isArray(src[field])) {
        const next = src[field].map(normalizeHeader).filter(Boolean);
        if (next.length) base.types[type][field] = next;
      }
    }
  }
  return base;
}

export function isSelfValue(val, trueVals, falseVals) {
  const s = normalizeHeader(val);
  if (!s) return null;
  const t = (trueVals && trueVals.length ? trueVals : DEFAULT_TRUE_VALUES).map(normalizeHeader);
  const f = (falseVals && falseVals.length ? falseVals : DEFAULT_FALSE_VALUES).map(normalizeHeader);
  const upper = s.toUpperCase();
  if (t.some((x) => x && (s === x || upper === x.toUpperCase()))) return true;
  if (f.some((x) => x && (s === x || upper === x.toUpperCase() || (x.length >= 2 && s.includes(x))))) return false;
  if (/非本人|不本人|否本人/.test(s)) return false;
  if (s.includes('本人')) return true;
  return false;
}

export function resolveSubject(isSelfRaw, applicant, otherPerson, trueVals, falseVals) {
  const applicantName = String(applicant || '').trim();
  const other = String(otherPerson || '').trim();
  if (isSelfValue(isSelfRaw, trueVals, falseVals) === true) return applicantName;
  return other || applicantName;
}

function nonempty(val) {
  return val != null && String(val).trim() !== '';
}

function affixContains(longer, shorter) {
  if (!longer || !shorter || longer === shorter) return false;
  return longer.startsWith(shorter) || longer.endsWith(shorter);
}

function scoreHeader(header, alias) {
  if (!header || !alias) return 0;
  const h = headerBase(header);
  if (!h) return 0;
  if (h === alias) return 100;
  const ch = compactHeader(h);
  const ca = compactHeader(alias);
  if (ch && ca && ch === ca && ch.length >= 2) return 80;
  if (affixContains(h, alias) || affixContains(alias, h)) return 60;
  if (ch && ca && ch.length >= 3 && ca.length >= 3 && (affixContains(ch, ca) || affixContains(ca, ch))) return 40;
  return 0;
}

function emptyHit() {
  return { value: '', header: '', fuzzy: false, score: 0 };
}

function headerOrdinal(header) {
  const m = String(header || '').match(/#(\d+)$/);
  return m ? Number(m[1]) : 1;
}

export function listMatchingHeaders(clean, aliases) {
  const list = (aliases || []).map(normalizeHeader).filter(Boolean);
  const hits = [];
  for (const k of Object.keys(clean || {})) {
    let best = 0;
    for (const a of list) {
      const score = scoreHeader(k, a);
      if (score > best) best = score;
    }
    if (best >= 40) {
      hits.push({
        value: clean[k] == null ? '' : clean[k],
        header: k,
        fuzzy: best < 100,
        score: best,
      });
    }
  }
  hits.sort((a, b) => headerOrdinal(a.header) - headerOrdinal(b.header));
  return hits;
}

export function pickApplicantAndOther(clean, applicantAliases, subjectAliases) {
  const applicantHits = listMatchingHeaders(clean, applicantAliases);
  const subjectHits = listMatchingHeaders(clean, subjectAliases);
  const applicant = applicantHits[0] || emptyHit();
  const used = applicant.header;
  const otherFromSubject = subjectHits.find((h) => h.header !== used);
  const other = otherFromSubject || applicantHits[1] || emptyHit();
  return { applicant, other };
}

export function pickField(clean, aliases) {
  const list = (aliases || []).map(normalizeHeader).filter(Boolean);
  const keys = Object.keys(clean);
  let best = { value: '', header: '', fuzzy: false, score: 0 };
  for (const a of list) {
    for (const k of keys) {
      const score = scoreHeader(k, a);
      if (score < 40) continue;
      const filled = nonempty(clean[k]);
      const betterScore = score > best.score;
      const sameScoreFilled = score === best.score && filled && !nonempty(best.value);
      if (betterScore || sameScoreFilled) {
        best = { value: clean[k] == null ? '' : clean[k], header: k, fuzzy: score < 100, score };
      }
    }
  }
  return { value: best.value, header: best.header, fuzzy: best.fuzzy, score: best.score };
}

export function headerExists(headers, aliases) {
  const normalized = (headers || []).map(normalizeHeader).filter(Boolean);
  const list = (aliases || []).map(normalizeHeader).filter(Boolean);
  for (const h of normalized) {
    for (const a of list) {
      if (scoreHeader(h, a) >= 40) return true;
    }
  }
  return false;
}

export const FieldMap = {
  async getMap() {
    try {
      const entry = await Store.getByKey('settings', OA_FIELD_MAP_KEY);
      let saved = entry && entry.value !== undefined ? entry.value : entry;
      if (typeof saved === 'string') {
        try { saved = JSON.parse(saved); } catch (e) { saved = null; }
      }
      return mergeFieldMap(saved);
    } catch (e) {
      return mergeFieldMap(null);
    }
  },

  async saveMap(map) {
    const merged = mergeFieldMap(map);
    await Store.put('settings', { key: OA_FIELD_MAP_KEY, value: merged });
    return merged;
  },

  async learnMany(items) {
    if (!items || !items.length) return null;
    const map = await this.getMap();
    let changed = false;
    for (const item of items) {
      const type = item.type;
      const field = item.field;
      const header = normalizeHeader(item.header);
      if (!type || !field || !header) continue;
      if (!map.types[type] || !map.types[type][field]) continue;
      const list = map.types[type][field];
      if (!list.includes(header)) {
        list.unshift(header);
        changed = true;
      }
    }
    if (changed) await this.saveMap(map);
    return changed ? map : null;
  },
};

export default FieldMap;
