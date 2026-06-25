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

  exportToExcel(records, template, filename) {
    const headers = template.fields.map(f => f.label);
    const data = records.map((rec, idx) => {
      return template.fields.map(f => {
        if (f.field === '_index') return idx + 1;
        return rec[f.field] !== undefined ? rec[f.field] : '';
      });
    });
    const ws = XLSX.utils.aoa_to_sheet([headers, ...data]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, '考勤记录');
    XLSX.writeFile(wb, filename || 'attendance_export.xlsx');
  },

  async exportCalendarReport(targetMonth) {
    const [yearStr, monthStr] = targetMonth.split('-');
    const y = parseInt(yearStr);
    const m = parseInt(monthStr);
    const lastDay = new Date(y, m, 0).getDate();

    const results = await Store.getByIndex('attendance_results', 'month', targetMonth);
    if (results.length === 0) throw new Error('没有考勤结果，请先执行计算');

    const allSchedules = await Store.getByIndex('schedules', 'year', y);
    const scheduleForMonth = allSchedules.filter(s => s.month === m);

    const deptEmployees = {};
    const empMap = {};
    for (const r of results) {
      if (!deptEmployees[r.department]) deptEmployees[r.department] = new Set();
      deptEmployees[r.department].add(r.employeeNo);
      if (!empMap[r.employeeNo]) empMap[r.employeeNo] = { name: r.name, department: r.department };
    }

    const deptCols = [];
    for (const [dept, enoSet] of Object.entries(deptEmployees)) {
      deptCols.push({ department: dept, employees: [...enoSet].sort() });
    }

    const dateToSerial = (year, month, day) => {
      return month + '月' + day + '日';
    };

    const headerRow1 = ['日期', '排班', '打卡时间'];
    const headerRow2 = ['', '', ''];
    for (const dc of deptCols) {
      for (let i = 0; i < dc.employees.length; i++) {
        headerRow1.push(i === 0 ? dc.department : '');
        headerRow2.push(empMap[dc.employees[i]].name);
      }
    }

    const rows = [headerRow1, headerRow2];
    const merges = [
      { s: { r: 0, c: 0 }, e: { r: 1, c: 0 } },
      { s: { r: 0, c: 1 }, e: { r: 1, c: 1 } },
      { s: { r: 0, c: 2 }, e: { r: 1, c: 2 } }
    ];

    let deptStart = 3;
    for (const dc of deptCols) {
      if (dc.employees.length > 1) {
        merges.push({ s: { r: 0, c: deptStart }, e: { r: 0, c: deptStart + dc.employees.length - 1 } });
      }
      deptStart += dc.employees.length;
    }

    let rowIdx = 2;

    for (let d = 1; d <= lastDay; d++) {
      const dateStr = `${targetMonth}-${String(d).padStart(2, '0')}`;
      const dayNum = String(d).padStart(2, '0');
      const dateSerial = dateToSerial(y, m, d);

      const sched = scheduleForMonth.find(s => {
        const match = s.workDays && s.workDays[dayNum] === true;
        return match;
      });
      const isRest = (!sched) && scheduleForMonth.length > 0;
      const scheduleLabel = isRest ? '休息日' : '工作日';

      const amRow = [dateSerial, scheduleLabel, '上午'];
      const pmRow = ['', '', '下午'];

      for (const dc of deptCols) {
        for (const eno of dc.employees) {
          const dayResults = results.filter(r => r.employeeNo === eno && r.date === dateStr);
          const r = dayResults[0];

          if (!r) {
            amRow.push(''); pmRow.push('');
            continue;
          }

          const signIn = r.signIn || '';
          const signOut = r.signOut || '';

          const annotations = [];
          if (r.leaveType) annotations.push(r.leaveType);
          if (r.overtimeHours > 0) annotations.push('加班 ' + r.overtimeHours + 'h');
          if (r.travelHours > 0) annotations.push('出差');

          const hasMissPunch = r.sourceMissIds && r.sourceMissIds.length > 0;
          if (hasMissPunch && signIn && !signOut) annotations.push('下午补卡');
          if (hasMissPunch && !signIn && signOut) annotations.push('上午补卡');

          if (annotations.length > 0) {
            amRow.push(annotations.join(' / '));
            pmRow.push(signOut ? signOut : '');
          } else if (r.status === 'rest') {
            amRow.push(''); pmRow.push('');
          } else if (r.status === 'leave' || r.status === 'travel') {
            amRow.push(r.status === 'leave' ? '请假' : '出差');
            pmRow.push('');
          } else if (r.absent) {
            amRow.push('缺勤'); pmRow.push('');
          } else {
            amRow.push(signIn || '');
            pmRow.push(signOut || '');
          }
        }
      }

      rows.push(amRow);
      rows.push(pmRow);

      merges.push({ s: { r: rowIdx, c: 0 }, e: { r: rowIdx + 1, c: 0 } });
      merges.push({ s: { r: rowIdx, c: 1 }, e: { r: rowIdx + 1, c: 1 } });

      rowIdx += 2;
    }

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws['!merges'] = merges;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, y + '年' + m + '月考勤');
    XLSX.writeFile(wb, '考勤月报_' + targetMonth + '.xlsx');
  }
};
