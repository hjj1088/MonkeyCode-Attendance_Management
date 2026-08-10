// shared/init.js — 兼容桥接层 V3.1 (Store API backend)
// DB (Dexie) is no longer used; replaced by Store REST API

window.AttendanceDB = {
  punches: {
    toArray: () => Store.getAll('punch_records'),
    bulkPut: (records) => Store.bulkPut('punch_records', records),
    clear: () => Store.clearTable('punch_records'),
  },
  leaves: {
    toArray: () => Store.getAll('leave_records'),
  },
};

window.AttendanceRules = {
  async get() {
    const entry = await Store.getByKey('settings', 'attendance_config');
    return entry ? entry.value : {
      workStartTime: '08:30', workEndTime: '17:30',
      lateThreshold: 0, earlyThreshold: 0,
      graceTimes: 2, graceMinutes: 30,
      work_hours: 8, lunch_start: '12:00', lunch_end: '13:00',
      work_days: [1,2,3,4,5], single_punch_threshold: 4
    };
  },
  async save(settings) {
    await Store.put('settings', {key: 'attendance_config', value: settings});
  }
};

window.AttendanceMatcher = {
  match(punches, employees, settings, holidays, leaveRecords, startDate, endDate) {
    const result = [];
    const empMap = {};
    for (const e of employees) {
      empMap[e.employeeNo || e.id] = e;
    }
    const holidaySet = new Set(holidays.map(h => h.date));
    const leaveMap = {};
    for (const l of leaveRecords) {
      const key = l.employee_id || l.employeeNo;
      if (!leaveMap[key]) leaveMap[key] = [];
      leaveMap[key].push(l);
    }

    const groupByEmpDate = {};
    for (const p of punches) {
      if (!p.employeeNo && !p.employee_id) continue;
      const eid = p.employeeNo || p.employee_id;
      const key = eid + '|' + p.date;
      if (!groupByEmpDate[key]) groupByEmpDate[key] = { employee_id: eid, date: p.date, signIns: [], signOuts: [] };
      if (p.sign_in) groupByEmpDate[key].signIns.push(p.sign_in);
      if (p.sign_out) groupByEmpDate[key].signOuts.push(p.sign_out);
    }

    for (const key of Object.keys(groupByEmpDate)) {
      const g = groupByEmpDate[key];
      const emp = empMap[g.employee_id] || { name: '', department: '' };
      const isHoliday = holidaySet.has(g.date);
      const dayOfWeek = new Date(g.date).getDay();
      const workDays = (settings.work_days || [1,2,3,4,5]);
      const isWorkDay = workDays.includes(dayOfWeek === 0 ? 7 : dayOfWeek) && !isHoliday;

      const signIn = g.signIns.sort()[0] || '';
      const signOut = g.signOuts.sort().pop() || '';

      let status = 'normal';
      let lateMinutes = 0, earlyMinutes = 0;

      if (!signIn && !signOut) {
        if (!isWorkDay) { status = 'rest'; }
        else {
          const eid = g.employee_id;
          const dayLeaves = leaveMap[eid] ? leaveMap[eid].filter(l => l.start_date <= g.date && l.end_date >= g.date) : [];
          if (dayLeaves.length) { status = 'leave'; }
          else { status = 'miss'; }
        }
      } else if (!signIn && signOut) {
        status = 'absent';
      } else if (signIn && !signOut) {
        status = 'absent';
      } else if (isWorkDay) {
        const workStart = settings.workStartTime || settings.work_start || '08:30';
        const workEnd = settings.workEndTime || settings.work_end || '17:30';
        const lateGrace = settings.lateGrace || settings.late_grace || 0;
        const earlyGrace = settings.earlyGrace || settings.early_grace || 0;

        const [sh, sm] = workStart.split(':').map(Number);
        const startMin = sh * 60 + sm;
        const [eh, em] = workEnd.split(':').map(Number);
        const endMin = eh * 60 + em;

        const [ish, ism] = signIn.split(':').map(Number);
        const signInMin = ish * 60 + ism;
        const [osh, osm] = signOut.split(':').map(Number);
        const signOutMin = osh * 60 + osm;

        if (signInMin > startMin + lateGrace) lateMinutes = signInMin - startMin;
        if (signOutMin < endMin - earlyGrace) earlyMinutes = endMin - signOutMin;

        if (lateMinutes > 0) status = 'late';
        if (earlyMinutes > 0 && status === 'normal') status = 'early';
        if (lateMinutes > 0 && earlyMinutes > 0) status = 'abnormal';
      }

      const workHours = settings.workHours || settings.work_hours || 8;
      let hours = 0;
      if (signIn && signOut) {
        const [ish, ism] = signIn.split(':').map(Number);
        const [osh, osm] = signOut.split(':').map(Number);
        hours = ((osh * 60 + osm) - (ish * 60 + ism)) / 60;
      }

      result.push({
        employee_id: g.employee_id,
        name: emp.name || '',
        department: emp.department || '',
        date: g.date,
        signIn, signOut,
        status,
        lateMinutes, earlyMinutes,
        overtimeHours: Math.max(0, hours - workHours),
        workHours: Math.round(hours * 100) / 100,
        leaveType: status === 'leave' ? '请假' : '',
      });
    }

    return result.sort((a, b) => a.date.localeCompare(b.date) || a.name.localeCompare(b.name));
  }
};
