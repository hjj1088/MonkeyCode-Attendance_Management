// shared/db.js
// IndexedDB 数据库 Schema 与 CRUD 操作 (基于 Dexie.js)

let DB;

function createDB() {
  DB = new Dexie('AttendanceDB');

  DB.version(1).stores({
    raw_files:        '++id, fileType, importTime',
    punch_records:    '++id, employeeNo, name, date, department',
    leave_records:    '++id, applicant, startDate, endDate',
    overtime_records: '++id, applicant',
    travel_records:   '++id, applicant',
    miss_punch_records: '++id, applicant, missDate',
    schedules:        '++id, [employeeNo+year+month], year, month',
    attendance_results: '[employeeNo+date], employeeNo, date, month, department, status',
    carry_over:       '[employeeNo+month], employeeNo, month',
    holidays:         '++id, date',
    settings:         'key',
    export_templates: '++id, isDefault',
    employees:        'employeeNo, name, department'
  });

  DB.version(2).stores({
    travel_records: '++id, applicant, startDate'
  }).upgrade(async tx => {
    try { await tx.table('travel_records').clear(); } catch (e) {}
  });
}

createDB();

// --- 通用 CRUD 工具 ---

const Store = {
  _clean(value) {
    return JSON.parse(JSON.stringify(value));
  },

  async bulkPut(tableName, records) {
    if (!records || records.length === 0) return 0;
    return DB[tableName].bulkPut(this._clean(records));
  },

  async clearTable(tableName) {
    return DB[tableName].clear();
  },

  async getAll(tableName) {
    return DB[tableName].toArray();
  },

  async getByIndex(tableName, indexName, value) {
    return DB[tableName].where(indexName).equals(value).toArray();
  },

  async getByRange(tableName, indexName, lower, upper) {
    return DB[tableName].where(indexName).between(lower, upper, true, true).toArray();
  },

  async getByKey(tableName, key) {
    return DB[tableName].get(key);
  },

  async put(tableName, record) {
    return DB[tableName].put(this._clean(record));
  },

  async deleteByKey(tableName, key) {
    return DB[tableName].delete(key);
  },

  async resetAllData() {
    const tableNames = [
      'raw_files', 'punch_records', 'leave_records', 'overtime_records',
      'travel_records', 'miss_punch_records', 'schedules',
      'attendance_results', 'carry_over', 'holidays', 'settings',
      'export_templates', 'employees'
    ];
    for (const t of tableNames) {
      await DB[t].clear();
    }
    await initDefaultSettings();
  }
};

// --- 初始化默认设置 ---

async function initDefaultSettings() {
  const existing = await Store.getByKey('settings', 'attendance_config');
  if (!existing) {
    await Store.put('settings', {
      key: 'attendance_config',
      value: {
        workStartTime: '08:30',
        workEndTime: '17:30',
        lateThreshold: 0,
        earlyThreshold: 0,
        graceTimes: 2,
        graceMinutes: 30
      }
    });
  }

  const defaultTemplate = await DB.export_templates.where('isDefault').equals(1).first();
  if (!defaultTemplate) {
    await DB.export_templates.put({
      name: '默认模板',
      isDefault: 1,
      fields: [
        { label: '序号', field: '_index' },
        { label: '考勤号码', field: 'employeeNo' },
        { label: '姓名', field: 'name' },
        { label: '部门', field: 'department' },
        { label: '日期', field: 'date' },
        { label: '对应时段', field: 'period' },
        { label: '上班时间', field: 'scheduleStart' },
        { label: '下班时间', field: 'scheduleEnd' },
        { label: '签到时间', field: 'signIn' },
        { label: '签退时间', field: 'signOut' },
        { label: '迟到时间', field: 'lateMinutes' },
        { label: '早退时间', field: 'earlyMinutes' },
        { label: '加班时间', field: 'overtimeHours' },
        { label: '出差时间', field: 'travelHours' },
        { label: '是否旷工', field: 'absent' }
      ]
    });
  }
}

function startDB() {
  return DB.open().then(() => initDefaultSettings()).catch(async err => {
    console.warn('DB open failed, recreating:', err.message);
    await Dexie.delete('AttendanceDB');
    createDB();
    await DB.open();
    return initDefaultSettings();
  });
}

startDB();
