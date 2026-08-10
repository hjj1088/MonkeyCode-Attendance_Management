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
