import os
import sys
import tempfile
import bcrypt
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

import database
from middleware import generate_token, verify_token


def setup_module():
    database.DB_DIR = os.path.join(tempfile.gettempdir(), 'attendance-v3-auth-test')
    database.DB_PATH = os.path.join(database.DB_DIR, 'attendance.db')
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    database.init_db()


def test_bcrypt_hash_and_verify():
    password = 'test_password_123'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    assert bcrypt.checkpw(password.encode(), hashed.encode())
    assert not bcrypt.checkpw('wrong_password'.encode(), hashed.encode())


def test_jwt_generate_and_verify():
    token = generate_token(1, 'testuser', 'employee', '技术部')
    payload = verify_token(token)
    assert payload is not None
    assert payload['uid'] == 1
    assert payload['username'] == 'testuser'
    assert payload['role'] == 'employee'
    assert payload['department'] == '技术部'


def test_jwt_expired_token():
    import jwt
    import time
    expired = jwt.encode(
        {'uid': 1, 'username': 'test', 'role': 'employee', 'department': '', 'exp': int(time.time()) - 1},
        os.environ.get('JWT_SECRET', 'attendance-v3-default-secret-key-change-in-production'),
        algorithm='HS256'
    )
    assert verify_token(expired) is None


def test_jwt_invalid_token():
    assert verify_token('invalid.token.here') is None
    assert verify_token('') is None
    assert verify_token(None) is None


def test_ensure_admin_user():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server', 'handlers'))
    import handlers.auth as auth_mod

    conn = database.get_db()
    conn.execute("DELETE FROM users WHERE username='admin'")
    conn.commit()
    conn.close()

    auth_mod.ensure_admin_user()

    conn = database.get_db()
    user = database.get_user_by_username(conn, 'admin')
    conn.close()
    assert user is not None
    assert user['role'] == 'hradmin'
    assert bcrypt.checkpw('admin123'.encode(), user['password_hash'].encode())


def test_ensure_admin_user_idempotent():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server', 'handlers'))
    import handlers.auth as auth_mod

    auth_mod.ensure_admin_user()
    auth_mod.ensure_admin_user()

    conn = database.get_db()
    user = database.get_user_by_username(conn, 'admin')
    conn.close()
    assert user is not None
    assert user['role'] == 'hradmin'
