import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

import database


def setup_module():
    database.DB_DIR = os.path.join(tempfile.gettempdir(), 'attendance-v3-generic-test')
    database.DB_PATH = os.path.join(database.DB_DIR, 'attendance.db')
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    database.init_db()


def _conn():
    return database.get_db()


def test_insert_records_punch():
    conn = _conn()
    records = [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部', 'date': '2026-08-01', 'signIn': '08:20'},
        {'employeeNo': 'T002', 'name': '李四', 'department': '技术部', 'date': '2026-08-01', 'signIn': '08:21'},
    ]
    count = database.insert_records(conn, 'punch_records', records)
    conn.commit()
    assert count == 2
    rows = conn.execute("SELECT * FROM punch_records").fetchall()
    assert len(rows) == 2
    assert rows[0]['employeeNo'] == 'T001'
    conn.close()


def test_insert_records_json_and_bool_serialization():
    conn = _conn()
    database.insert_records(conn, 'schedules', [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部', 'year': 2026, 'month': 8,
         'workDays': {'1': True, '2': False}},
    ])
    conn.commit()
    row = conn.execute("SELECT * FROM schedules").fetchone()
    import json
    assert json.loads(row['workDays']) == {'1': True, '2': False}

    database.insert_records(conn, 'holidays', [
        {'date': '2026-10-01', 'name': '国庆', 'isWorkday': False, 'isHoliday': True},
    ])
    conn.commit()
    holiday = conn.execute("SELECT * FROM holidays").fetchone()
    assert holiday['isWorkday'] == 0
    assert holiday['isHoliday'] == 1
    conn.close()


def test_insert_records_settings_upsert():
    conn = _conn()
    database.insert_records(conn, 'settings', [{'key': 'company_name', 'value': '测试公司'}])
    conn.commit()
    row = conn.execute("SELECT value FROM settings WHERE key='company_name'").fetchone()
    assert row['value'] == '测试公司'
    conn.close()


def test_clear_table():
    conn = _conn()
    database.insert_records(conn, 'punch_records', [{'employeeNo': 'T001', 'date': '2026-08-01'}])
    conn.commit()
    database.clear_table(conn, 'punch_records')
    rows = conn.execute("SELECT * FROM punch_records").fetchall()
    assert len(rows) == 0
    conn.close()
