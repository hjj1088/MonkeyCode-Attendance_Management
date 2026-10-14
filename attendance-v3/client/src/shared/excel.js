// shared/excel.js
// SheetJS 封装 - Excel 解析、排班表颜色识别、导出（ES Module 化，无 IndexedDB 依赖）
// XLSX 882KB 库懒加载：首次调用任何解析/导出方法时动态注入 <script>，避免阻塞 SPA 首屏（登录页）

import Store from './store';
import { FieldMap, mergeFieldMap, pickField, headerExists, resolveSubject, uniquifyHeaders, pickApplicantAndOther, headerBase, TYPE_IDENTIFY, RECORD_SCHEMA } from './fieldMap';

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

    const rows = await this.sheetToArray(ws);
    const headerIdx = this._findHeaderRowIndex(rows);
    const headers = uniquifyHeaders(rows[headerIdx] || []);
    const fmap = await this._getFieldMap();
    const types = fmap.types;
    const aliasesOf = (type, field) => (types[type] && types[type][field]) || [];

    let bestType = 'unknown';
    let bestScore = 0;
    for (const [type, rule] of Object.entries(TYPE_IDENTIFY)) {
      const requiredMatch = rule.required.every((f) => headerExists(headers, aliasesOf(type, f)))
        || (rule.requiredAlt ? rule.requiredAlt.every((f) => headerExists(headers, aliasesOf(type, f))) : false);
      if (!requiredMatch) continue;
      const bonusMatch = (rule.bonus || []).filter((f) => headerExists(headers, aliasesOf(type, f))).length;
      const score = rule.required.length + bonusMatch;
      if (score > bestScore) {
        bestScore = score;
        bestType = type;
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
    const rows = await this.sheetToArray(ws);
    const fmap = await this._getFieldMap();
    const learned = [];
    const records = [];
    if (!rows.length) return records;
    const headerIdx = this._findHeaderRowIndex(rows);
    const headers = uniquifyHeaders(rows[headerIdx] || []);
    for (let i = headerIdx + 1; i < rows.length; i++) {
      const row = rows[i] || [];
      if (row.every((c) => c === '' || c == null)) continue;
      const obj = {};
      for (let c = 0; c < headers.length; c++) {
        if (!headers[c]) continue;
        obj[headers[c]] = row[c] == null ? '' : row[c];
      }
      const rec = await this._normalizeRecord(obj, fileType, fmap, learned);
      if (rec) records.push(rec);
    }
    if (learned.length) {
      try {
        await FieldMap.learnMany(learned);
        this._fieldMapCache = null;
      } catch (e) { /* 学习失败不影响导入 */ }
    }
    return records;
  },

  _findHeaderRowIndex(rows) {
    let bestIdx = 0;
    let bestFilled = 0;
    const limit = Math.min(rows.length, 20);
    for (let i = 0; i < limit; i++) {
      const row = rows[i] || [];
      const filled = row.filter((c) => String(c || '').trim() !== '').length;
      const text = row.map((c) => String(c || '').replace(/\s+/g, '')).join('|');
      if (/申请人|请假类型|加班起止|出差起止|忘打卡|漏打卡|考勤号码|考勤号/.test(text) && filled >= bestFilled) {
        return i;
      }
      if (filled > bestFilled) {
        bestFilled = filled;
        bestIdx = i;
      }
    }
    return bestIdx;
  },

  async _getFieldMap() {
    if (this._fieldMapCache) return this._fieldMapCache;
    try {
      this._fieldMapCache = await FieldMap.getMap();
    } catch (e) {
      this._fieldMapCache = mergeFieldMap(null);
    }
    return this._fieldMapCache;
  },

  _learnHit(hit, learned, type, field) {
    if (hit && hit.fuzzy && hit.score >= 60 && hit.header && type && field) {
      learned.push({ type, field, header: headerBase(hit.header) });
    }
  },

  _pick(clean, aliases, learned, type, field) {
    const hit = pickField(clean, aliases);
    this._learnHit(hit, learned, type, field);
    return hit.value;
  },

  _pickPeople(clean, t, learned, fileType) {
    const subjectAliases = [].concat(t.subjectPerson || [], t.travelers || []);
    const picked = pickApplicantAndOther(clean, t.applicant || [], subjectAliases);
    this._learnHit(picked.applicant, learned, fileType, 'applicant');
    this._learnHit(picked.other, learned, fileType, 'subjectPerson');
    return {
      applicant: String(picked.applicant.value || '').trim(),
      other: String(picked.other.value || '').trim(),
    };
  },

  async _coerce(kind, raw) {
    if (kind === 'date') return this._formatDate(raw);
    if (kind === 'time') return this._formatTime(raw);
    if (kind === 'datetime') return this._formatDateTime(raw);
    if (kind === 'num') return parseFloat(raw) || 0;
    if (kind === 'bool') return ['是', 'True', 'true', 'TRUE', '1'].includes(String(raw || ''));
    return raw == null ? '' : raw;
  },

  async _normalizeRecord(row, fileType, fmap, learned) {
    const schema = RECORD_SCHEMA[fileType];
    if (!schema) return null;
    const clean = {};
    for (const key of Object.keys(row)) {
      clean[key.replace(/\s+/g, '')] = row[key];
    }
    const map = fmap || mergeFieldMap(null);
    const t = map.types[fileType] || {};
    const learnedList = learned || [];
    const pick = (field) => this._pick(clean, t[field], learnedList, fileType, field);
    const rec = {};
    for (const [field, kind] of Object.entries(schema.fields)) {
      rec[field] = await this._coerce(kind, pick(field));
    }
    if (schema.oa) {
      const isSelf = String(pick('isSelf') || '').trim();
      const people = this._pickPeople(clean, t, learnedList, fileType);
      rec.applicant = people.applicant;
      rec.isSelf = isSelf;
      rec.subject = resolveSubject(isSelf, people.applicant, people.other, map.selfTrueValues, map.selfFalseValues);
      if (schema.after === 'leaveEndFallback') {
        rec.endDate = rec.endDate || rec.startDate;
      } else if (schema.after === 'overtimeRange') {
        const otRange = pick('overtimeRange') || '';
        const hasRange = String(otRange).trim() !== '';
        rec.startTime = hasRange
          ? (typeof otRange === 'number' ? (otRange > 1 ? await this._formatDate(otRange) : this._formatTime(otRange)) : String(otRange).trim())
          : await this._formatDateTime(pick('startTime'));
        rec.endTime = hasRange ? '' : await this._formatDateTime(pick('endTime'));
      } else if (schema.after === 'travelRange') {
        const travelDate = pick('travelRange') || '';
        const parts = String(travelDate).split(/[~至到]/).filter(Boolean);
        rec.startDate = await this._formatDate(parts[0] || '');
        rec.endDate = await this._formatDate(parts[1] || parts[0] || '');
        rec.travelers = people.other || pick('travelers') || '';
        rec.subject = resolveSubject(isSelf, people.applicant, rec.travelers, map.selfTrueValues, map.selfFalseValues);
      } else if (schema.after === 'missPerson') {
        rec.missPerson = people.other;
        rec.subject = resolveSubject(isSelf, people.applicant, rec.missPerson, map.selfTrueValues, map.selfFalseValues);
      }
    }
    if (schema.order) {
      const ordered = {};
      for (const k of schema.order) ordered[k] = rec[k];
      return ordered;
    }
    return rec;
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
