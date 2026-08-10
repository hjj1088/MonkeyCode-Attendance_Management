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


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_create_user():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_create_duplicate_username_fails():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_get_all_users():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_update_user():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_set_user_enabled():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_increment_login_attempt_locks_after_5():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_reset_login_attempts():
    pass


@pytest.mark.skip(reason='V3.2 multi-role: users table not implemented in V3.1')
def test_ensure_admin_user():
    pass
