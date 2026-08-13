"""
阶段 B 集成测试：真实 HTTP 服务器全链路（登录/锁定/改密/用户 CRUD/角色鉴权）
"""
import json
import os
import sys
import threading
import time
import tempfile
import urllib.request
import urllib.error
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(TESTS_DIR, '..', 'server')

# Use a dedicated DB so we don't touch the dev database
TEST_DB_DIR = os.path.join(tempfile.gettempdir(), 'attendance-v3-e2e')
sys.path.insert(0, SERVER_DIR)

PORT = 18081
BASE = 'http://127.0.0.1:{}'.format(PORT)

SERVER_PROC = None
SESSION_TOKEN = {}


def _api(method, path, body=None, token=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if raw:
                return resp.status, content
            return resp.status, json.loads(content)
    except urllib.error.HTTPError as e:
        content = e.read()
        if raw:
            return e.code, content
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {'code': 1, 'message': content.decode('utf-8', 'ignore')}


@pytest.fixture(scope='module', autouse=True)
def server():
    import database
    database.DB_DIR = TEST_DB_DIR
    database.DB_PATH = os.path.join(TEST_DB_DIR, 'attendance.db')
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)

    from server import main  # noqa: F401  (import server module to get PORT)
    import server as server_mod
    server_mod.PORT = PORT
    from handlers.auth import ensure_admin_user
    database.init_db()
    ensure_admin_user()

    from http.server import HTTPServer
    from server import APIHandler
    httpd = HTTPServer(('127.0.0.1', PORT), APIHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)
    yield
    httpd.shutdown()


def test_login_admin():
    status, body = _api('POST', '/api/auth/login', {'username': 'admin', 'password': 'admin123'})
    assert status == 200
    assert body['code'] == 0
    SESSION_TOKEN['admin'] = body['data']['token']
    assert body['data']['user']['role'] == 'hradmin'
    assert body['data']['need_change_password'] is True


def test_login_check_valid():
    status, body = _api('GET', '/api/auth/login-check', token=SESSION_TOKEN['admin'])
    assert status == 200
    assert body['data']['valid'] is True


def test_login_wrong_password():
    status, body = _api('POST', '/api/auth/login', {'username': 'admin', 'password': 'wrong'})
    assert status != 200 or body['code'] != 0


def test_unauthorized_store_rejected():
    status, body = _api('GET', '/api/store/settings')
    assert status == 401


def test_create_user():
    status, body = _api('POST', '/api/users', {
        'username': 'zhangsan', 'name': '张三', 'department': '技术部',
        'role': 'employee', 'password': '123456',
    }, token=SESSION_TOKEN['admin'])
    assert status == 200
    assert body['code'] == 0


def test_duplicate_username_rejected():
    status, body = _api('POST', '/api/users', {
        'username': 'zhangsan', 'name': '张三2', 'department': '技术部',
        'role': 'employee', 'password': '123456',
    }, token=SESSION_TOKEN['admin'])
    assert status == 400
    assert '已存在' in body['message']


def test_users_list():
    status, body = _api('GET', '/api/users', token=SESSION_TOKEN['admin'])
    assert status == 200
    usernames = [u['username'] for u in body['data']]
    assert 'admin' in usernames
    assert 'zhangsan' in usernames


def test_employee_login():
    status, body = _api('POST', '/api/auth/login', {'username': 'zhangsan', 'password': '123456'})
    assert status == 200
    assert body['code'] == 0
    assert body['data']['user']['role'] == 'employee'
    SESSION_TOKEN['employee'] = body['data']['token']


def test_employee_cannot_list_users():
    status, body = _api('GET', '/api/users', token=SESSION_TOKEN['employee'])
    assert status == 403


def test_disabled_user_login_fails():
    user_id = None
    status, body = _api('GET', '/api/users', token=SESSION_TOKEN['admin'])
    for u in body['data']:
        if u['username'] == 'zhangsan':
            user_id = u['id']

    status, body = _api('PATCH', '/api/users/{}/status'.format(user_id), {'enabled': 0},
                        token=SESSION_TOKEN['admin'])
    assert status == 200

    status, body = _api('POST', '/api/auth/login', {'username': 'zhangsan', 'password': '123456'})
    assert body['code'] != 0
    assert '禁用' in body['message']

    _api('PATCH', '/api/users/{}/status'.format(user_id), {'enabled': 1}, token=SESSION_TOKEN['admin'])


def test_login_lockout_after_5_failures():
    # create a fresh user
    _api('POST', '/api/users', {'username': 'lockme', 'name': '锁定者', 'department': '行政部',
                                'role': 'employee', 'password': '123456'}, token=SESSION_TOKEN['admin'])
    for _ in range(5):
        _api('POST', '/api/auth/login', {'username': 'lockme', 'password': 'bad'})
    status, body = _api('POST', '/api/auth/login', {'username': 'lockme', 'password': '123456'})
    assert body['code'] != 0
    assert '锁定' in body['message']


def test_change_password_then_old_fails():
    status, body = _api('POST', '/api/auth/change-password',
                        {'old_password': 'admin123', 'new_password': 'NewAdmin@2026'},
                        token=SESSION_TOKEN['admin'])
    assert status == 200
    assert body['code'] == 0

    status, body = _api('POST', '/api/auth/login', {'username': 'admin', 'password': 'admin123'})
    assert body['code'] != 0

    status, body = _api('POST', '/api/auth/login', {'username': 'admin', 'password': 'NewAdmin@2026'})
    assert status == 200
    assert body['data']['need_change_password'] is False
    SESSION_TOKEN['admin'] = body['data']['token']
