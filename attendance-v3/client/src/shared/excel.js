// shared/excel.js
// SheetJS 封装 - Excel 解析、排班表颜色识别、导出（ES Module 化，无 IndexedDB 依赖）
// XLSX 882KB 库懒加载：首次调用任何解析/导出方法时动态注入 <script>，避免阻塞 SPA 首屏（登录页）

import Store from './store';

let _xlsxLoading = null;

function getXLSX() {
  if (window.XLSX) return Promise.resolve(window.XLSX);
  if (!_xlsxLoading) {
    _xlsxLoading = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = '/lib/xlsx.min.js';
      s.onload = () => resolve(window.XLSX);
      s.onerror = () => { _xlsxLoading = null; reject(new Error('xlsx.min.js 加载失败')); };
      document.head.appendChild(s);
    });
  }
  return _xlsxLoading;
}

async function withXLSX() {
  const X = await getXLSX();
  if (!X) throw new Error('XLSX 库不可用');
  return X;
}

export const Excel = {
  async parseExcelFile(file) {
    const XLSX = await withXLSX();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = function (e) {
        try {
          const data = new Uint8Array(e.target.result);
          const wb = XLSX.read(data, { type: 'array', cellStyles: true });
          resolve(wb);
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  },

  getSheetNames(wb) {
    return wb.SheetNames || [];
  },

  async sheetToJson(ws) {
    const XLSX = await withXLSX();
    return XLSX.utils.sheet_to_json(ws, { defval: '' });
  },

  async sheetToArray(ws) {
    const XLSX = await withXLSX();
    return XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
  },

  _hasFill(cell) {
    if (!cell || !cell.s) return false;
    if (cell.s.patternType === 'none') return false;
    const fill = cell.s.fgColor || cell.s.bgColor;
    if (!fill) return false;
    if (fill.rgb === 'FFFFFF' || fill.rgb === 'FFFFFFFF') return false;
    if (fill.indexed === 64 || fill.indexed === 65) return false;
    if (fill.theme === 1 && fill.tint === 0) return false;
    return !!fill.rgb || (fill.indexed != null && fill.indexed !== 64 && fill.indexed !== 65);
  },

  async parseScheduleSheet(ws, sheetName) {
    const XLSX = await withXLSX();
    const result = { year: null, month: null, workDays: {} };

    const monthMatch = sheetName.trim().match(/^(\d{1,2})月$/);
    if (!monthMatch) return null;
    result.month = parseInt(monthMatch[1]);

    const rows = await this.sheetToArray(ws);

    for (let i = 0; i < rows.length && !result.year; i++) {
      const row = rows[i];
      if (!row) continue;
      const joined = row.filter(Boolean).join('');
      const yearMatch = joined.match(/(\d{4})年/);
      if (yearMatch) {
        result.year = parseInt(yearMatch[1]);
        break;
      }
    }
    if (!result.year) return null;

    let headerRowIdx = -1;
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (!row) continue;
      const text = row.map(c => String(c || '').trim()).join('|');
      if (text.includes('周次') && text.includes('周一') && text.includes('周日')) {
        headerRowIdx = i;
        break;
      }
    }
    if (headerRowIdx < 0) return null;

    const headerRow = rows[headerRowIdx];
    const colMap = {};
    for (let i = 0; i < headerRow.length; i++) {
      const h = String(headerRow[i] || '').trim();
      if (h === '周一') colMap['周一'] = i;
      else if (h === '周二') colMap['周二'] = i;
      else if (h === '周三') colMap['周三'] = i;
      else if (h === '周四') colMap['周四'] = i;
      else if (h === '周五') colMap['周五'] = i;
      else if (h === '周六') colMap['周六'] = i;
      else if (h === '周日') colMap['周日'] = i;
    }

    if (Object.keys(colMap).length < 7) {
      for (let i = 0; i < headerRow.length; i++) {
        const h = String(headerRow[i] || '').trim();
        if (/^周[一二三四五六日]$/.test(h)) {
          colMap[h] = i;
        }
      }
    }

    const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

    for (let i = headerRowIdx + 1; i < rows.length; i++) {
      const row = rows[i];
      if (!row || row.every(c => c === '' || c == null)) continue;

      for (const dayName of dayNames) {
        const colIdx = colMap[dayName];
        if (colIdx == null) continue;
        const val = row[colIdx];
        if (val === '' || val == null) continue;

        const dateNum = parseInt(val);
        if (isNaN(dateNum) || dateNum < 1 || dateNum > 31) continue;

        const cellRef = XLSX.utils.encode_cell({ r: i, c: colIdx });
        const cell = ws[cellRef];
        const isRest = this._hasFill(cell);
        const dateStr = String(dateNum).padStart(2, '0');
        result.workDays[dateStr] = !isRest;
      }
    }

    return result;
  },

  isScheduleWorkbook(wb) {
    const names = this.getSheetNames(wb);
    return names.some(name => {
      const trimmed = name.trim();
      return /^\d{1,2}月$/.test(trimmed);
    });
  },

  async parseAllScheduleSheets(wb) {
    const XLSX = await withXLSX();
    const results = [];
    const names = this.getSheetNames(wb);
    for (const name of names) {
      const trimmed = name.trim();
      if (/^\d{1,2}月$/.test(trimmed)) {
        const ws = wb.Sheets[name];
        const parsed = await this.parseScheduleSheet(ws, trimmed);
        if (parsed) results.push(parsed);
      }
    }
    return results;
  },

  flattenScheduleDays(monthRecords) {
    const days = [];
    for (const rec of monthRecords || []) {
      const y = rec.year;
      const m = rec.month;
      if (!y || !m) continue;
      const monthStr = String(m).padStart(2, '0');
      const keys = Object.keys(rec.workDays || {}).sort();
      for (const d of keys) {
        days.push({
          date: y + '-' + monthStr + '-' + d,
          year: y,
          month: m,
          day: Number(d),
          work: rec.workDays[d] ? '上班' : '休息',
        });
      }
    }
    return days;
  },

  async identifyFileType(wb) {
    const names = this.getSheetNames(wb);
    if (this.isScheduleWorkbook(wb)) {
      return { type: 'schedule', confidence: 1.0 };
    }

    let ws = null;
    for (const name of names) {
      const s = wb.Sheets[name];
      const rows = await this.sheetToArray(s);
      if (rows.length > 1) { ws = s; break; }
    }
    if (!ws) return { type: 'unknown', confidence: 0 };

    const headerRow = (await this.sheetToArray(ws))[0] || [];
    const headers = headerRow.map(h => String(h || '').trim().replace(/\s+/g, ''));

    const typeRules = [
      { type: 'punch', required: ['考勤号码', '签到时间'], bonus: ['签退时间', '迟到时间', '部门', '日期', '上班时间', '下班时间'] },
      { type: 'leave', required: ['请假类型', '开始日期'], bonus: ['结束日期', '请假天数', '申请人', '申请部门', '是否本人', '请假人员'] },
      { type: 'overtime', required: ['加班起止时间'], requiredAlt: ['开始时间', '结束时间'], bonus: ['申请人', '申请部门', '加班内容', '是否本人', '加班人员', '小时'] },
      { type: 'travel', required: ['出差起止日期'], bonus: ['申请人', '目的地', '出差事由', '出差人员', '是否本人'] },
      { type: 'miss_punch', required: ['忘打卡日期'], bonus: ['申请人', '忘打卡人员', '未打卡时间', '事由', '是否本人'] }
    ];

    let bestType = 'unknown';
    let bestScore = 0;
    for (const rule of typeRules) {
      const requiredMatch = rule.required.every(r => headers.includes(r))
        || (rule.requiredAlt ? rule.requiredAlt.every(r => headers.includes(r)) : false);
      if (!requiredMatch) continue;
      const bonusMatch = rule.bonus.filter(b => headers.includes(b)).length;
      const score = rule.required.length + bonusMatch;
      if (score > bestScore) {
        bestScore = score;
        bestType = rule.type;
      }
    }
    return { type: bestType, confidence: bestType !== 'unknown' ? Math.min(bestScore / 8, 1.0) : 0 };
  },

  async parseRecords(wb, fileType) {
    const names = this.getSheetNames(wb);
    if (fileType === 'schedule') {
      return this.parseAllScheduleSheets(wb);
    }
    const ws = wb.Sheets[names[0]];
    const raw = await this.sheetToJson(ws);
    const records = [];
    for (const row of raw) {
      const rec = await this._normalizeRecord(row, fileType);
      if (rec) records.push(rec);
    }
    return records;
  },

  _isSelfValue(val) {
    const s = String(val || '').replace(/\s+/g, '');
    if (!s) return null;
    if (s === '本人' || s === '是' || s === 'Y' || /^yes$/i.test(s) || /^true$/i.test(s)) return true;
    return false;
  },

  _resolveSubject(isSelfRaw, applicant, otherPerson) {
    const applicantName = String(applicant || '').trim();
    const other = String(otherPerson || '').trim();
    if (this._isSelfValue(isSelfRaw) === true) return applicantName;
    return other || applicantName;
  },

  async _normalizeRecord(row, fileType) {
    const clean = {};
    for (const key of Object.keys(row)) {
      const cleanKey = key.replace(/\s+/g, '');
      clean[cleanKey] = row[key];
    }

    switch (fileType) {
      case 'punch':
        return {
          employeeNo: clean['考勤号码'] || clean['考勤号'] || '',
          customNo: clean['自定义编号'] || '',
          name: clean['姓名'] || '',
          date: await this._formatDate(clean['日期']),
          period: clean['对应时段'] || '',
          scheduleStart: this._formatTime(clean['上班时间']),
          scheduleEnd: this._formatTime(clean['下班时间']),
          signIn: this._formatTime(clean['签到时间']),
          signOut: this._formatTime(clean['签退时间']),
          lateMinutes: parseFloat(clean['迟到时间']) || 0,
          earlyMinutes: parseFloat(clean['早退时间']) || 0,
          absent: ['是', 'True', 'true', 'TRUE', '1'].includes(String(clean['是否旷工'] || '')),
          overtimeHours: parseFloat(clean['加班时间']) || 0,
          workHours: parseFloat(clean['工作时间']) || 0,
          department: clean['部门'] || '',
          isWeekday: clean['平日'] || '',
          isWeekend: clean['周末'] || '',
          isHoliday: clean['节假日'] || '',
          weekdayOT: parseFloat(clean['平日加班']) || 0,
          weekendOT: parseFloat(clean['周末加班']) || 0,
          holidayOT: parseFloat(clean['节假日加班']) || 0
        };

      case 'leave': {
        const leaveStart = await this._formatDate(clean['开始日期']);
        const leaveEnd = await this._formatDate(clean['结束日期']);
        const leaveApplicant = clean['申请人'] || '';
        const leaveIsSelf = String(clean['是否本人'] || '').trim();
        return {
          applicant: leaveApplicant,
          department: clean['申请部门'] || '',
          leaveType: clean['请假类型'] || '',
          startDate: leaveStart,
          endDate: leaveEnd || leaveStart,
          leaveDays: parseFloat(clean['请假天数']) || 0,
          leaveHours: parseFloat(clean['小时']) || 0,
          reason: clean['请假事由'] || '',
          isSelf: leaveIsSelf,
          subject: this._resolveSubject(leaveIsSelf, leaveApplicant, clean['请假人员'])
        };
      }

      case 'overtime': {
        const otRange = clean['加班起止时间'] || '';
        const otHours = clean['小时'] || '';
        const otApplicant = clean['申请人'] || '';
        const otIsSelf = String(clean['是否本人'] || '').trim();
        const hasRange = String(otRange).trim() !== '';
        const otStart = hasRange
          ? (typeof otRange === 'number' ? (otRange > 1 ? await this._formatDate(otRange) : this._formatTime(otRange)) : String(otRange).trim())
          : await this._formatDateTime(clean['开始时间']);
        return {
          applicant: otApplicant,
          department: clean['申请部门'] || '',
          startTime: otStart,
          endTime: hasRange ? '' : await this._formatDateTime(clean['结束时间']),
          overtimeHours: parseFloat(otHours) || 0,
          content: clean['加班内容'] || '',
          isSelf: otIsSelf,
          subject: this._resolveSubject(otIsSelf, otApplicant, clean['加班人员'])
        };
      }

      case 'travel': {
        const travelDate = clean['出差起止日期'] || '';
        const travelDateParts = travelDate.split(/[~至到]/).filter(Boolean);
        const travelStart = travelDateParts[0] || '';
        const travelEnd = travelDateParts[1] || travelStart;
        const travelApplicant = clean['申请人'] || '';
        const travelIsSelf = String(clean['是否本人'] || '').trim();
        const travelers = clean['出差人员'] || '';
        return {
          applicant: travelApplicant,
          department: clean['申请部门'] || '',
          destination: clean['目的地'] || '',
          travelers,
          startDate: await this._formatDate(travelStart),
          endDate: await this._formatDate(travelEnd),
          travelType: clean['出差类型'] || '',
          reason: clean['出差事由'] || '',
          isSelf: travelIsSelf,
          subject: this._resolveSubject(travelIsSelf, travelApplicant, travelers)
        };
      }

      case 'miss_punch': {
        const missApplicant = clean['申请人'] || '';
        const missIsSelf = String(clean['是否本人'] || '').trim();
        const missPerson = clean['忘打卡人员'] || '';
        return {
          applicant: missApplicant,
          department: clean['申请部门'] || '',
          missDate: await this._formatDate(clean['忘打卡日期']),
          missPerson,
          missTime: this._formatTime(clean['未打卡时间']),
          cardTime: this._formatTime(clean['当天刷卡时间']),
          reason: clean['事由'] || '',
          isSelf: missIsSelf,
          subject: this._resolveSubject(missIsSelf, missApplicant, missPerson)
        };
      }

      default:
        return null;
    }
  },

  async _formatDate(val) {
    if (!val && val !== 0) return '';
    if (typeof val === 'number') {
      const XLSX = await withXLSX();
      const date = XLSX.SSF.parse_date_code(val);
      if (date) {
        return `${date.y}-${String(date.m).padStart(2, '0')}-${String(date.d).padStart(2, '0')}`;
      }
    }
    const str = String(val).trim();
    const match = str.match(/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})/);
    if (match) {
      return `${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}`;
    }
    return str;
  },

  _formatTime(val) {
    if (!val && val !== 0) return '';
    if (typeof val === 'number' && val < 1) {
      const hours = Math.floor(val * 24);
      const minutes = Math.round((val * 24 - hours) * 60);
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    }
    const str = String(val).trim();
    const match = str.match(/(\d{1,2}):(\d{2})/);
    if (match) {
      return `${match[1].padStart(2, '0')}:${match[2]}`;
    }
    return str;
  },

  async _formatDateTime(val) {
    if (!val && val !== 0) return '';
    if (typeof val === 'number') {
      const XLSX = await withXLSX();
      const date = XLSX.SSF.parse_date_code(val);
      if (date) {
        const base = `${date.y}-${String(date.m).padStart(2, '0')}-${String(date.d).padStart(2, '0')}`;
        if (date.H || date.M) {
          return `${base} ${String(date.H).padStart(2, '0')}:${String(date.M).padStart(2, '0')}`;
        }
        return base;
      }
    }
    const str = String(val).trim();
    const match = str.match(/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})(?:[ T]+(\d{1,2}):(\d{1,2}))?/);
    if (match) {
      const date = `${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}`;
      if (match[4] != null) {
        return `${date} ${match[4].padStart(2, '0')}:${match[5]}`;
      }
      return date;
    }
    return str;
  },

  async _apiExport(endpoint, data, filename) {
    const token = sessionStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(data)
    });
    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error('导出失败: ' + (errText || resp.statusText));
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  _normalizeWorkTime(val) {
    const m = String(val || '').trim().match(/^(\d{1,2}):(\d{2})/);
    return m ? String(m[1]).padStart(2, '0') + ':' + m[2] : '';
  },

  async _getWorkTimes() {
    const entry = await Store.getByKey('settings', 'attendance_config');
    const cfg = (entry && entry.value) ? entry.value : (entry || {});
    return {
      startTime: this._normalizeWorkTime(cfg.workStartTime) || '08:30',
      endTime: this._normalizeWorkTime(cfg.workEndTime) || '17:30'
    };
  },

  async exportToExcel(records, template, filename) {
    const { startTime, endTime } = await Excel._getWorkTimes();
    return Excel._apiExport('/api/export/flat', {
      records: records,
      template: template,
      filename: filename || 'attendance_export.xlsx',
      startTime: startTime,
      endTime: endTime
    }, filename || 'attendance_export.xlsx');
  },

  async exportCalendarReport(targetMonth, fields) {
    const [yearStr, monthStr] = targetMonth.split('-');
    const y = parseInt(yearStr);
    const m = parseInt(monthStr);

    const results = await Store.getByIndex('attendance_results', 'month', targetMonth);
    if (results.length === 0) throw new Error('没有考勤结果，请先执行计算');

    const allSchedules = await Store.getByIndex('schedules', 'year', y);
    const scheduleForMonth = allSchedules.filter(s => s.month === m);

    const allHolidays = await Store.getAll('holidays');
    const holidaysForMonth = allHolidays.filter(h => h.date && h.date.startsWith(targetMonth));

    const { startTime, endTime } = await Excel._getWorkTimes();

    return Excel._apiExport('/api/export/calendar', {
      targetMonth: targetMonth,
      fields: fields || [],
      results: results,
      schedules: scheduleForMonth,
      holidays: holidaysForMonth,
      startTime: startTime,
      endTime: endTime
    }, '考勤明细_' + targetMonth + '.xlsx');
  }
};

export default Excel;
