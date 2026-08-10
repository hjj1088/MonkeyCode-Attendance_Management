import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

import database


def setup_module():
    database.DB_DIR = os.path.join(tempfile.gettempdir(), 'attendance-v3-test')
    database.DB_PATH = os.path.join(database.DB_DIR, 'attendance.db')
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)


def test_get_db_returns_connection():
    conn = database.get_db()
    assert conn is not None
    conn.close()


def test_init_tables_creates_all_13_tables():
    database.init_db()
    conn = database.get_db()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor.fetchall()]
    conn.close()

    expected = {
        'attendance_results', 'carry_over', 'employees', 'export_templates',
        'holidays', 'leave_records', 'miss_punch_records',
        'overtime_records', 'punch_records', 'raw_files', 'schedules',
        'settings', 'travel_records',
    }
    missing = expected - set(tables)
    assert not missing, f"Missing tables: {missing}"


def test_init_tables_idempotent():
    database.init_db()
    database.init_db()
    conn = database.get_db()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor.fetchall()]
    conn.close()
    expected = {
        'attendance_results', 'carry_over', 'employees', 'export_templates',
        'holidays', 'leave_records', 'miss_punch_records',
        'overtime_records', 'punch_records', 'raw_files', 'schedules',
        'settings', 'travel_records',
    }
    missing = expected - set(tables)
    assert not missing, f"Missing tables after re-init: {missing}"


def test_attendance_results_schema():
    conn = database.get_db()
    cursor = conn.execute("PRAGMA table_info(attendance_results)")
    columns = {row['name'] for row in cursor.fetchall()}
    conn.close()
    expected_columns = {
        'employeeNo', 'name', 'department', 'date', 'month', 'status',
        'signIn', 'signOut', 'lateMinutes', 'earlyMinutes',
        'overtimeHours', 'travelHours', 'leaveHours', 'workHours',
        'absent', 'leaveType', 'isRestDay', 'missTime',
    }
    assert expected_columns.issubset(columns), f"Missing columns: {expected_columns - columns}"
