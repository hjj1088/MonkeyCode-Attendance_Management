// shared/excel.js
// SheetJS 封装 - Excel 解析、排班表颜色识别、导出

const Excel = {
  parseExcelFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = function(e) {
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

  sheetToJson(ws) {
    return XLSX.utils.sheet_to_json(ws, { defval: '' });
  },

  sheetToArray(ws) {
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

  parseScheduleSheet(ws, sheetName) {
    const result = { year: null, month: null, workDays: {} };

    const monthMatch = sheetName.trim().match(/^(\d{1,2})月$/);
    if (!monthMatch) return null;
    result.month = parseInt(monthMatch[1]);

    const rows = this.sheetToArray(ws);

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

  parseAllScheduleSheets(wb) {
    const results = [];
    const names = this.getSheetNames(wb);
    for (const name of names) {
      const trimmed = name.trim();
      if (/^\d{1,2}月$/.test(trimmed)) {
        const ws = wb.Sheets[name];
        const parsed = this.parseScheduleSheet(ws, trimmed);
        if (parsed) results.push(parsed);
      }
    }
    return results;
  },

  identifyFileType(wb) {
    const names = this.getSheetNames(wb);
    if (this.isScheduleWorkbook(wb)) {
      return { type: 'schedule', confidence: 1.0 };
    }

    let ws = null;
    for (const name of names) {
      const s = wb.Sheets[name];
      const rows = this.sheetToArray(s);
      if (rows.length > 1) { ws = s; break; }
    }
    if (!ws) return { type: 'unknown', confidence: 0 };

    const headerRow = this.sheetToArray(ws)[0] || [];
    const headers = headerRow.map(h => String(h || '').trim().replace(/\s+/g, ''));

    const typeRules = [
      { type: 'punch', required: ['考勤号码', '签到时间'], bonus: ['签退时间', '迟到时间', '部门', '日期', '上班时间', '下班时间'] },
      { type: 'leave', required: ['请假类型', '开始日期'], bonus: ['结束日期', '请假天数', '申请人', '申请部门'] },
      { type: 'overtime', required: ['加班起止时间'], bonus: ['申请人', '申请部门', '加班内容'] },
      { type: 'travel', required: ['出差起止日期'], bonus: ['申请人', '目的地', '出差事由', '出差人员'] },
      { type: 'miss_punch', required: ['忘打卡日期'], bonus: ['申请人', '忘打卡人员', '未打卡时间', '事由'] }
    ];

    let bestType = 'unknown';
    let bestScore = 0;
    for (const rule of typeRules) {
      const requiredMatch = rule.required.every(r => headers.includes(r));
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

  parseRecords(wb, fileType) {
    const names = this.getSheetNames(wb);
    if (fileType === 'schedule') {
      return this.parseAllScheduleSheets(wb);
    }
    const ws = wb.Sheets[names[0]];
    const raw = this.sheetToJson(ws);
    return raw.map(row => this._normalizeRecord(row, fileType)).filter(Boolean);
  },

  _normalizeRecord(row, fileType) {
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
          date: this._formatDate(clean['日期']),
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

      case 'leave':
        const leaveStart = this._formatDate(clean['开始日期']);
        const leaveEnd = this._formatDate(clean['结束日期']);
        return {
          applicant: clean['申请人'] || '',
          department: clean['申请部门'] || '',
          leaveType: clean['请假类型'] || '',
          startDate: leaveStart,
          endDate: leaveEnd || leaveStart,
          leaveDays: parseFloat(clean['请假天数']) || 0,
          leaveHours: parseFloat(clean['小时']) || 0,
          reason: clean['请假事由'] || ''
        };

      case 'overtime':
        const otHours = clean['小时'] || '';
        return {
          applicant: clean['申请人'] || '',
          department: clean['申请部门'] || '',
          startTime: '',
          endTime: '',
          overtimeHours: parseFloat(otHours) || 0,
          content: clean['加班内容'] || ''
        };

      case 'travel':
        const travelDate = clean['出差起止日期'] || '';
        const travelDateParts = travelDate.split(/[~至到]/).filter(Boolean);
        const travelStart = travelDateParts[0] || '';
        const travelEnd = travelDateParts[1] || travelStart;
        return {
          applicant: clean['申请人'] || '',
          department: clean['申请部门'] || '',
          destination: clean['目的地'] || '',
          travelers: clean['出差人员'] || '',
          startDate: this._formatDate(travelStart),
          endDate: this._formatDate(travelEnd),
          travelType: clean['出差类型'] || '',
          reason: clean['出差事由'] || ''
        };

      case 'miss_punch':
        return {
          applicant: clean['申请人'] || '',
          department: clean['申请部门'] || '',
          missDate: this._formatDate(clean['忘打卡日期']),
          missPerson: clean['忘打卡人员'] || '',
          missTime: this._formatTime(clean['未打卡时间']),
          cardTime: this._formatTime(clean['当天刷卡时间']),
          reason: clean['事由'] || ''
        };

      default:
        return null;
    }
  },

  _formatDate(val) {
    if (!val && val !== 0) return '';
    if (typeof val === 'number') {
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

  async _apiExport(endpoint, data, filename) {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

   exportToExcel(records, template, filename) {
    return Excel._apiExport('/api/export/flat', {
      records: records,
      template: template,
      filename: filename || 'attendance_export.xlsx'
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

    return Excel._apiExport('/api/export/calendar', {
      targetMonth: targetMonth,
      fields: fields || [],
      results: results,
      schedules: scheduleForMonth,
      holidays: holidaysForMonth
    }, '考勤明细_' + targetMonth + '.xlsx');
  }
};
