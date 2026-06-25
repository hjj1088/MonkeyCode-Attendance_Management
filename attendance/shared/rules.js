// shared/rules.js
// 考勤规则引擎 - 迟到/早退/旷工判定、容错、结余计算

const RulesEngine = {
  async getConfig() {
    const entry = await Store.getByKey('settings', 'attendance_config');
    return entry ? entry.value : {
      workStartTime: '08:30',
      workEndTime: '17:30',
      lateThreshold: 0,
      earlyThreshold: 0,
      graceTimes: 2,
      graceMinutes: 30
    };
  },

  async getHolidays() {
    return Store.getAll('holidays');
  },

  _trimName(n) { return (n || '').replace(/\s+/g, ''); },

  _matchOA(oaRecords, employeeName, dateStr, dateStartField, dateEndField) {
    const name = this._trimName(employeeName);
    return oaRecords.filter(r => {
      if (this._trimName(r.applicant) !== name) return false;
      const start = r[dateStartField] || r.startDate || '';
      const end = r[dateEndField] || start;
      if (!start) return false;
      return dateStr >= start && dateStr <= end;
    });
  },

  _timeToMinutes(timeStr) {
    if (!timeStr) return null;
    const parts = String(timeStr).split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  },

  _calcDeviation(signIn, signOut, config) {
    let lateMinutes = 0;
    let earlyMinutes = 0;

    if (signIn) {
      const signInMin = this._timeToMinutes(signIn);
      const startMin = this._timeToMinutes(config.workStartTime);
      if (signInMin > startMin + (config.lateThreshold || 0)) {
        lateMinutes = signInMin - startMin;
      }
    }

    if (signOut) {
      const signOutMin = this._timeToMinutes(signOut);
      const endMin = this._timeToMinutes(config.workEndTime);
      if (signOutMin < endMin - (config.earlyThreshold || 0)) {
        earlyMinutes = endMin - signOutMin;
      }
    }

    return { lateMinutes, earlyMinutes };
  },

  _isWorkDay(schedulesData, holidaysData, dateStr) {
    const fullDate = dateStr;

    const holiday = holidaysData.find(h => h.date === fullDate);
    if (holiday) {
      if (holiday.isWorkday) return true;
      if (holiday.isHoliday) return false;
    }

    if (!schedulesData) return true;

    const parts = dateStr.split('-');
    const day = String(parseInt(parts[2])).padStart(2, '0');
    return schedulesData.workDays[day] === true;
  },

  async calculateMonth(targetMonth) {
    const config = await this.getConfig();
    const holidaysData = await this.getHolidays();

    const [yearStr, monthStr] = targetMonth.split('-');
    const targetYear = parseInt(yearStr);
    const targetMonthNum = parseInt(monthStr);

    const startDate = `${targetMonth}-01`;
    const lastDay = new Date(targetYear, targetMonthNum, 0).getDate();
    const endDate = `${targetMonth}-${String(lastDay).padStart(2, '0')}`;

    const punchRecords = await Store.getByRange('punch_records', 'date', startDate, endDate);
    const allLeaveRecords = await Store.getAll('leave_records');
    const leaveRecords = allLeaveRecords.filter(l => l.endDate >= startDate && l.startDate <= endDate);
    const allTravelRecords = await Store.getAll('travel_records');
    const travelRecords = allTravelRecords.filter(t => t.endDate >= startDate && t.startDate <= endDate);
    const missPunchRecords = await Store.getByRange('miss_punch_records', 'missDate', startDate, endDate);
    const allOvertimeRecords = await Store.getAll('overtime_records');
    const overtimeRecords = allOvertimeRecords.filter(o => {
      const dateStr = (o.startTime || '').substring(0, 10);
      return dateStr >= startDate && dateStr <= endDate;
    });

    const punchByEmployee = {};
    for (const p of punchRecords) {
      if (!p.employeeNo) continue;
      if (!punchByEmployee[p.employeeNo]) punchByEmployee[p.employeeNo] = [];
      punchByEmployee[p.employeeNo].push(p);
    }

    const results = [];

    for (const [employeeNo, punches] of Object.entries(punchByEmployee)) {
      const scheduleEntry = await DB.schedules
        .where('[employeeNo+year+month]')
        .equals([employeeNo, targetYear, targetMonthNum])
        .first();

      let schedulesData = scheduleEntry || null;

      if (!schedulesData) {
        const allSchedules = await Store.getByIndex('schedules', 'year', targetYear);
        schedulesData = allSchedules.find(s => s.month === targetMonthNum) || null;
      }
      const lateRecords = [];

      const employeeName = punches[0].name;
      const department = punches[0].department;

      const punchByDate = {};
      for (const p of punches) {
        if (!punchByDate[p.date]) punchByDate[p.date] = [];
        punchByDate[p.date].push(p);
      }

      for (let d = 1; d <= lastDay; d++) {
        const dateStr = `${targetMonth}-${String(d).padStart(2, '0')}`;
        const isWorkDay = this._isWorkDay(schedulesData, holidaysData, dateStr);

        const dayPunches = punchByDate[dateStr] || [];

        let firstSignIn = null;
        let lastSignOut = null;
        let totalOvertime = 0;
        let totalLate = 0;
        let totalEarly = 0;

        for (const p of dayPunches) {
          if (p.signIn && (!firstSignIn || p.signIn < firstSignIn)) firstSignIn = p.signIn;
          if (p.signOut && (!lastSignOut || p.signOut > lastSignOut)) lastSignOut = p.signOut;
          if (isWorkDay) totalOvertime += p.overtimeHours || 0;
          const dev = this._calcDeviation(p.signIn, p.signOut, config);
          totalLate += dev.lateMinutes;
          totalEarly += dev.earlyMinutes;
        }

        const hasRealPunch = !!firstSignIn || !!lastSignOut;

        let status = 'normal';
        let absent = false;
        let adjustedLateMinutes = totalLate;
        let adjustedEarlyMinutes = totalEarly;
        let adjustedOvertime = totalOvertime;
        let leaveType = '';
        let leaveHours = 0;
        let travelHours = 0;
        let isRestDay = false;

        const dayMissRecords = missPunchRecords.filter(m =>
          (m.missDate === dateStr) &&
          (this._trimName(m.applicant) === this._trimName(employeeName) ||
           this._trimName(m.missPerson) === this._trimName(employeeName))
        );
        const missRecord = dayMissRecords[0] || null;

        const dayLeaveRecords = this._matchOA(leaveRecords, employeeName, dateStr, 'startDate', 'endDate');
        const leaveRecord = dayLeaveRecords[0] || null;

        const dayTravelRecords = this._matchOA(travelRecords, employeeName, dateStr, 'startDate', 'endDate');
        const travelRecord = dayTravelRecords[0] || null;

        const dayOvertimeRecords = overtimeRecords.filter(o => {
          const oDate = (o.startTime || '').substring(0, 10);
          return this._trimName(o.applicant) === this._trimName(employeeName) && oDate === dateStr;
        });
        const overtimeRecord = dayOvertimeRecords[0] || null;

        if (!isWorkDay) {
          isRestDay = true;
          if (hasRealPunch) {
            if (dayOvertimeRecords.length > 0) {
              status = 'overtime';
            } else {
              status = 'suspect_ot';
            }
          } else {
            status = 'rest';
          }
        }

        // Sum all overtime hours from matching records
        for (const o of dayOvertimeRecords) {
          adjustedOvertime += o.overtimeHours || 0;
        }

        if (leaveRecord) {
          leaveType = leaveRecord.leaveType;
          for (const l of dayLeaveRecords) {
            leaveHours += l.leaveHours || (l.leaveDays * 8) || 0;
            if (l.leaveType && l.leaveType.includes('调休')) {
              adjustedOvertime -= l.leaveHours || 0;
            }
          }
          if (!hasRealPunch || leaveRecord.leaveDays >= 1) {
            status = 'leave';
          }
        }

        if (travelRecord) {
          travelHours = 8;
          if (!hasRealPunch) status = 'travel';
        }

        if (missRecord) {
          status = 'normal';
        }

        if (isWorkDay && !hasRealPunch && !leaveRecord && !travelRecord && !missRecord) {
          status = 'absent';
          absent = true;
        }

        if (totalLate > 0 && hasRealPunch && status !== 'leave' && status !== 'travel') {
          lateRecords.push({ date: dateStr, minutes: totalLate });
          status = 'abnormal';
        }

        results.push({
          employeeNo,
          name: employeeName,
          department,
          date: dateStr,
          period: dayPunches[0] ? dayPunches[0].period : '',
          scheduleStart: config.workStartTime,
          scheduleEnd: config.workEndTime,
          signIn: firstSignIn || '',
          signOut: lastSignOut || '',
          lateMinutes: adjustedLateMinutes,
          earlyMinutes: adjustedEarlyMinutes,
          overtimeHours: adjustedOvertime,
          travelHours,
          leaveHours,
          absent,
          status,
          leaveType,
          isRestDay,
          month: targetMonth,
          sourcePunchIds: dayPunches.map(p => p.id).filter(Boolean),
          sourceLeaveIds: dayLeaveRecords.map(l => l.id).filter(Boolean),
          sourceTravelIds: dayTravelRecords.map(t => t.id).filter(Boolean),
          sourceMissIds: dayMissRecords.map(m => m.id).filter(Boolean),
          sourceOvertimeIds: dayOvertimeRecords.map(o => o.id).filter(Boolean)
        });
      }

      const totalLateMinutes = lateRecords.reduce((sum, r) => sum + r.minutes, 0);
      if (lateRecords.length <= config.graceTimes && totalLateMinutes <= config.graceMinutes) {
        for (const r of results.filter(r => r.employeeNo === employeeNo)) {
          r.lateMinutes = 0;
          if (r.status === 'abnormal') r.status = 'normal';
        }
      }

      let monthTotalOvertime = 0;
      const empResults = results.filter(r => r.employeeNo === employeeNo);
      for (const r of empResults) {
        const dayPs = punchByDate[r.date] || [];
        for (const p of dayPs) {
          monthTotalOvertime += p.overtimeHours || 0;
        }
      }

      await this._updateCarryOver(employeeNo, employeeName, targetMonth, monthTotalOvertime, leaveRecords);
    }

    await Store.clearTable('attendance_results');
    await Store.bulkPut('attendance_results', results);

    return results;
  },

  async _updateCarryOver(employeeNo, name, targetMonth, monthOvertime, leaveRecords) {
    const adjustmentHours = leaveRecords
      .filter(l => l.leaveType && l.leaveType.includes('调休'))
      .reduce((sum, l) => sum + (l.leaveHours || 0), 0);

    const [yearStr, monthStr] = targetMonth.split('-');
    let prevYear = parseInt(yearStr);
    let prevMonth = parseInt(monthStr) - 2;
    if (prevMonth <= 0) {
      prevMonth += 12;
      prevYear -= 1;
    }
    const prevMonthKey = `${prevYear}-${String(prevMonth).padStart(2, '0')}`;

    const prevCarry = await DB.carry_over
      .where('[employeeNo+month]')
      .equals([employeeNo, prevMonthKey])
      .first();

    const prevBalance = prevCarry ? prevCarry.overtimeBalance : 0;
    const newBalance = prevBalance + monthOvertime - adjustmentHours;

    await DB.carry_over.put({
      employeeNo,
      name,
      month: targetMonth,
      overtimeBalance: Math.max(0, newBalance)
    });
  },

  async getMonthResults(targetMonth) {
    return Store.getByIndex('attendance_results', 'month', targetMonth);
  },

  async getResultDetail(employeeNo, date) {
    const result = await DB.attendance_results
      .where('[employeeNo+date]')
      .equals([employeeNo, date])
      .first();

    if (!result) return null;

    const detail = { ...result, sourcePunches: [], sourceLeaves: [], sourceTravels: [], sourceMisses: [], sourceOvertimes: [] };

    for (const id of (result.sourcePunchIds || [])) {
      const rec = await Store.getByKey('punch_records', id);
      if (rec) detail.sourcePunches.push(rec);
    }
    for (const id of (result.sourceLeaveIds || [])) {
      const rec = await Store.getByKey('leave_records', id);
      if (rec) detail.sourceLeaves.push(rec);
    }
    for (const id of (result.sourceTravelIds || [])) {
      const rec = await Store.getByKey('travel_records', id);
      if (rec) detail.sourceTravels.push(rec);
    }
    for (const id of (result.sourceMissIds || [])) {
      const rec = await Store.getByKey('miss_punch_records', id);
      if (rec) detail.sourceMisses.push(rec);
    }
    for (const id of (result.sourceOvertimeIds || [])) {
      const rec = await Store.getByKey('overtime_records', id);
      if (rec) detail.sourceOvertimes.push(rec);
    }

    return detail;
  }
};
