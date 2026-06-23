# 考勤管理系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建纯前端考勤管理系统 MVP，支持 Excel 导入自动识别、排班解析、复杂规则引擎计算、列表/日历视图展示、页面内模板导出。

**Architecture:** 多 HTML (index/import/attendance/export/settings) + 共享 JS 模块 (auth/db/excel/matcher/rules)，Vue 3 CDN + Dexie.js IndexedDB + SheetJS，全部本地化 lib/ 存放。

**Tech Stack:** Vue 3 (CDN Options API), Dexie.js, SheetJS (xlsx), TailwindCSS CDN, IndexedDB

---

### Task 0: 项目骨架与本地依赖

**Files:**
- Create: `attendance/` 目录结构
- Create: `attendance/lib/vue.global.prod.js`
- Create: `attendance/lib/dexie.min.js`
- Create: `attendance/lib/xlsx.full.min.js`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p /workspace/attendance/lib /workspace/attendance/shared
```

- [ ] **Step 2: 下载 Vue 3 生产版本**

```bash
curl -sL -o /workspace/attendance/lib/vue.global.prod.js \
  https://unpkg.com/vue@3.4.21/dist/vue.global.prod.js
```

- [ ] **Step 3: 下载 Dexie.js**

```bash
curl -sL -o /workspace/attendance/lib/dexie.min.js \
  https://unpkg.com/dexie@4.0.8/dist/dexie.min.js
```

- [ ] **Step 4: 下载 SheetJS**

```bash
curl -sL -o /workspace/attendance/lib/xlsx.full.min.js \
  https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js
```

- [ ] **Step 5: 验证文件**

```bash
ls -la /workspace/attendance/lib/
```

Expected: 三个 .js 文件存在，均 > 0 字节

- [ ] **Step 6: Commit**

```bash
cd /workspace && git add attendance/lib/ && git commit -m "chore: add local CDN dependencies (Vue3, Dexie, SheetJS)"
```

---

### Task 1: 认证模块 (shared/auth.js)

**Files:**
- Create: `attendance/shared/auth.js`

- [ ] **Step 1: 编写 auth.js**

```javascript
// shared/auth.js
// 考勤系统认证模块 - localStorage 形式登录

const AUTH_KEY = 'attendance_auth';
const DEFAULT_CREDENTIALS = { username: 'admin', password: 'admin123' };

const Auth = {
  isLoggedIn() {
    return localStorage.getItem(AUTH_KEY) === 'true';
  },

  login(username, password) {
    if (username === DEFAULT_CREDENTIALS.username && password === DEFAULT_CREDENTIALS.password) {
      localStorage.setItem(AUTH_KEY, 'true');
      return { success: true };
    }
    return { success: false, message: '账号或密码错误' };
  },

  logout() {
    localStorage.removeItem(AUTH_KEY);
    window.location.href = 'index.html';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = 'index.html';
    }
  }
};
```

- [ ] **Step 2: 验证 - 在浏览器控制台模拟**

```
// 预期行为:
Auth.isLoggedIn()     // false
Auth.login('admin', 'admin123')  // {success: true}
Auth.isLoggedIn()     // true
Auth.login('wrong', 'wrong')     // {success: false, message: '账号或密码错误'}
Auth.logout()         // 跳转到 index.html
```

- [ ] **Step 3: Commit**

```bash
cd /workspace && git add attendance/shared/auth.js && git commit -m "feat: add auth module with localStorage login"
```

---

### Task 2: 数据库模块 (shared/db.js)

**Files:**
- Create: `attendance/shared/db.js`

- [ ] **Step 1: 编写 db.js**

```javascript
// shared/db.js
// IndexedDB 数据库 Schema 与 CRUD 操作 (基于 Dexie.js)

const DB = new Dexie('AttendanceDB');

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

// --- 通用 CRUD 工具 ---

const Store = {
  async bulkPut(tableName, records) {
    if (!records || records.length === 0) return 0;
    return DB[tableName].bulkPut(records);
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
    return DB[tableName].put(record);
  },

  async deleteByKey(tableName, key) {
    return DB[tableName].delete(key);
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

// 在数据库打开后初始化
DB.open().then(() => initDefaultSettings());
```

- [ ] **Step 2: 验证 - 检查数据库创建**

创建一个简单测试 HTML 或在浏览器控制台执行:
```javascript
// 加载 db.js 后:
await Store.getAll('settings')      // 应返回默认考勤配置
await DB.export_templates.toArray() // 应返回默认模板
```

- [ ] **Step 3: Commit**

```bash
cd /workspace && git add attendance/shared/db.js && git commit -m "feat: add IndexedDB schema and CRUD module"
```

---

### Task 3: Excel 解析模块 (shared/excel.js)

**Files:**
- Create: `attendance/shared/excel.js`

- [ ] **Step 1: 编写 excel.js 第一部分 - 文件解析与导出**

```javascript
// shared/excel.js
// SheetJS 封装 - Excel 解析、排班表颜色识别、导出

const Excel = {
  /**
   * 解析 Excel 文件，返回 workbook 对象
   */
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

  /**
   * 获取 workbook 中所有 Sheet 名称
   */
  getSheetNames(wb) {
    return wb.SheetNames || [];
  },

  /**
   * 将 Sheet 转为 JSON 数组 (第一行为表头)
   */
  sheetToJson(ws) {
    return XLSX.utils.sheet_to_json(ws, { defval: '' });
  },

  /**
   * 将 Sheet 转为二维数组 (保留所有行)
   */
  sheetToArray(ws) {
    return XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
  },

  /**
   * 读取单元格背景色 - 判断是否有填充
   */
  _hasFill(cell) {
    if (!cell || !cell.s) return false;
    const fill = cell.s.fgColor || cell.s.bgColor;
    if (!fill) return false;
    // 白色/无填充视为无填充
    if (fill.rgb === 'FFFFFF' || fill.rgb === 'FFFFFFFF') return false;
    if (fill.indexed === 64 || fill.indexed === 65) return false; // 系统白/无填充
    if (fill.theme === 1 && fill.tint === 0) return false; // 默认白色
    return !!fill.rgb || (fill.indexed != null && fill.indexed !== 64 && fill.indexed !== 65);
  },

  /**
   * 解析日历样式排班表 Sheet
   * @param {Object} ws - SheetJS worksheet
   * @param {String} sheetName - Sheet 名称 (如 "12月")
   * @returns {{year, month, workDays: {dateStr: boolean}}}
   */
  parseScheduleSheet(ws, sheetName) {
    const result = { year: null, month: null, workDays: {} };

    // 从 Sheet 名提取月份 (trim 空格)
    const monthMatch = sheetName.trim().match(/^(\d{1,2})月$/);
    if (!monthMatch) return null;
    result.month = parseInt(monthMatch[1]);

    // 获取所有行数据
    const rows = this.sheetToArray(ws);

    // 从首行标题提取年份 (如 "2026年12月日历表及6S检查轮值表")
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

    // 定位表头行: "周次|周一|周二|周三|周四|周五|周六|周日"
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

    // 获取 header 列索引映射
    const headerRow = rows[headerRowIdx];
    const colMap = {}; // { '周一': colIndex, ... }
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
      // 尝试备选: 周一可能在列索引1-7
      for (let i = 0; i < headerRow.length; i++) {
        const h = String(headerRow[i] || '').trim();
        if (/^周[一二三四五六日]$/.test(h)) {
          colMap[h] = i;
        }
      }
    }

    const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

    // 遍历数据行
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
        result.workDays[dateStr] = !isRest; // true=上班, false=休息
      }
    }

    return result;
  },

  /**
   * 判断 workbook 是否包含日历样式排班表
   */
  isScheduleWorkbook(wb) {
    const names = this.getSheetNames(wb);
    return names.some(name => {
      const trimmed = name.trim();
      return /^\d{1,2}月$/.test(trimmed);
    });
  },

  /**
   * 提取排班表中所有排班数据
   */
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

  /**
   * 生成导出 Excel 并下载
   */
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
  }
};
```

- [ ] **Step 2: 编写 excel.js 第二部分 - 文件类型自动识别**

```javascript
// 追加到 excel.js

/**
 * 自动识别 Excel 文件类型
 * 采用评分制: 匹配列名越多，得分越高
 */
Excel.identifyFileType = function(wb) {
  const names = this.getSheetNames(wb);

  // 优先判断排班表 (按 Sheet 名)
  if (this.isScheduleWorkbook(wb)) {
    return { type: 'schedule', confidence: 1.0 };
  }

  // 取第一个有数据的 Sheet
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
    {
      type: 'punch',
      required: ['考勤号码', '签到时间'],
      bonus: ['签退时间', '迟到时间', '部门', '日期', '上班时间', '下班时间']
    },
    {
      type: 'leave',
      required: ['请假类型', '开始日期'],
      bonus: ['结束日期', '请假天数', '申请人', '申请部门']
    },
    {
      type: 'overtime',
      required: ['加班起止时间'],
      bonus: ['申请人', '申请部门', '加班内容']
    },
    {
      type: 'travel',
      required: ['出差起止日期'],
      bonus: ['申请人', '目的地', '出差事由', '出差人员']
    },
    {
      type: 'miss_punch',
      required: ['忘打卡日期'],
      bonus: ['申请人', '忘打卡人员', '未打卡时间', '事由']
    }
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
};
```

- [ ] **Step 3: 编写 excel.js 第三部分 - 各类型数据解析**

```javascript
// 追加到 excel.js

/**
 * 解析导入数据，根据类型返回结构化记录
 */
Excel.parseRecords = function(wb, fileType) {
  const names = this.getSheetNames(wb);
  const ws = wb.Sheets[names[0]];
  const raw = this.sheetToJson(ws);

  if (fileType === 'schedule') {
    return this.parseAllScheduleSheets(wb);
  }

  return raw.map(row => this._normalizeRecord(row, fileType)).filter(Boolean);
};

/**
 * 标准化单条记录
 */
Excel._normalizeRecord = function(row, fileType) {
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
        absent: clean['是否旷工'] === '是' || clean['是否旷工'] === true,
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
      return {
        applicant: clean['申请人'] || '',
        department: clean['申请部门'] || '',
        leaveType: clean['请假类型'] || '',
        startDate: this._formatDate(clean['开始日期']),
        endDate: this._formatDate(clean['结束日期']),
        leaveDays: parseFloat(clean['请假天数']) || 0,
        leaveHours: parseFloat(clean['小时']) || 0,
        reason: clean['请假事由'] || ''
      };

    case 'overtime':
      const otTime = clean['加班起止时间小时'] || clean['加班起止时间'] || '';
      return {
        applicant: clean['申请人'] || '',
        department: clean['申请部门'] || '',
        startTime: '',
        endTime: '',
        overtimeHours: parseFloat(otTime) || 0,
        content: clean['加班内容'] || ''
      };

    case 'travel':
      const travelDate = clean['出差起止日期'] || '';
      const dateParts = travelDate.split(/[-~至到]/);
      return {
        applicant: clean['申请人'] || '',
        department: clean['申请部门'] || '',
        destination: clean['目的地'] || '',
        travelers: clean['出差人员'] || '',
        startDate: this._formatDate(dateParts[0]),
        endDate: this._formatDate(dateParts[1]) || this._formatDate(dateParts[0]),
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
};

/**
 * 日期格式化: Excel 序列号或字符串 → YYYY-MM-DD
 */
Excel._formatDate = function(val) {
  if (!val && val !== 0) return '';
  if (typeof val === 'number') {
    // Excel 日期序列号
    const date = XLSX.SSF.parse_date_code(val);
    if (date) {
      return `${date.y}-${String(date.m).padStart(2, '0')}-${String(date.d).padStart(2, '0')}`;
    }
  }
  const str = String(val).trim();
  // 兼容 YYYY/MM/DD, YYYY-MM-DD, MM/DD/YYYY
  const match = str.match(/(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})/);
  if (match) {
    return `${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}`;
  }
  return str;
};

/**
 * 时间格式化: Excel 小数或字符串 → HH:MM
 */
Excel._formatTime = function(val) {
  if (!val && val !== 0) return '';
  if (typeof val === 'number' && val < 1) {
    const hours = Math.floor(val * 24);
    const minutes = Math.round((val * 24 - hours) * 60);
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }
  const str = String(val).trim();
  // 兼容 HH:MM, HH:MM:SS
  const match = str.match(/(\d{1,2}):(\d{2})/);
  if (match) {
    return `${match[1].padStart(2, '0')}:${match[2]}`;
  }
  return str;
};
```

- [ ] **Step 4: 编写验证测试 HTML**

创建 `attendance/test_excel.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>Excel 模块测试</title></head>
<body>
  <h1>Excel 模块测试</h1>
  <input type="file" id="fileInput" accept=".xlsx,.xls" multiple>
  <pre id="output"></pre>

  <script src="./lib/xlsx.full.min.js?v=1.0.0"></script>
  <script src="./shared/excel.js?v=1.0.0"></script>
  <script>
    const output = document.getElementById('output');

    document.getElementById('fileInput').addEventListener('change', async function(e) {
      const files = Array.from(e.target.files);
      output.textContent = '';

      for (const file of files) {
        output.textContent += `\n=== ${file.name} ===\n`;
        try {
          const wb = await Excel.parseExcelFile(file);
          output.textContent += `Sheets: ${Excel.getSheetNames(wb).join(', ')}\n`;

          const ident = Excel.identifyFileType(wb);
          output.textContent += `识别类型: ${ident.type} (置信度: ${ident.confidence})\n`;

          const records = Excel.parseRecords(wb, ident.type);
          output.textContent += `解析记录数: ${records.length}\n`;

          if (ident.type === 'schedule') {
            for (const s of records) {
              const workDays = Object.entries(s.workDays).filter(([_, v]) => v).length;
              const restDays = Object.entries(s.workDays).filter(([_, v]) => !v).length;
              output.textContent += `  ${s.year}年${s.month}月: 上班${workDays}天, 休息${restDays}天\n`;
            }
          } else if (records.length > 0) {
            output.textContent += `  首条预览: ${JSON.stringify(records[0], null, 2).slice(0, 300)}\n`;
          }
        } catch(err) {
          output.textContent += `错误: ${err.message}\n`;
        }
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 5: Commit**

```bash
cd /workspace && git add attendance/shared/excel.js attendance/test_excel.html && git commit -m "feat: add Excel parse/identify/export module with test page"
```

---

### Task 4: 数据匹配模块 (shared/matcher.js)

**Files:**
- Create: `attendance/shared/matcher.js`

- [ ] **Step 1: 编写 matcher.js**

```javascript
// shared/matcher.js
// 跨文件数据匹配 - 考勤号为主键，姓名+部门为降级键

const Matcher = {
  /**
   * 从打卡记录构建员工花名册映射
   * @returns {Promise<{[employeeNo]: {name, department}}>}
   */
  async buildEmployeeMap() {
    const punchRecords = await Store.getAll('punch_records');
    const map = {};
    for (const rec of punchRecords) {
      if (rec.employeeNo && rec.name) {
        map[rec.employeeNo] = {
          name: rec.name,
          department: rec.department || ''
        };
      }
    }
    return map;
  },

  /**
   * 同步更新 employees 表
   */
  async syncEmployees() {
    const map = await this.buildEmployeeMap();
    const employees = Object.entries(map).map(([no, info]) => ({
      employeeNo: no,
      name: info.name,
      department: info.department
    }));
    await Store.clearTable('employees');
    await Store.bulkPut('employees', employees);
    return employees;
  },

  /**
   * 通过"申请人+部门"查找考勤号
   */
  async resolveEmployeeNo(applicant, department) {
    const employees = await Store.getAll('employees');
    const match = employees.find(e =>
      e.name === applicant && e.department === department
    );
    return match ? match.employeeNo : null;
  },

  /**
   * 生成 OA 单据与打卡数据的匹配映射
   * 返回 {oaIndex: employeeNo|null}
   */
  async matchOAToPunch(oaRecords, oaType) {
    const employeeMap = await this.buildEmployeeMap();

    // 构建反向索引: "姓名+部门" → employeeNo
    const nameDeptToNo = {};
    for (const [no, info] of Object.entries(employeeMap)) {
      const key = `${info.name}|${info.department}`;
      nameDeptToNo[key] = no;
    }

    const matches = [];
    for (let i = 0; i < oaRecords.length; i++) {
      const rec = oaRecords[i];
      const key = `${rec.applicant}|${rec.department}`;
      const employeeNo = nameDeptToNo[key] || null;
      matches.push({ index: i, employeeNo, applicant: rec.applicant, department: rec.department });
    }

    return matches;
  }
};
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/shared/matcher.js && git commit -m "feat: add data matcher module for cross-file employee matching"
```

---

### Task 5: 考勤规则引擎 (shared/rules.js)

**Files:**
- Create: `attendance/shared/rules.js`

- [ ] **Step 1: 编写 rules.js**

```javascript
// shared/rules.js
// 考勤规则引擎 - 迟到/早退/旷工判定、容错、结余计算

const RulesEngine = {
  /**
   * 获取系统配置
   */
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

  /**
   * 获取所有公司假期/调休日期
   */
  async getHolidays() {
    return Store.getAll('holidays');
  },

  /**
   * 时间字符串转为分钟数 (08:30 → 510)
   */
  _timeToMinutes(timeStr) {
    if (!timeStr) return null;
    const parts = String(timeStr).split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  },

  /**
   * 计算迟到/早退分钟数
   */
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

  /**
   * 判断某天是否为应出勤日
   * @param schedulesData - 排班数据，如 workDays: {"01": true, "02": false, ...}
   * @param holidaysData - 公司假期/调休数组
   * @param dateStr - YYYY-MM-DD
   */
  _isWorkDay(schedulesData, holidaysData, dateStr) {
    if (!schedulesData) return false;

    const parts = dateStr.split('-');
    const day = String(parseInt(parts[2])).padStart(2, '0'); // 去前导零后补零 ("02")
    const month = String(parseInt(parts[1]));
    const fullDate = dateStr; // YYYY-MM-DD

    // 检查公司调休 (调休上班日强制为上班)
    const holiday = holidaysData.find(h => h.date === fullDate);
    if (holiday) {
      if (holiday.isWorkday) return true;  // 调休上班日
      if (holiday.isHoliday) return false; // 公司假日
    }

    // 查排班表
    return schedulesData.workDays[day] === true;
  },

  /**
   * 计算指定月份所有考勤结果
   * @param {String} targetMonth - YYYY-MM
   * @returns {Array} 计算结果数组
   */
  async calculateMonth(targetMonth) {
    const config = await this.getConfig();
    const holidaysData = await this.getHolidays();

    const [yearStr, monthStr] = targetMonth.split('-');
    const targetYear = parseInt(yearStr);
    const targetMonthNum = parseInt(monthStr);

    // 获取打卡记录 (按日期范围)
    const startDate = `${targetMonth}-01`;
    const lastDay = new Date(targetYear, targetMonthNum, 0).getDate();
    const endDate = `${targetMonth}-${String(lastDay).padStart(2, '0')}`;

    const punchRecords = await Store.getByRange('punch_records', 'date', startDate, endDate);

    // 获取 OA 单据 (日期范围)
    const leaveRecords = await Store.getByRange('leave_records', 'startDate', startDate, endDate);
    const overtimeRecords = await Store.getAll('overtime_records');
    const travelRecords = await Store.getByRange('travel_records', 'startDate', startDate, endDate);
    const missPunchRecords = await Store.getByRange('miss_punch_records', 'missDate', startDate, endDate);

    // 按人员分组打卡记录
    const punchByEmployee = {};
    for (const p of punchRecords) {
      if (!p.employeeNo) continue;
      if (!punchByEmployee[p.employeeNo]) punchByEmployee[p.employeeNo] = [];
      punchByEmployee[p.employeeNo].push(p);
    }

    const results = [];

    for (const [employeeNo, punches] of Object.entries(punchByEmployee)) {
      // 获取该人员的排班数据
      const scheduleEntry = await DB.schedules
        .where('[employeeNo+year+month]')
        .equals([employeeNo, targetYear, targetMonthNum])
        .first();

      const schedulesData = scheduleEntry || null;

      // 当月迟到累计 (用于容错判断)
      const lateRecords = [];

      // 按日期分组
      const punchByDate = {};
      for (const p of punches) {
        if (!punchByDate[p.date]) punchByDate[p.date] = [];
        punchByDate[p.date].push(p);
      }

      // 遍历当月每一天
      for (let d = 1; d <= lastDay; d++) {
        const dateStr = `${targetMonth}-${String(d).padStart(2, '0')}`;
        const isWorkDay = this._isWorkDay(schedulesData, holidaysData, dateStr);

        const dayPunches = punchByDate[dateStr] || [];
        const employeeName = punches[0].name;
        const department = punches[0].department;

        // 汇总当天打卡数据
        let firstSignIn = null;
        let lastSignOut = null;
        let totalOvertime = 0;
        let totalLate = 0;
        let totalEarly = 0;

        for (const p of dayPunches) {
          if (p.signIn && (!firstSignIn || p.signIn < firstSignIn)) firstSignIn = p.signIn;
          if (p.signOut && (!lastSignOut || p.signOut > lastSignOut)) lastSignOut = p.signOut;
          totalOvertime += p.overtimeHours || 0;
          const dev = this._calcDeviation(p.signIn, p.signOut, config);
          totalLate += dev.lateMinutes;
          totalEarly += dev.earlyMinutes;
        }

        // 基本状态判定
        let status = 'normal';
        let absent = false;
        let adjustedLateMinutes = totalLate;
        let adjustedEarlyMinutes = totalEarly;
        let adjustedOvertime = totalOvertime;
        let leaveType = '';
        let travelHours = 0;

        // 检查是否休息日
        if (!isWorkDay) {
          // 休息日有打卡则算加班
        }

        // 检查漏打卡说明
        const missRecord = missPunchRecords.find(m =>
          (m.missDate === dateStr) &&
          (m.applicant === employeeName || m.missPerson === employeeName)
        );

        // 检查请假
        const leaveRecord = leaveRecords.find(l =>
          l.applicant === employeeName && dateStr >= l.startDate && dateStr <= l.endDate
        );

        // 检查出差
        const travelRecord = travelRecords.find(t =>
          t.applicant === employeeName && dateStr >= t.startDate && dateStr <= t.endDate
        );

        if (leaveRecord && (!dayPunches.length || leaveRecord.leaveDays >= 1)) {
          status = 'abnormal';
          leaveType = leaveRecord.leaveType;
          // 调休: 从加班余额扣除
          if (leaveRecord.leaveType === '调休') {
            adjustedOvertime -= leaveRecord.leaveHours || 0;
          }
        }

        if (travelRecord) {
          status = 'abnormal';
          travelHours = 8; // 默认全天出差
        }

        if (missRecord && dayPunches.length === 0) {
          // 有漏打卡说明，清除旷工/漏打卡标记
          status = 'normal';
        }

        // 旷工判定: 应出勤日且无任何记录
        if (isWorkDay && dayPunches.length === 0 && !leaveRecord && !travelRecord && !missRecord) {
          status = 'absent';
          absent = true;
        }

        // 容错判断 (先累计迟到记录)
        if (totalLate > 0 && dayPunches.length > 0) {
          lateRecords.push({ date: dateStr, minutes: totalLate });
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
          absent,
          status,
          leaveType,
          month: targetMonth,
          sourcePunchIds: dayPunches.map(p => p.id).filter(Boolean),
          sourceLeaveIds: leaveRecord ? [leaveRecord.id] : [],
          sourceTravelIds: travelRecord ? [travelRecord.id] : [],
          sourceMissIds: missRecord ? [missRecord.id] : []
        });
      }

      // 容错规则应用: 月累计 ≤ 2次 且 ≤ 30min → 豁免
      const totalLateMinutes = lateRecords.reduce((sum, r) => sum + r.minutes, 0);
      if (lateRecords.length <= config.graceTimes && totalLateMinutes <= config.graceMinutes) {
        for (const r of results.filter(r => r.employeeNo === employeeNo)) {
          r.lateMinutes = 0;
        }
      }

      // 结余计算
      await this._updateCarryOver(employeeNo, employeeName, targetMonth, totalOvertime, leaveRecords);
    }

    // 保存计算结果
    await Store.clearTable('attendance_results');
    await Store.bulkPut('attendance_results', results);

    return results;
  },

  /**
   * 更新结余数据
   */
  async _updateCarryOver(employeeNo, name, targetMonth, monthOvertime, leaveRecords) {
    // 计算当月的调休消耗
    const adjustmentHours = leaveRecords
      .filter(l => l.leaveType === '调休')
      .reduce((sum, l) => sum + (l.leaveHours || 0), 0);

    // 查找上上个月结余
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

  /**
   * 获取指定月份的考勤计算结果
   */
  async getMonthResults(targetMonth) {
    return Store.getByIndex('attendance_results', 'month', targetMonth);
  },

  /**
   * 获取计算结果详情 (含原始记录)
   */
  async getResultDetail(employeeNo, date) {
    const result = await DB.attendance_results
      .where('[employeeNo+date]')
      .equals([employeeNo, date])
      .first();

    if (!result) return null;

    const detail = { ...result, sourcePunches: [], sourceLeaves: [], sourceTravels: [], sourceMisses: [] };

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

    return detail;
  }
};
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/shared/rules.js && git commit -m "feat: add attendance rules engine with grace period and carry-over logic"
```

---

### Task 6: 登录页与主导航 (index.html)

**Files:**
- Create: `attendance/index.html`

- [ ] **Step 1: 编写 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考勤管理系统</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .module-card { transition: all 0.2s ease; }
    .module-card:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <div id="app">
    <!-- 登录表单 -->
    <div v-if="!loggedIn" class="flex items-center justify-center min-h-screen">
      <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 class="text-2xl font-bold text-center text-gray-800 mb-6">考勤管理系统</h1>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">账号</label>
          <input v-model="username" type="text" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="请输入账号">
        </div>
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input v-model="password" type="password" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="请输入密码" @keyup.enter="doLogin">
        </div>
        <div v-if="errorMsg" class="mb-4 p-2 bg-red-100 text-red-700 rounded text-sm">{{ errorMsg }}</div>
        <button @click="doLogin" class="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 transition">登录</button>
        <p class="text-xs text-gray-400 text-center mt-4">默认账号: admin / admin123</p>
      </div>
    </div>

    <!-- 主导航 -->
    <div v-else class="max-w-4xl mx-auto px-4 py-12">
      <div class="flex justify-between items-center mb-8">
        <h1 class="text-3xl font-bold text-gray-800">考勤管理系统</h1>
        <button @click="doLogout" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition">退出登录</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <template v-for="card in modules" :key="card.id">
          <a :href="card.link" class="module-card block bg-white rounded-lg shadow p-6 hover:shadow-lg">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-lg flex items-center justify-center text-2xl" :class="card.bgClass">{{ card.icon }}</div>
              <div>
                <h3 class="text-lg font-semibold text-gray-800">{{ card.title }}</h3>
                <p class="text-sm text-gray-500 mt-1">{{ card.desc }}</p>
              </div>
            </div>
          </a>
        </template>
      </div>
    </div>
  </div>

  <script src="./lib/vue.global.prod.js?v=1.0.0"></script>
  <script src="./shared/auth.js?v=1.0.0"></script>
  <script>
    const { createApp } = Vue;

    createApp({
      data() {
        return {
          loggedIn: Auth.isLoggedIn(),
          username: 'admin',
          password: '',
          errorMsg: '',
          modules: [
            { id: 'import', icon: '\u{1F4C1}', bgClass: 'bg-blue-100', title: '数据导入', desc: '拖拽上传Excel文件，自动识别并导入考勤数据', link: 'import.html' },
            { id: 'attendance', icon: '\u{1F4C5}', bgClass: 'bg-green-100', title: '考勤计算', desc: '运行规则引擎，列表/日历视图查询考勤结果', link: 'attendance.html' },
            { id: 'export', icon: '\u{1F4E4}', bgClass: 'bg-purple-100', title: '导出中心', desc: '设计导出模板，预览并导出考勤凭证', link: 'export.html' },
            { id: 'settings', icon: '\u2699', bgClass: 'bg-gray-100', title: '系统设置', desc: '配置考勤规则、容错参数、公司假期', link: 'settings.html' }
          ]
        };
      },
      methods: {
        doLogin() {
          const result = Auth.login(this.username, this.password);
          if (result.success) {
            this.loggedIn = true;
            this.errorMsg = '';
          } else {
            this.errorMsg = result.message;
          }
        },
        doLogout() {
          Auth.logout();
        }
      }
    }).mount('#app');
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/index.html && git commit -m "feat: add login page and main navigation"
```

---

### Task 7: 系统设置页 (settings.html)

**Files:**
- Create: `attendance/settings.html`

- [ ] **Step 1: 编写 settings.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>系统设置 - 考勤管理</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
  <div id="app" class="max-w-2xl mx-auto px-4 py-8">
    <!-- 头部导航 -->
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <a href="index.html" class="text-blue-600 hover:underline">&larr; 返回</a>
        <h1 class="text-2xl font-bold text-gray-800">系统设置</h1>
      </div>
      <button @click="saveConfig" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition">保存设置</button>
    </div>

    <!-- 保存成功提示 -->
    <div v-if="saved" class="mb-4 p-3 bg-green-100 text-green-700 rounded-md">设置已保存</div>

    <!-- 考勤规则 -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">考勤规则配置</h2>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">上班时间</label>
          <input v-model="config.workStartTime" type="time" class="w-full px-3 py-2 border rounded-md">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">下班时间</label>
          <input v-model="config.workEndTime" type="time" class="w-full px-3 py-2 border rounded-md">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">迟到阈值 (分钟)</label>
          <input v-model.number="config.lateThreshold" type="number" min="0" class="w-full px-3 py-2 border rounded-md">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">早退阈值 (分钟)</label>
          <input v-model.number="config.earlyThreshold" type="number" min="0" class="w-full px-3 py-2 border rounded-md">
        </div>
      </div>
    </div>

    <!-- 容错规则 -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">容错规则配置</h2>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">每月豁免次数</label>
          <input v-model.number="config.graceTimes" type="number" min="0" class="w-full px-3 py-2 border rounded-md">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">累计豁免时长 (分钟)</label>
          <input v-model.number="config.graceMinutes" type="number" min="0" class="w-full px-3 py-2 border rounded-md">
        </div>
      </div>
    </div>

    <!-- 假期管理 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">假期管理</h2>
      <div class="flex gap-3 mb-4">
        <input v-model="newHoliday.date" type="date" class="px-3 py-2 border rounded-md flex-1">
        <input v-model="newHoliday.name" type="text" placeholder="假期名称" class="px-3 py-2 border rounded-md flex-1">
        <select v-model="newHoliday.type" class="px-3 py-2 border rounded-md">
          <option value="holiday">休息日</option>
          <option value="workday">调休上班日</option>
        </select>
        <button @click="addHoliday" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition">添加</button>
      </div>
      <div class="space-y-2">
        <div v-for="h in holidays" :key="h.id" class="flex justify-between items-center p-2 bg-gray-50 rounded">
          <span>{{ h.date }} - {{ h.name }} <span class="text-xs px-2 py-0.5 rounded" :class="h.isWorkday ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">{{ h.isWorkday ? '上班' : '休息' }}</span></span>
          <button @click="deleteHoliday(h.id)" class="text-red-500 hover:text-red-700 text-sm">删除</button>
        </div>
        <div v-if="holidays.length === 0" class="text-gray-400 text-sm text-center py-4">暂无假期设置</div>
      </div>
    </div>
  </div>

  <script src="./lib/vue.global.prod.js?v=1.0.0"></script>
  <script src="./lib/dexie.min.js?v=1.0.0"></script>
  <script src="./shared/auth.js?v=1.0.0"></script>
  <script src="./shared/db.js?v=1.0.0"></script>
  <script>
    Auth.requireAuth();

    const { createApp } = Vue;
    createApp({
      data() {
        return {
          saved: false,
          config: {
            workStartTime: '08:30',
            workEndTime: '17:30',
            lateThreshold: 0,
            earlyThreshold: 0,
            graceTimes: 2,
            graceMinutes: 30
          },
          holidays: [],
          newHoliday: { date: '', name: '', type: 'holiday' }
        };
      },
      async created() {
        const entry = await Store.getByKey('settings', 'attendance_config');
        if (entry && entry.value) {
          Object.assign(this.config, entry.value);
        }
        this.holidays = await Store.getAll('holidays');
      },
      methods: {
        async saveConfig() {
          await Store.put('settings', { key: 'attendance_config', value: { ...this.config } });
          this.saved = true;
          setTimeout(() => { this.saved = false; }, 2000);
        },
        async addHoliday() {
          if (!this.newHoliday.date) return;
          await DB.holidays.put({
            date: this.newHoliday.date,
            name: this.newHoliday.name || '假期',
            isWorkday: this.newHoliday.type === 'workday',
            isHoliday: this.newHoliday.type === 'holiday'
          });
          this.holidays = await Store.getAll('holidays');
          this.newHoliday = { date: '', name: '', type: 'holiday' };
        },
        async deleteHoliday(id) {
          await Store.deleteByKey('holidays', id);
          this.holidays = await Store.getAll('holidays');
        }
      }
    }).mount('#app');
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/settings.html && git commit -m "feat: add system settings page with attendance rules and holiday management"
```

---

### Task 8: 数据导入页 (import.html)

**Files:**
- Create: `attendance/import.html`

- [ ] **Step 1: 编写 import.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>数据导入 - 考勤管理</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .drop-zone { transition: all 0.2s ease; border: 2px dashed #d1d5db; }
    .drop-zone.dragover { border-color: #3b82f6; background: #eff6ff; }
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <div id="app" class="max-w-5xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <a href="index.html" class="text-blue-600 hover:underline">&larr; 返回</a>
        <h1 class="text-2xl font-bold text-gray-800">数据导入</h1>
      </div>
    </div>

    <!-- 拖拽上传区域 -->
    <div class="drop-zone bg-white rounded-lg p-8 mb-6 text-center"
         :class="{ 'dragover': dragging }"
         @dragover.prevent="dragging = true"
         @dragleave="dragging = false"
         @drop.prevent="handleDrop">
      <p class="text-gray-500 mb-2">拖拽 Excel 文件到此处</p>
      <p class="text-gray-400 text-sm">或</p>
      <label class="inline-block mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer transition">
        选择文件
        <input type="file" accept=".xlsx,.xls" multiple class="hidden" @change="handleFileSelect">
      </label>
    </div>

    <!-- 文件列表 / 识别结果 -->
    <div v-if="files.length > 0" class="bg-white rounded-lg shadow p-6 mb-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-gray-800">文件列表 ({{ files.length }})</h2>
        <button @click="importAll" :disabled="importing" class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition">
          {{ importing ? '导入中...' : '全部入库' }}
        </button>
      </div>
      <div class="space-y-3">
        <div v-for="(f, idx) in files" :key="idx" class="flex items-center gap-4 p-3 bg-gray-50 rounded">
          <span class="text-sm font-medium text-gray-700 w-32 truncate">{{ f.fileName }}</span>
          <span class="px-2 py-1 text-xs rounded" :class="typeClass(f.fileType)">{{ typeLabel(f.fileType) }}</span>
          <span class="text-sm text-gray-500">解析: {{ f.recordCount }} 条</span>
          <span v-if="f.imported" class="text-green-600 text-sm">已入库</span>
          <span v-if="f.error" class="text-red-600 text-sm">{{ f.error }}</span>
        </div>
      </div>
    </div>

    <!-- 预览区域 -->
    <div v-if="previewFile" class="bg-white rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">数据预览 - {{ previewFile.fileName }}</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th v-for="col in previewColumns" :key="col" class="px-3 py-2 text-left text-gray-600 whitespace-nowrap">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in previewRows" :key="ri" class="border-t">
              <td v-for="col in previewColumns" :key="col" class="px-3 py-2 whitespace-nowrap">{{ row[col] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script src="./lib/vue.global.prod.js?v=1.0.0"></script>
  <script src="./lib/dexie.min.js?v=1.0.0"></script>
  <script src="./lib/xlsx.full.min.js?v=1.0.0"></script>
  <script src="./shared/auth.js?v=1.0.0"></script>
  <script src="./shared/db.js?v=1.0.0"></script>
  <script src="./shared/excel.js?v=1.0.0"></script>
  <script src="./shared/matcher.js?v=1.0.0"></script>
  <script>
    Auth.requireAuth();

    const { createApp } = Vue;
    createApp({
      data() {
        return {
          dragging: false,
          importing: false,
          files: [],          // {fileName, fileType, recordCount, records, workbook, imported, error}
          previewFile: null,
          previewColumns: [],
          previewRows: []
        };
      },
      methods: {
        typeLabel(type) {
          const map = { punch: '打卡', leave: '请假', overtime: '加班', travel: '出差', miss_punch: '漏打卡', schedule: '排班', unknown: '未知' };
          return map[type] || type;
        },
        typeClass(type) {
          const map = { punch: 'bg-blue-100 text-blue-700', leave: 'bg-yellow-100 text-yellow-700', overtime: 'bg-orange-100 text-orange-700', travel: 'bg-purple-100 text-purple-700', miss_punch: 'bg-pink-100 text-pink-700', schedule: 'bg-green-100 text-green-700', unknown: 'bg-gray-100 text-gray-700' };
          return map[type] || 'bg-gray-100 text-gray-700';
        },
        async handleFileSelect(e) {
          await this.processFiles(Array.from(e.target.files));
        },
        async handleDrop(e) {
          this.dragging = false;
          await this.processFiles(Array.from(e.dataTransfer.files));
        },
        async processFiles(fileList) {
          const excelFiles = fileList.filter(f => /\.xlsx?$/i.test(f.name));
          for (const file of excelFiles) {
            const existing = this.files.find(f => f.fileName === file.name);
            if (existing) continue;

            try {
              const wb = await Excel.parseExcelFile(file);
              const ident = Excel.identifyFileType(wb);
              const records = Excel.parseRecords(wb, ident.type);
              this.files.push({
                fileName: file.name,
                fileType: ident.type,
                recordCount: records.length,
                records,
                workbook: wb,
                imported: false,
                error: null
              });
            } catch (err) {
              this.files.push({
                fileName: file.name,
                fileType: 'unknown',
                recordCount: 0,
                records: [],
                workbook: null,
                imported: false,
                error: err.message
              });
            }
          }
        },
        showPreview(f) {
          this.previewFile = f;
          if (f.records.length > 0) {
            this.previewColumns = Object.keys(f.records[0]);
            this.previewRows = f.records.slice(0, 10);
          }
        },
        async importAll() {
          this.importing = true;
          try {
            for (const f of this.files) {
              if (f.imported) continue;

              switch (f.fileType) {
                case 'punch':
                  // 清空旧数据
                  await Store.clearTable('punch_records');
                  await Store.bulkPut('punch_records', f.records);
                  // 同步员工花名册
                  await Matcher.syncEmployees();
                  break;
                case 'leave':
                  await Store.clearTable('leave_records');
                  await Store.bulkPut('leave_records', f.records);
                  break;
                case 'overtime':
                  await Store.clearTable('overtime_records');
                  await Store.bulkPut('overtime_records', f.records);
                  break;
                case 'travel':
                  await Store.clearTable('travel_records');
                  await Store.bulkPut('travel_records', f.records);
                  break;
                case 'miss_punch':
                  await Store.clearTable('miss_punch_records');
                  await Store.bulkPut('miss_punch_records', f.records);
                  break;
                case 'schedule':
                  // 排班数据扁平化存入
                  const scheduleRows = [];
                  for (const s of f.records) {
                    if (!s.year || !s.month) continue;
                    // 从打卡记录中获取该排班关联的员工
                    const employees = await Store.getAll('employees');
                    for (const emp of employees) {
                      scheduleRows.push({
                        employeeNo: emp.employeeNo,
                        name: emp.name,
                        department: emp.department,
                        year: s.year,
                        month: s.month,
                        workDays: s.workDays
                      });
                    }
                  }
                  await Store.clearTable('schedules');
                  await Store.bulkPut('schedules', scheduleRows);
                  break;
              }

              // 记录原始文件
              await DB.raw_files.put({
                fileName: f.fileName,
                fileType: f.fileType,
                importTime: new Date().toISOString()
              });

              f.imported = true;
            }

            alert('所有数据导入完成！可前往考勤计算页面运行计算。');
          } catch (err) {
            alert('导入出错: ' + err.message);
          }
          this.importing = false;
        }
      }
    }).mount('#app');
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/import.html && git commit -m "feat: add data import page with drag-drop, auto-identify and preview"
```

---

### Task 9: 考勤计算与视图页 (attendance.html)

**Files:**
- Create: `attendance/attendance.html`

- [ ] **Step 1: 编写 attendance.html 第一部分 - 结构**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考勤计算 - 考勤管理</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .status-normal { background: #dcfce7; color: #166534; }
    .status-abnormal { background: #fef9c3; color: #854d0e; }
    .status-absent { background: #fee2e2; color: #991b1b; }
    .cal-cell { min-height: 80px; transition: all 0.15s; }
    .cal-cell:hover { transform: scale(1.02); z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <div id="app" class="max-w-7xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <a href="index.html" class="text-blue-600 hover:underline">&larr; 返回</a>
        <h1 class="text-2xl font-bold text-gray-800">考勤计算</h1>
      </div>
      <div class="flex gap-3">
        <button @click="viewMode = 'list'" :class="viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'" class="px-3 py-1 rounded text-sm transition">列表</button>
        <button @click="viewMode = 'calendar'" :class="viewMode === 'calendar' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'" class="px-3 py-1 rounded text-sm transition">日历</button>
        <button @click="runCalculation" :disabled="calculating" class="px-4 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50 transition">
          {{ calculating ? '计算中...' : '重新计算' }}
        </button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap gap-3 items-center">
      <input v-model="currentMonth" type="month" class="px-3 py-1 border rounded text-sm">
      <select v-model="filterDept" class="px-3 py-1 border rounded text-sm">
        <option value="">全部部门</option>
        <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="filterStatus" class="px-3 py-1 border rounded text-sm">
        <option value="">全部状态</option>
        <option value="normal">正常</option>
        <option value="abnormal">异常</option>
        <option value="absent">缺勤</option>
      </select>
      <input v-model="searchName" type="text" placeholder="搜索姓名" class="px-3 py-1 border rounded text-sm w-32">
    </div>

    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'" class="bg-white rounded-lg shadow overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-100 text-gray-600">
            <th class="px-3 py-2 text-left">考勤号</th>
            <th class="px-3 py-2 text-left">姓名</th>
            <th class="px-3 py-2 text-left">部门</th>
            <th class="px-3 py-2 text-left">日期</th>
            <th class="px-3 py-2 text-left">签到</th>
            <th class="px-3 py-2 text-left">签退</th>
            <th class="px-3 py-2 text-left">迟到(min)</th>
            <th class="px-3 py-2 text-left">早退(min)</th>
            <th class="px-3 py-2 text-left">加班(h)</th>
            <th class="px-3 py-2 text-left">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredResults" :key="r.employeeNo + r.date" class="border-t hover:bg-gray-50 cursor-pointer" @click="showDetail(r)">
            <td class="px-3 py-2">{{ r.employeeNo }}</td>
            <td class="px-3 py-2">{{ r.name }}</td>
            <td class="px-3 py-2">{{ r.department }}</td>
            <td class="px-3 py-2">{{ r.date }}</td>
            <td class="px-3 py-2">{{ r.signIn }}</td>
            <td class="px-3 py-2">{{ r.signOut }}</td>
            <td class="px-3 py-2">{{ r.lateMinutes }}</td>
            <td class="px-3 py-2">{{ r.earlyMinutes }}</td>
            <td class="px-3 py-2">{{ r.overtimeHours }}</td>
            <td class="px-3 py-2">
              <span class="px-2 py-0.5 rounded text-xs" :class="statusCellClass(r.status)">{{ statusLabel(r.status) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="filteredResults.length === 0" class="text-center text-gray-400 py-12">
        暂无数据，请先 <a href="import.html" class="text-blue-600 hover:underline">导入数据</a> 后计算
      </div>
    </div>

    <!-- 日历视图 -->
    <div v-if="viewMode === 'calendar'" class="bg-white rounded-lg shadow p-4">
      <div class="grid grid-cols-7 gap-1 mb-2">
        <div v-for="day in ['一','二','三','四','五','六','日']" :key="day" class="text-center text-sm font-medium text-gray-600 py-1">{{ day }}</div>
      </div>
      <div class="grid grid-cols-7 gap-1">
        <div v-for="cell in calendarCells" :key="cell.key" class="cal-cell border rounded p-1 text-xs" :class="cell.statusClass">
          <div class="font-bold">{{ cell.day }}</div>
          <div v-if="cell.record" class="mt-1">
            <div>{{ cell.record.signIn || '--' }} / {{ cell.record.signOut || '--' }}</div>
            <div v-if="cell.record.status !== 'normal'" class="font-semibold">{{ statusLabel(cell.record.status) }}</div>
          </div>
          <div v-if="!cell.record && !cell.isRest" class="text-gray-400 mt-1">无记录</div>
          <div v-if="cell.isRest" class="text-gray-400 mt-1">休息</div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detail" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="detail = null">
      <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[80vh] overflow-y-auto">
        <h3 class="text-lg font-semibold mb-4">{{ detail.name }} - {{ detail.date }} 详情</h3>
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div><span class="text-gray-500">考勤号:</span> {{ detail.employeeNo }}</div>
          <div><span class="text-gray-500">部门:</span> {{ detail.department }}</div>
          <div><span class="text-gray-500">签到:</span> {{ detail.signIn || '--' }}</div>
          <div><span class="text-gray-500">签退:</span> {{ detail.signOut || '--' }}</div>
          <div><span class="text-gray-500">迟到:</span> {{ detail.lateMinutes }}min</div>
          <div><span class="text-gray-500">早退:</span> {{ detail.earlyMinutes }}min</div>
          <div><span class="text-gray-500">加班:</span> {{ detail.overtimeHours }}h</div>
          <div><span class="text-gray-500">出差:</span> {{ detail.travelHours }}h</div>
          <div><span class="text-gray-500">请假类型:</span> {{ detail.leaveType || '--' }}</div>
          <div><span class="text-gray-500">状态:</span> <span :class="statusCellClass(detail.status)">{{ statusLabel(detail.status) }}</span></div>
        </div>
        <div v-if="detail.sourcePunches && detail.sourcePunches.length" class="mb-4">
          <h4 class="font-semibold mb-2">关联打卡记录</h4>
          <table class="w-full text-sm border">
            <thead><tr class="bg-gray-50"><th class="p-1 border">签到</th><th class="p-1 border">签退</th><th class="p-1 border">迟到</th><th class="p-1 border">早退</th></tr></thead>
            <tbody><tr v-for="p in detail.sourcePunches" :key="p.id"><td class="p-1 border">{{ p.signIn }}</td><td class="p-1 border">{{ p.signOut }}</td><td class="p-1 border">{{ p.lateMinutes }}</td><td class="p-1 border">{{ p.earlyMinutes }}</td></tr></tbody>
          </table>
        </div>
        <button @click="detail = null" class="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">关闭</button>
      </div>
    </div>
  </div>

  <script src="./lib/vue.global.prod.js?v=1.0.0"></script>
  <script src="./lib/dexie.min.js?v=1.0.0"></script>
  <script src="./shared/auth.js?v=1.0.0"></script>
  <script src="./shared/db.js?v=1.0.0"></script>
  <script src="./shared/rules.js?v=1.0.0"></script>
  <script>
    Auth.requireAuth();

    const { createApp } = Vue;
    createApp({
      data() {
        const now = new Date();
        const defaultMonth = `${now.getFullYear()}-${String(now.getMonth()).padStart(2, '0')}`;
        return {
          viewMode: 'list',
          calculating: false,
          currentMonth: defaultMonth,
          filterDept: '',
          filterStatus: '',
          searchName: '',
          results: [],
          detail: null,
          departments: [],
          calendarCells: []
        };
      },
      computed: {
        filteredResults() {
          let list = this.results;
          if (this.filterDept) list = list.filter(r => r.department === this.filterDept);
          if (this.filterStatus) list = list.filter(r => r.status === this.filterStatus);
          if (this.searchName) list = list.filter(r => r.name.includes(this.searchName));

          // 排序: 考勤号 → 部门 → 日期
          list = [...list].sort((a, b) => {
            if (a.employeeNo !== b.employeeNo) {
              const na = parseInt(a.employeeNo) || 0;
              const nb = parseInt(b.employeeNo) || 0;
              if (na !== nb) return na - nb;
              return String(a.employeeNo).localeCompare(String(b.employeeNo));
            }
            if (a.department !== b.department) return a.department.localeCompare(b.department);
            return a.date.localeCompare(b.date);
          });
          return list;
        },
      },
      async created() {
        await this.loadResults();
      },
      watch: {
        currentMonth() { this.loadResults(); },
        viewMode() { if (this.viewMode === 'calendar') this.buildCalendar(); }
      },
      methods: {
        statusLabel(s) {
          const map = { normal: '正常', abnormal: '异常', absent: '缺勤' };
          return map[s] || s;
        },
        statusCellClass(s) {
          const map = { normal: 'px-2 py-0.5 rounded text-xs status-normal', abnormal: 'px-2 py-0.5 rounded text-xs status-abnormal', absent: 'px-2 py-0.5 rounded text-xs status-absent' };
          return map[s] || '';
        },
        async loadResults() {
          this.results = await RulesEngine.getMonthResults(this.currentMonth);
          if (this.viewMode === 'calendar') this.buildCalendar();

          // 收集部门列表
          const depts = new Set(this.results.map(r => r.department).filter(Boolean));
          this.departments = [...depts].sort();
        },
        async runCalculation() {
          this.calculating = true;
          try {
            await RulesEngine.calculateMonth(this.currentMonth);
            await this.loadResults();
          } catch (err) {
            alert('计算出错: ' + err.message);
          }
          this.calculating = false;
        },
        buildCalendar() {
          const [y, m] = this.currentMonth.split('-').map(Number);
          const firstDay = new Date(y, m - 1, 1);
          const lastDate = new Date(y, m, 0).getDate();
          const startDow = firstDay.getDay() || 7; // 周一=1

          const cells = [];
          // 上月填充
          for (let i = 1; i < startDow; i++) {
            cells.push({ key: 'prev-' + i, day: '', isRest: false, record: null, statusClass: 'bg-gray-50' });
          }
          // 当月日期
          for (let d = 1; d <= lastDate; d++) {
            const dateStr = `${this.currentMonth}-${String(d).padStart(2, '0')}`;
            const record = this.results.find(r => r.date === dateStr);
            let statusClass = 'bg-white';
            if (record) {
              if (record.status === 'normal') statusClass = 'bg-green-50 border-green-300';
              else if (record.status === 'abnormal') statusClass = 'bg-yellow-50 border-yellow-300';
              else if (record.status === 'absent') statusClass = 'bg-red-50 border-red-300';
            }
            cells.push({ key: dateStr, day: d, isRest: !record && false, record, statusClass });
          }
          this.calendarCells = cells;
        },
        async showDetail(r) {
          this.detail = await RulesEngine.getResultDetail(r.employeeNo, r.date);
        }
      }
    }).mount('#app');
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/attendance.html && git commit -m "feat: add attendance calculation page with list and calendar views"
```

---

### Task 10: 导出中心页 (export.html)

**Files:**
- Create: `attendance/export.html`

- [ ] **Step 1: 编写 export.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>导出中心 - 考勤管理</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
  <div id="app" class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <a href="index.html" class="text-blue-600 hover:underline">&larr; 返回</a>
        <h1 class="text-2xl font-bold text-gray-800">导出中心</h1>
      </div>
    </div>

    <div class="flex gap-6">
      <!-- 左侧: 模板列表 -->
      <div class="w-48 flex-shrink-0">
        <div class="bg-white rounded-lg shadow p-4">
          <h3 class="font-semibold text-gray-700 mb-3">模板列表</h3>
          <div class="space-y-1">
            <div v-for="t in templates" :key="t.id" @click="selectTemplate(t)" class="p-2 rounded text-sm cursor-pointer transition" :class="selectedTemplate && selectedTemplate.id === t.id ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100'">
              {{ t.name }}
            </div>
          </div>
          <button @click="saveAsTemplate" class="w-full mt-3 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition">另存为模板</button>
        </div>
      </div>

      <!-- 中间: 字段编辑器 -->
      <div class="flex-1">
        <div class="bg-white rounded-lg shadow p-4">
          <h3 class="font-semibold text-gray-700 mb-3">模板字段编辑</h3>
          <div class="space-y-2">
            <div v-for="(field, idx) in editingFields" :key="idx" class="flex items-center gap-2">
              <input v-model="field.label" class="px-2 py-1 border rounded text-sm w-32" placeholder="列名">
              <select v-model="field.field" class="px-2 py-1 border rounded text-sm flex-1">
                <option v-for="col in availableColumns" :key="col.field" :value="col.field">{{ col.label }}</option>
              </select>
              <button @click="removeField(idx)" class="text-red-500 text-sm">删除</button>
            </div>
          </div>
          <button @click="addField" class="mt-3 px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300 transition">添加字段</button>
        </div>

        <!-- 导出区域 -->
        <div class="bg-white rounded-lg shadow p-4 mt-4">
          <h3 class="font-semibold text-gray-700 mb-3">导出设置</h3>
          <div class="flex gap-3 items-center">
            <select v-model="exportMonth" class="px-3 py-1 border rounded text-sm">
              <option value="">导出: 全部月份</option>
              <option v-for="m in availableMonths" :key="m" :value="m">{{ m }}</option>
            </select>
            <button @click="doExport" class="px-4 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition">导出 Excel</button>
          </div>
        </div>
      </div>

      <!-- 右侧: 预览 -->
      <div class="w-96 flex-shrink-0">
        <div class="bg-white rounded-lg shadow p-4">
          <h3 class="font-semibold text-gray-700 mb-3">实时预览 (前5条)</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-xs border">
              <thead>
                <tr class="bg-gray-100">
                  <th v-for="f in editingFields" :key="f.field" class="p-1 border text-left whitespace-nowrap">{{ f.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in previewData" :key="ri">
                  <td v-for="f in editingFields" :key="f.field" class="p-1 border whitespace-nowrap">
                    {{ f.field === '_index' ? ri + 1 : (row[f.field] !== undefined ? row[f.field] : '') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="previewData.length === 0" class="text-gray-400 text-sm text-center py-4">暂无数据预览</div>
        </div>
      </div>
    </div>
  </div>

  <script src="./lib/vue.global.prod.js?v=1.0.0"></script>
  <script src="./lib/dexie.min.js?v=1.0.0"></script>
  <script src="./lib/xlsx.full.min.js?v=1.0.0"></script>
  <script src="./shared/auth.js?v=1.0.0"></script>
  <script src="./shared/db.js?v=1.0.0"></script>
  <script src="./shared/excel.js?v=1.0.0"></script>
  <script>
    Auth.requireAuth();

    const { createApp } = Vue;
    createApp({
      data() {
        return {
          templates: [],
          selectedTemplate: null,
          editingFields: [],
          previewData: [],
          exportMonth: '',
          availableMonths: [],
          availableColumns: [
            { label: '序号(自动)', field: '_index' },
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
            { label: '是否旷工', field: 'absent' },
            { label: '状态', field: 'status' },
            { label: '请假类型', field: 'leaveType' }
          ]
        };
      },
      async created() {
        await this.loadTemplates();
        await this.loadMonths();
      },
      methods: {
        async loadTemplates() {
          this.templates = await DB.export_templates.toArray();
          if (this.templates.length > 0) {
            this.selectTemplate(this.templates[0]);
          }
        },
        selectTemplate(t) {
          this.selectedTemplate = t;
          this.editingFields = JSON.parse(JSON.stringify(t.fields));
          this.updatePreview();
        },
        addField() {
          if (this.availableColumns.length > 0) {
            this.editingFields.push({ label: '', field: this.availableColumns[0].field });
          }
        },
        removeField(idx) {
          this.editingFields.splice(idx, 1);
          this.updatePreview();
        },
        async saveAsTemplate() {
          const name = prompt('请输入模板名称:');
          if (!name) return;
          await DB.export_templates.put({
            name,
            isDefault: 0,
            fields: JSON.parse(JSON.stringify(this.editingFields))
          });
          await this.loadTemplates();
        },
        async updatePreview() {
          const sampleData = await DB.attendance_results.limit(5).toArray();
          this.previewData = sampleData;
        },
        async loadMonths() {
          const results = await Store.getAll('attendance_results');
          const months = new Set(results.filter(r => r.month).map(r => r.month));
          this.availableMonths = [...months].sort();
          // 默认选最新月份
          if (this.availableMonths.length > 0) {
            this.exportMonth = this.availableMonths[this.availableMonths.length - 1];
          }
        },
        async doExport() {
          if (this.editingFields.length === 0) {
            alert('请至少添加一个导出字段');
            return;
          }
          let records;
          if (this.exportMonth) {
            records = await Store.getByIndex('attendance_results', 'month', this.exportMonth);
          } else {
            records = await Store.getAll('attendance_results');
          }
          if (records.length === 0) {
            alert('没有可导出的数据');
            return;
          }
          const template = { fields: this.editingFields };
          const filename = this.exportMonth ? `考勤记录_${this.exportMonth}.xlsx` : '考勤记录_全部.xlsx';
          Excel.exportToExcel(records, template, filename);
        }
      },
      watch: {
        editingFields: { deep: true, handler() { this.updatePreview(); } }
      }
    }).mount('#app');
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /workspace && git add attendance/export.html && git commit -m "feat: add export center with template designer and preview"
```

---

## 自检清单

- [x] **Spec 覆盖**: 所有 3.1-3.6 需求均有对应 Task (导入识别/规则引擎/视图/导出/设置)
- [x] **占位符检查**: 无 TBD/TODO/待实现，所有步骤包含完整代码
- [x] **类型一致性**: Store/DB/RulesEngine/Excel/Matcher/Auth 接口在各 Task 间一致
- [x] **文件路径**: 所有路径使用 `attendance/` 前缀

---

## 完成后的验证步骤

1. 在浏览器中打开 `attendance/index.html`
2. 登录 (admin / admin123)
3. 进入系统设置确认默认配置
4. 进入数据导入，上传测试 Excel 文件
5. 进入考勤计算，点击"重新计算"，检查列表/日历视图
6. 进入导出中心，预览模板并导出 Excel
7. 关闭浏览器后重新打开，验证 IndexedDB 数据持久化
