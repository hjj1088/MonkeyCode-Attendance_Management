# V3.1 database.py
# SQLite schema matching V2.0 IndexedDB (camelCase field names, same 13 tables)

import sqlite3
import os
import json

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'attendance.db')


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fileName TEXT NOT NULL DEFAULT '',
            fileType TEXT NOT NULL DEFAULT '',
            recordCount INTEGER NOT NULL DEFAULT 0,
            importTime TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS punch_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employeeNo TEXT NOT NULL DEFAULT '',
            customNo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            scheduleStart TEXT NOT NULL DEFAULT '',
            scheduleEnd TEXT NOT NULL DEFAULT '',
            signIn TEXT NOT NULL DEFAULT '',
            signOut TEXT NOT NULL DEFAULT '',
            lateMinutes REAL NOT NULL DEFAULT 0,
            earlyMinutes REAL NOT NULL DEFAULT 0,
            absent INTEGER NOT NULL DEFAULT 0,
            overtimeHours REAL NOT NULL DEFAULT 0,
            workHours REAL NOT NULL DEFAULT 0,
            department TEXT NOT NULL DEFAULT '',
            isWeekday TEXT NOT NULL DEFAULT '',
            isWeekend TEXT NOT NULL DEFAULT '',
            isHoliday TEXT NOT NULL DEFAULT '',
            weekdayOT REAL NOT NULL DEFAULT 0,
            weekendOT REAL NOT NULL DEFAULT 0,
            holidayOT REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS leave_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            leaveType TEXT NOT NULL DEFAULT '',
            startDate TEXT NOT NULL DEFAULT '',
            endDate TEXT NOT NULL DEFAULT '',
            leaveDays REAL NOT NULL DEFAULT 0,
            leaveHours REAL NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS overtime_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            startTime TEXT NOT NULL DEFAULT '',
            endTime TEXT NOT NULL DEFAULT '',
            overtimeHours REAL NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS travel_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            destination TEXT NOT NULL DEFAULT '',
            travelers TEXT NOT NULL DEFAULT '',
            startDate TEXT NOT NULL DEFAULT '',
            endDate TEXT NOT NULL DEFAULT '',
            travelType TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS miss_punch_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            missDate TEXT NOT NULL DEFAULT '',
            missPerson TEXT NOT NULL DEFAULT '',
            missTime TEXT NOT NULL DEFAULT '',
            cardTime TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employeeNo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            year INTEGER NOT NULL DEFAULT 0,
            month INTEGER NOT NULL DEFAULT 0,
            workDays TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS attendance_results (
            employeeNo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            scheduleStart TEXT NOT NULL DEFAULT '',
            scheduleEnd TEXT NOT NULL DEFAULT '',
            signIn TEXT NOT NULL DEFAULT '',
            signOut TEXT NOT NULL DEFAULT '',
            lateMinutes REAL NOT NULL DEFAULT 0,
            earlyMinutes REAL NOT NULL DEFAULT 0,
            overtimeHours REAL NOT NULL DEFAULT 0,
            travelHours REAL NOT NULL DEFAULT 0,
            leaveHours REAL NOT NULL DEFAULT 0,
            workHours REAL NOT NULL DEFAULT 0,
            absent INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT '',
            leaveType TEXT NOT NULL DEFAULT '',
            isRestDay INTEGER NOT NULL DEFAULT 0,
            month TEXT NOT NULL DEFAULT '',
            sourcePunchIds TEXT NOT NULL DEFAULT '[]',
            sourceLeaveIds TEXT NOT NULL DEFAULT '[]',
            sourceTravelIds TEXT NOT NULL DEFAULT '[]',
            sourceMissIds TEXT NOT NULL DEFAULT '[]',
            sourceOvertimeIds TEXT NOT NULL DEFAULT '[]',
            missTime TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS carry_over (
            employeeNo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            month TEXT NOT NULL DEFAULT '',
            overtimeBalance REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            isWorkday INTEGER NOT NULL DEFAULT 0,
            isHoliday INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS export_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            isDefault INTEGER NOT NULL DEFAULT 0,
            fields TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS employees (
            employeeNo TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'employee',
            password_hash TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            login_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        );
    """)

    # Create indices matching V2.0 IndexedDB indexes
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_raw_files_fileType ON raw_files(fileType);
        CREATE INDEX IF NOT EXISTS idx_punch_employeeNo ON punch_records(employeeNo);
        CREATE INDEX IF NOT EXISTS idx_punch_date ON punch_records(date);
        CREATE INDEX IF NOT EXISTS idx_leave_applicant ON leave_records(applicant);
        CREATE INDEX IF NOT EXISTS idx_leave_startDate ON leave_records(startDate);
        CREATE INDEX IF NOT EXISTS idx_overtime_applicant ON overtime_records(applicant);
        CREATE INDEX IF NOT EXISTS idx_travel_applicant ON travel_records(applicant);
        CREATE INDEX IF NOT EXISTS idx_travel_startDate ON travel_records(startDate);
        CREATE INDEX IF NOT EXISTS idx_miss_applicant ON miss_punch_records(applicant);
        CREATE INDEX IF NOT EXISTS idx_miss_missDate ON miss_punch_records(missDate);
        CREATE INDEX IF NOT EXISTS idx_schedules_employeeNo ON schedules(employeeNo, year, month);
        CREATE INDEX IF NOT EXISTS idx_results_employeeNo ON attendance_results(employeeNo, date);
        CREATE INDEX IF NOT EXISTS idx_results_month ON attendance_results(month);
        CREATE INDEX IF NOT EXISTS idx_results_department ON attendance_results(department);
        CREATE INDEX IF NOT EXISTS idx_carry_employeeNo ON carry_over(employeeNo, month);
        CREATE INDEX IF NOT EXISTS idx_holidays_date ON holidays(date);
        CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(name);
    """)

    # Migrations for pre-existing databases (CREATE TABLE IF NOT EXISTS won't add columns)
    _migrate(conn)

    conn.commit()

    # Init default settings (matching V2.0 initDefaultSettings)
    _init_settings(conn)

    # Init system config defaults (V3.2)
    init_system(conn)

    conn.commit()
    conn.close()


def _migrate(conn):
    results_cols = {row[1] for row in conn.execute("PRAGMA table_info(attendance_results)").fetchall()}
    if 'missTime' not in results_cols:
        conn.execute("ALTER TABLE attendance_results ADD COLUMN missTime TEXT NOT NULL DEFAULT ''")


def _init_settings(conn):
    existing = conn.execute(
        "SELECT value FROM settings WHERE key = 'attendance_config'"
    ).fetchone()
    if not existing:
        config = json.dumps({
            'workStartTime': '08:30',
            'workEndTime': '17:30',
            'lateThreshold': 0,
            'earlyThreshold': 0,
            'graceTimes': 2,
            'graceMinutes': 30
        }, ensure_ascii=False)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('attendance_config', ?)",
            (config,)
        )

    default_template = conn.execute(
        "SELECT id FROM export_templates WHERE isDefault = 1"
    ).fetchone()
    if not default_template:
        fields = json.dumps([
            {'label': '序号', 'field': '_index'},
            {'label': '考勤号码', 'field': 'employeeNo'},
            {'label': '姓名', 'field': 'name'},
            {'label': '部门', 'field': 'department'},
            {'label': '日期', 'field': 'date'},
            {'label': '对应时段', 'field': 'period'},
            {'label': '上班时间', 'field': 'scheduleStart'},
            {'label': '下班时间', 'field': 'scheduleEnd'},
            {'label': '签到时间', 'field': 'signIn'},
            {'label': '签退时间', 'field': 'signOut'},
            {'label': '迟到时间', 'field': 'lateMinutes'},
            {'label': '早退时间', 'field': 'earlyMinutes'},
            {'label': '加班时间', 'field': 'overtimeHours'},
            {'label': '出差时间', 'field': 'travelHours'},
            {'label': '请假类型', 'field': 'leaveType'},
            {'label': '请假小时', 'field': 'leaveHours'},
            {'label': '是否旷工', 'field': 'absent'}
        ], ensure_ascii=False)
        conn.execute(
            "INSERT INTO export_templates (name, isDefault, fields) VALUES ('默认模板', 1, ?)",
            (fields,)
        )


def create_user(conn, username, password_hash, name, department, role='employee'):
    from datetime import datetime
    now = datetime.now().isoformat(timespec='seconds')
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, name, department, role, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, password_hash, name, department, role, now, now)
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_username(conn, username):
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(conn, user_id):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_all_users(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id, username, name, department, role, enabled, login_attempts, locked_until, created_at "
        "FROM users ORDER BY id"
    ).fetchall()]


def update_user(conn, user_id, fields):
    from datetime import datetime
    if not fields:
        return 0
    fields = dict(fields)
    fields['updated_at'] = datetime.now().isoformat(timespec='seconds')
    sets = ', '.join('{} = ?'.format(k) for k in fields)
    cur = conn.execute(
        "UPDATE users SET {} WHERE id = ?".format(sets),
        list(fields.values()) + [user_id]
    )
    conn.commit()
    return cur.rowcount


def set_user_enabled(conn, user_id, enabled):
    return update_user(conn, user_id, {'enabled': 1 if enabled else 0})


def increment_login_attempt(conn, user_id):
    from datetime import datetime, timedelta
    conn.execute(
        "UPDATE users SET login_attempts = login_attempts + 1 WHERE id = ?", (user_id,)
    )
    row = conn.execute("SELECT login_attempts FROM users WHERE id = ?", (user_id,)).fetchone()
    attempts = row['login_attempts'] if row else 0
    if attempts >= 5:
        locked_until = (datetime.now() + timedelta(minutes=30)).isoformat(timespec='seconds')
        conn.execute(
            "UPDATE users SET locked_until = ? WHERE id = ?", (locked_until, user_id)
        )
    conn.commit()
    return {'login_attempts': attempts}


def reset_login_attempts(conn, user_id):
    conn.execute(
        "UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,)
    )
    conn.commit()


def clear_locked_if_expired(conn, user_id):
    from datetime import datetime
    row = conn.execute("SELECT locked_until FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or not row['locked_until']:
        return
    try:
        if datetime.fromisoformat(row['locked_until']) <= datetime.now():
            reset_login_attempts(conn, user_id)
    except ValueError:
        reset_login_attempts(conn, user_id)


def log_operation(conn, username, action, detail=''):
    from datetime import datetime
    conn.execute(
        "INSERT INTO operation_logs (username, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (username or '', action or '', detail or '', datetime.now().isoformat(timespec='seconds'))
    )
    conn.commit()


def init_system(conn):
    """First-boot system config defaults (V3.2). Reuses attendance_config from _init_settings."""
    defaults = {
        'company_name': '考勤管理系统',
        'data_retention_days': '365',
    }
    for key, value in defaults.items():
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
    conn.commit()


JSON_FIELDS = frozenset({
    'workDays', 'fields', 'sourcePunchIds', 'sourceLeaveIds',
    'sourceTravelIds', 'sourceMissIds', 'sourceOvertimeIds', 'value',
})
BOOL_FIELDS = frozenset({'isWorkday', 'isHoliday', 'isDefault', 'absent', 'isRestDay', 'enabled'})


def serialize_record(record):
    """Convert a camelCase record into SQLite-storable values (JSON dump + bool→0/1)."""
    clean = {}
    for k, v in record.items():
        if k in JSON_FIELDS:
            clean[k] = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        elif isinstance(v, bool) or k in BOOL_FIELDS and v in (0, 1, None):
            clean[k] = 1 if v else 0
        else:
            clean[k] = v
    return clean


def insert_records(conn, table, records):
    """Generic bulk insert. Skips `id`; JSON/bool fields serialized. Returns inserted count."""
    count = 0
    for record in records:
        clean = serialize_record(record)
        if table == 'settings':
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (clean.get('key', ''), clean.get('value', ''))
            )
        else:
            clean.pop('id', None)
            cols = ', '.join('"{}"'.format(k) for k in clean.keys())
            placeholders = ', '.join(['?'] * len(clean))
            conn.execute(
                'INSERT INTO {} ({}) VALUES ({})'.format(table, cols, placeholders),
                list(clean.values())
            )
        count += 1
    return count


def clear_table(conn, table):
    conn.execute('DELETE FROM {}'.format(table))
    conn.commit()
