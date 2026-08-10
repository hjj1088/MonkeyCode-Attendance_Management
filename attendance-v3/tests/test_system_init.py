"""
系统初始化单元测试
"""
import os
import sys
import json
import pytest
import tempfile
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

pytestmark = pytest.mark.skip(reason='V3.2: init_system/users admin flow not implemented in V3.1')


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    import database
    db_dir = os.path.join(tempfile.gettempdir(), 'attendance-v3-test')
    db_path = os.path.join(db_dir, 'attendance.db')
    monkeypatch.setattr(database, 'DB_DIR', db_dir)
    monkeypatch.setattr(database, 'DB_PATH', db_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_tables()
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
        database.init_system()
        conn = database.get_db()
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        conn.close()
        settings = {r['key']: r['value'] for r in rows}
        assert settings['company_name'] == '默认公司'
        assert settings['data_retention_days'] == '365'
        assert settings['work_start_time'] == '08:30'
        assert settings['work_end_time'] == '17:30'
        assert settings['late_threshold'] == '0'
        assert settings['early_threshold'] == '0'
        assert settings['tolerance_count'] == '2'
        assert settings['tolerance_minutes'] == '30'

    def test_init_system_idempotent(self):
        import database
        database.init_system()
        count1 = len(database.get_db().execute("SELECT * FROM settings").fetchall())
        database.init_system()
        count2 = len(database.get_db().execute("SELECT * FROM settings").fetchall())
        assert count1 == count2
        assert count1 >= 8


class TestDefaultPasswordDetection:
    def test_admin_default_password_detected(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_check_default_password

        ensure_admin_user()

        h = MockHandler()
        from handlers.auth import generate_token
        token = generate_token(1, 'admin', 'hradmin', '系统')
        h.headers = {'Authorization': 'Bearer ' + token}
        handle_check_default_password(h)
        assert h.sent['code'] == 0
        assert h.sent['data']['is_default'] is True

    def test_after_password_change_not_default(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password, handle_check_default_password

        ensure_admin_user()

        h0 = MockHandler()
        from handlers.auth import generate_token
        token = generate_token(1, 'admin', 'hradmin', '系统')
        h0.headers = {'Authorization': 'Bearer ' + token}
        h0._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h0)
        assert h0.sent['code'] == 0

        h1 = MockHandler()
        h1.headers = {'Authorization': 'Bearer ' + token}
        handle_check_default_password(h1)
        assert h1.sent['data']['is_default'] is False

    def test_login_with_new_password_works(self):
        import database
        from handlers.auth import ensure_admin_user
        from handlers.system import handle_admin_password

        ensure_admin_user()

        h0 = MockHandler()
        from handlers.auth import generate_token
        token = generate_token(1, 'admin', 'hradmin', '系统')
        h0.headers = {'Authorization': 'Bearer ' + token}
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
        from handlers.auth import generate_token
        token = generate_token(1, 'admin', 'hradmin', '系统')
        h0.headers = {'Authorization': 'Bearer ' + token}
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
        from handlers.auth import generate_token
        token = generate_token(2, 'user', 'employee', '技术部')
        h.headers = {'Authorization': 'Bearer ' + token}
        h._body = json.dumps({'current_password': 'admin123', 'new_password': 'NewP@ssw0rd!'})
        handle_admin_password(h)
        assert h.sent['code'] == 403
