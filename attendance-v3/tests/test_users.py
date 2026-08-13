import os
import sys
import tempfile
import bcrypt
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

import database


def setup_module():
    database.DB_DIR = os.path.join(tempfile.gettempdir(), 'attendance-v3-users-test')
    database.DB_PATH = os.path.join(database.DB_DIR, 'attendance.db')
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    database.init_db()


def _conn():
    return database.get_db()


def test_users_table_exists():
    conn = _conn()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None
    conn.close()


def test_operation_logs_table_exists():
    conn = _conn()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='operation_logs'")
    assert cursor.fetchone() is not None
    conn.close()


def test_create_user():
    conn = _conn()
    uid = database.create_user(conn, 'zhangsan', 'hash1', '张三', '技术部', 'employee')
    assert uid is not None
    user = database.get_user_by_username(conn, 'zhangsan')
    assert user is not None
    assert user['name'] == '张三'
    assert user['role'] == 'employee'
    assert user['enabled'] == 1
    conn.close()


def test_create_duplicate_username_fails():
    conn = _conn()
    database.create_user(conn, 'dupe', 'hash1', '甲', '行政部', 'employee')
    with pytest.raises(Exception):
        database.create_user(conn, 'dupe', 'hash2', '乙', '行政部', 'employee')
    conn.close()


def test_get_all_users():
    conn = _conn()
    database.create_user(conn, 'u_all_1', 'h', '用户1', '技术部', 'employee')
    database.create_user(conn, 'u_all_2', 'h', '用户2', '销售部', 'deptadmin')
    users = database.get_all_users(conn)
    usernames = {u['username'] for u in users}
    assert 'u_all_1' in usernames
    assert 'u_all_2' in usernames
    conn.close()


def test_update_user():
    conn = _conn()
    uid = database.create_user(conn, 'upd', 'h', '原名', '技术部', 'employee')
    database.update_user(conn, uid, {'name': '新名', 'department': '销售部'})
    user = database.get_user_by_id(conn, uid)
    assert user['name'] == '新名'
    assert user['department'] == '销售部'
    conn.close()


def test_set_user_enabled():
    conn = _conn()
    uid = database.create_user(conn, 'dis', 'h', '禁用者', '行政部', 'employee')
    database.set_user_enabled(conn, uid, False)
    user = database.get_user_by_id(conn, uid)
    assert user['enabled'] == 0
    conn.close()


def test_increment_login_attempt_locks_after_5():
    conn = _conn()
    uid = database.create_user(conn, 'locker', 'h', '锁定者', '技术部', 'employee')
    info = None
    for _ in range(5):
        info = database.increment_login_attempt(conn, uid)
    assert info['login_attempts'] == 5
    user = database.get_user_by_id(conn, uid)
    assert user['locked_until'] is not None
    conn.close()


def test_reset_login_attempts():
    conn = _conn()
    uid = database.create_user(conn, 'resetme', 'h', '重置者', '技术部', 'employee')
    for _ in range(5):
        database.increment_login_attempt(conn, uid)
    database.reset_login_attempts(conn, uid)
    user = database.get_user_by_id(conn, uid)
    assert user['login_attempts'] == 0
    assert user['locked_until'] is None
    conn.close()


def test_log_operation():
    conn = _conn()
    database.log_operation(conn, 'admin', 'login', 'admin logged in')
    row = conn.execute(
        "SELECT * FROM operation_logs WHERE username='admin' AND action='login'"
    ).fetchone()
    assert row is not None
    assert 'admin logged in' in row['detail']
    conn.close()


def test_init_system_writes_defaults():
    conn = _conn()
    database.init_system(conn)
    company = conn.execute("SELECT value FROM settings WHERE key='company_name'").fetchone()
    retention = conn.execute("SELECT value FROM settings WHERE key='data_retention_days'").fetchone()
    assert company is not None and company['value']
    assert retention is not None and retention['value'] == '365'
    conn.close()
