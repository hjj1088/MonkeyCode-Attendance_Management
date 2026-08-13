"""
系统初始化单元测试（V3.2）
"""
import os
import sys
import json
import pytest
import tempfile
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    import database
    db_dir = os.path.join(tempfile.gettempdir(), 'attendance-v3-test')
    db_path = os.path.join(db_dir, 'attendance.db')
    monkeypatch.setattr(database, 'DB_DIR', db_dir)
    monkeypatch.setattr(database, 'DB_PATH', db_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_db()
    yield
    try:
        os.remove(db_path)
    except OSError:
        pass


class MockHandler:
    def __init__(self):
        self.sent = None
        self.headers = {}
        self._body = None

    def _send_json(self, code, data=None, message=None):
        self.sent = {'code': code, 'data': data, 'message': message}

    def _read_body(self):
        return json.loads(self._body) if self._body else None


class TestInitSystem:
    def test_init_system_writes_defaults(self):
        import database
        conn = database.get_db()
        database.init_system(conn)
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        conn.close()
        settings = {r['key']: r['value'] for r in rows}
        assert settings['company_name'] == '考勤管理系统'
        assert settings['data_retention_days'] == '365'
        config = json.loads(settings['attendance_config'])
        assert config['workStartTime'] == '08:30'
        assert config['workEndTime'] == '17:30'
        assert config['lateThreshold'] == 0
        assert config['earlyThreshold'] == 0
        assert config['graceTimes'] == 2
        assert config['graceMinutes'] == 30

    def test_init_system_idempotent(self):
        import database
        conn = database.get_db()
        database.init_system(conn)
        count1 = len(conn.execute("SELECT * FROM settings").fetchall())
        database.init_system(conn)
        count2 = len(conn.execute("SELECT * FROM settings").fetchall())
        conn.close()
        assert count1 == count2
        assert count1 >= 3


class TestDefaultPasswordDetection:
    def _token(self, username, role, department='系统'):
        from middleware import generate_token
        return generate_token(1, username, role, department)

    def test_admin_default_password_detected(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_check_default_password

        ensure_admin_user()

        h = MockHandler()
        h.headers = {'Authorization': 'Bearer ' + self._token('admin', 'hradmin')}
        handle_check_default_password(h)
        assert h.sent['code'] == 0
        assert h.sent['data']['is_default'] is True

    def test_after_password_change_not_default(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password, handle_check_default_password

        ensure_admin_user()

        h0 = MockHandler()
        h0.headers = {'Authorization': 'Bearer ' + self._token('admin', 'hradmin')}
        h0._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h0)
        assert h0.sent['code'] == 0

        h1 = MockHandler()
        h1.headers = {'Authorization': 'Bearer ' + self._token('admin', 'hradmin')}
        handle_check_default_password(h1)
        assert h1.sent['data']['is_default'] is False

    def test_login_with_new_password_works(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password

        ensure_admin_user()

        h0 = MockHandler()
        h0.headers = {'Authorization': 'Bearer ' + self._token('admin', 'hradmin')}
        h0._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h0)
        assert h0.sent['code'] == 0

        from handlers.auth import handle_login
        h1 = MockHandler()
        h1._body = json.dumps({'username': 'admin', 'password': 'NewP@ssw0rd!'})
        handle_login(h1)
        assert h1.sent['code'] == 0
        assert h1.sent['data'].get('need_change_password') is False

    def test_old_password_fails_after_change(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password

        ensure_admin_user()

        h0 = MockHandler()
        h0.headers = {'Authorization': 'Bearer ' + self._token('admin', 'hradmin')}
        h0._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h0)
        assert h0.sent['code'] == 0

        from handlers.auth import handle_login
        h1 = MockHandler()
        h1._body = json.dumps({'username': 'admin', 'password': 'admin123'})
        handle_login(h1)
        assert h1.sent['code'] != 0

    def test_non_admin_cannot_change_password(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password

        ensure_admin_user()

        h = MockHandler()
        h.headers = {'Authorization': 'Bearer ' + self._token('user', 'employee', '技术部')}
        h._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h)
        assert h.sent['code'] == 403
