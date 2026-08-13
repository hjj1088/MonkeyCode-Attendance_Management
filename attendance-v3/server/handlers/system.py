import os
import json
import bcrypt
import time
from datetime import datetime, timezone

from database import get_db
from middleware import verify_token

SERVER_START_TIME = None
APP_VERSION = '3.1.0'


def set_start_time():
    global SERVER_START_TIME
    SERVER_START_TIME = datetime.now(timezone.utc)


def _get_admin_user(conn):
    try:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", ('admin',)
        ).fetchone()
    except Exception:
        return None


def handle_system_version(handler):
    handler._send_json(0, data={
        'app_version': APP_VERSION,
        'version_name': 'V3.1',
    })


def handle_system_status(handler):
    from middleware import verify_token
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return

    conn = get_db()
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'attendance.db')
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    tables = [
        'users', 'punch_records', 'leave_records', 'overtime_records',
        'travel_records', 'miss_punch_records', 'schedules', 'attendance_results',
        'carry_over', 'holidays', 'settings', 'export_templates',
        'employees', 'raw_files', 'operation_logs',
    ]
    record_counts = {}
    for t in tables:
        row = conn.execute("SELECT COUNT(*) as cnt FROM {}".format(t)).fetchone()
        record_counts[t] = row['cnt']
    conn.close()

    uptime_seconds = 0
    if SERVER_START_TIME:
        uptime_seconds = int((datetime.now(timezone.utc) - SERVER_START_TIME).total_seconds())

    handler._send_json(0, data={
        'app_version': APP_VERSION,
        'db_size_bytes': db_size,
        'db_size_mb': round(db_size / (1024 * 1024), 2),
        'record_counts': record_counts,
        'uptime_seconds': uptime_seconds,
        'server_start_time': SERVER_START_TIME.isoformat() if SERVER_START_TIME else None,
        'python_version': __import__('sys').version.split()[0],
    })


def handle_check_default_password(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return

    conn = get_db()
    admin = _get_admin_user(conn)
    conn.close()
    if not admin:
        handler._send_json(0, data={'is_default': False})
        return

    is_default = bcrypt.checkpw('admin123'.encode(), admin['password_hash'].encode())
    handler._send_json(0, data={'is_default': is_default})


def handle_admin_password(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return

    try:
        data = handler._read_body()
    except Exception:
        handler._send_json(1, message='无效的请求格式')
        return

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        handler._send_json(1, message='当前密码和新密码不能为空')
        return
    if len(new_password) < 6:
        handler._send_json(1, message='新密码长度不能少于6位')
        return

    conn = get_db()
    admin = _get_admin_user(conn)
    if not admin:
        conn.close()
        handler._send_json(1, message='管理员账号不存在')
        return

    if not bcrypt.checkpw(current_password.encode(), admin['password_hash'].encode()):
        conn.close()
        handler._send_json(1, message='当前密码不正确')
        return

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (new_hash,))
    conn.commit()
    conn.close()

    handler._send_json(0, data={'message': '管理员密码修改成功'})


def handle_system_config(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return

    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings WHERE key IN ('company_name', 'data_retention_days')").fetchall()
    config = {row['key']: row['value'] for row in rows}
    conn.close()
    handler._send_json(0, data=config)


def handle_system_config_update(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return

    try:
        data = handler._read_body()
    except Exception:
        handler._send_json(1, message='无效的请求格式')
        return

    allowed_keys = {'company_name', 'data_retention_days'}
    conn = get_db()
    for key, value in data.items():
        if key in allowed_keys:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value))
            )
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '配置已更新'})


def _require_hradmin(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return None
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return None
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return None
    return payload


def handle_seed_test_data(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return

    import random
    from datetime import datetime, timedelta

    conn = get_db()

    departments = [
        ('技术部', '技术部管理员'),
        ('销售部', '销售部管理员'),
        ('行政部', '行政部'),
    ]

    password_hash = bcrypt.hashpw('test123'.encode(), bcrypt.gensalt()).decode()

    for dept_name, admin_name in departments:
        existing = conn.execute("SELECT id FROM users WHERE department = ? AND role = 'employee' LIMIT 1", (dept_name,)).fetchone()
        if existing:
            continue

        for i in range(1, 6):
            emp_no = '{}{:03d}'.format(dept_name[:1], i)
            username = emp_no.lower()
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, name, department, role) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, '{}{}'.format(dept_name, i), dept_name, 'employee')
            )

        if admin_name:
            dept_username = 'dept_' + dept_name[:1].lower()
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, name, department, role) VALUES (?, ?, ?, ?, ?)",
                (dept_username, password_hash, admin_name, dept_name, 'deptadmin')
            )

    conn.commit()

    today = datetime.now()
    first_day = today.replace(day=1)
    test_month = first_day.strftime('%Y-%m')

    def workdays_in_month():
        days = []
        current = first_day
        while current.month == first_day.month:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days

    employees = conn.execute("SELECT * FROM users WHERE role = 'employee'").fetchall()

    for emp in employees:
        for day in workdays_in_month():
            date_str = day.strftime('%Y-%m-%d')
            sign_in_h = random.randint(7, 8)
            sign_in_m = random.randint(0, 59)
            sign_in = '{:02d}:{:02d}'.format(sign_in_h, sign_in_m)

            sign_out_h = random.randint(17, 19)
            sign_out_m = random.randint(0, 59)
            sign_out = '{:02d}:{:02d}'.format(sign_out_h, sign_out_m)

            conn.execute(
                "INSERT OR IGNORE INTO punch_records (employeeNo, name, department, date, signIn, signOut, scheduleStart, scheduleEnd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (emp['username'], emp['name'], emp['department'], date_str, sign_in, sign_out, '08:30', '17:30')
            )

        leave_date = first_day + timedelta(days=random.randint(5, 15))
        conn.execute(
            "INSERT INTO leave_records (applicant, department, leaveType, startDate, endDate, leaveDays, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (emp['name'], emp['department'], '年假', leave_date.strftime('%Y-%m-%d'), leave_date.strftime('%Y-%m-%d'), 1, '测试请假')
        )

    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '测试数据生成成功'})


def handle_reset_data(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return

    conn = get_db()
    business_tables = [
        'punch_records', 'leave_records', 'overtime_records',
        'travel_records', 'miss_punch_records', 'schedules',
        'attendance_results',
    ]
    for t in business_tables:
        conn.execute("DELETE FROM {}".format(t))
    conn.execute("DELETE FROM carry_over")
    conn.execute("DELETE FROM raw_files")
    conn.execute("DELETE FROM employees")
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '业务数据已清空，用户和配置已保留'})
