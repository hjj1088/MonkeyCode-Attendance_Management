"""
考勤规则配置单元测试
"""
import os
import sys
import json
import pytest
import tempfile
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

pytestmark = pytest.mark.skip(reason='V3.2: rules/holidays handlers not mounted in V3.1')


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
    database.init_system()
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
        self.path = '/api/rules/holidays'

    def _send_json(self, code, data=None, message=None):
        self.sent = {'code': code, 'data': data, 'message': message}

    def _read_body(self):
        return json.loads(self._body) if self._body else None


def make_hradmin_handler():
    from handlers.auth import generate_token
    h = MockHandler()
    token = generate_token(1, 'admin', 'hradmin', '系统')
    h.headers = {'Authorization': 'Bearer ' + token}
    return h


def make_employee_handler():
    from handlers.auth import generate_token
    h = MockHandler()
    token = generate_token(2, 'emp01', 'employee', '技术部')
    h.headers = {'Authorization': 'Bearer ' + token}
    return h


class TestRulesConfig:
    def test_get_config_defaults(self):
        h = make_hradmin_handler()
        from handlers.rules import handle_rules_config_get
        handle_rules_config_get(h)
        assert h.sent['code'] == 0
        assert h.sent['data']['work_start_time'] == '08:30'
        assert h.sent['data']['work_end_time'] == '17:30'

    def test_update_config(self):
        from handlers.rules import handle_rules_config_put, handle_rules_config_get
        h = make_hradmin_handler()
        h._body = json.dumps({'late_threshold': '15', 'early_threshold': '10'})
        handle_rules_config_put(h)
        assert h.sent['code'] == 0

        h2 = make_hradmin_handler()
        handle_rules_config_get(h2)
        assert h2.sent['data']['late_threshold'] == '15'
        assert h2.sent['data']['early_threshold'] == '10'

    def test_employee_cannot_access(self):
        h = make_employee_handler()
        from handlers.rules import handle_rules_config_get
        handle_rules_config_get(h)
        assert h.sent['code'] == 403

    def test_no_token_rejected(self):
        h = MockHandler()
        from handlers.rules import handle_rules_config_get
        handle_rules_config_get(h)
        assert h.sent['code'] == 401


class TestToleranceConfig:
    def test_get_defaults(self):
        h = make_hradmin_handler()
        from handlers.rules import handle_tolerance_get
        handle_tolerance_get(h)
        assert h.sent['code'] == 0
        assert h.sent['data']['tolerance_count'] == '2'
        assert h.sent['data']['tolerance_minutes'] == '30'

    def test_update_tolerance(self):
        from handlers.rules import handle_tolerance_put, handle_tolerance_get
        h = make_hradmin_handler()
        h._body = json.dumps({'tolerance_count': '5', 'tolerance_minutes': '60'})
        handle_tolerance_put(h)
        assert h.sent['code'] == 0

        h2 = make_hradmin_handler()
        handle_tolerance_get(h2)
        assert h2.sent['data']['tolerance_count'] == '5'
        assert h2.sent['data']['tolerance_minutes'] == '60'


class TestHolidays:
    def test_get_holidays_empty(self):
        h = make_hradmin_handler()
        from handlers.rules import handle_holidays_get
        handle_holidays_get(h)
        assert h.sent['code'] == 0
        assert h.sent['data'] == []

    def test_add_holidays(self):
        from handlers.rules import handle_holidays_post, handle_holidays_get
        h = make_hradmin_handler()
        h._body = json.dumps({
            'dates': ['2026-10-01', '2026-10-02', '2026-10-03'],
            'name': '国庆节',
            'is_workday': 0,
        })
        handle_holidays_post(h)
        assert h.sent['code'] == 0
        assert h.sent['data']['added'] == 3

        h2 = make_hradmin_handler()
        handle_holidays_get(h2)
        assert len(h2.sent['data']) == 3

    def test_duplicate_date_skipped(self):
        from handlers.rules import handle_holidays_post
        h = make_hradmin_handler()
        h._body = json.dumps({'dates': ['2026-10-01'], 'name': '国庆', 'is_workday': 0})
        handle_holidays_post(h)
        assert h.sent['data']['added'] == 1

        h2 = make_hradmin_handler()
        h2._body = json.dumps({'dates': ['2026-10-01'], 'name': '国庆', 'is_workday': 0})
        handle_holidays_post(h2)
        assert h2.sent['data']['added'] == 0

    def test_workday_holiday(self):
        from handlers.rules import handle_holidays_post, handle_holidays_get
        h = make_hradmin_handler()
        h._body = json.dumps({'dates': ['2026-09-27'], 'name': '调休上班', 'is_workday': 1})
        handle_holidays_post(h)
        assert h.sent['code'] == 0

        h2 = make_hradmin_handler()
        handle_holidays_get(h2)
        holiday = h2.sent['data'][0]
        assert holiday['is_workday'] == 1
        assert holiday['is_holiday'] == 0

    def test_delete_holiday(self):
        from handlers.rules import handle_holidays_post, handle_holidays_get, handle_holidays_delete
        h = make_hradmin_handler()
        h._body = json.dumps({'dates': ['2026-05-01'], 'name': '劳动节', 'is_workday': 0})
        handle_holidays_post(h)
        assert h.sent['data']['added'] == 1

        h2 = make_hradmin_handler()
        handle_holidays_get(h2)
        holiday_id = h2.sent['data'][0]['id']

        h3 = make_hradmin_handler()
        h3.path = '/api/rules/holidays/' + str(holiday_id)
        handle_holidays_delete(h3)
        assert h3.sent['code'] == 0

        h4 = make_hradmin_handler()
        handle_holidays_get(h4)
        assert len(h4.sent['data']) == 0

    def test_year_filter(self):
        from handlers.rules import handle_holidays_post, handle_holidays_get
        h0 = make_hradmin_handler()
        h0._body = json.dumps({'dates': ['2025-05-01'], 'name': '劳动节2025', 'is_workday': 0})
        handle_holidays_post(h0)

        h1 = make_hradmin_handler()
        h1._body = json.dumps({'dates': ['2026-05-01'], 'name': '劳动节2026', 'is_workday': 0})
        handle_holidays_post(h1)

        h_get = make_hradmin_handler()
        h_get.path = '/api/rules/holidays?year=2026'
        handle_holidays_get(h_get)
        assert len(h_get.sent['data']) == 1
        assert h_get.sent['data'][0]['name'] == '劳动节2026'
