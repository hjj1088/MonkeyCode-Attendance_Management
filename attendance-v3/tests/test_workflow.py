"""
考勤工作流单元测试
"""
import os
import sys
import json
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    import database
    db_dir = os.path.join(tempfile.gettempdir(), 'attendance-v3-test-workflow')
    db_path = os.path.join(db_dir, 'attendance.db')
    monkeypatch.setattr(database, 'DB_DIR', db_dir)
    monkeypatch.setattr(database, 'DB_PATH', db_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_db()

    from handlers.auth import ensure_admin_user
    ensure_admin_user()

    yield db_path
    try:
        os.remove(db_path)
    except OSError:
        pass


class MockHandler:
    def __init__(self, token=None, body=None, path=''):
        from middleware import generate_token as _gen
        if token == 'admin':
            token = _gen(1, 'admin', 'hradmin', '')
        elif token == 'deptadmin':
            token = _gen(2, 'deptadmin', 'deptadmin', '技术部')
        elif token == 'employee':
            token = _gen(3, 'employee', 'employee', '技术部')
        self.token = token
        self.sent = None
        body_bytes = json.dumps(body).encode() if body else b''
        self.headers = {
            'Authorization': 'Bearer ' + token if token else '',
            'Content-Length': str(len(body_bytes)),
        }
        self._body = json.dumps(body) if body else None
        self.path = path
        self.rfile = type('obj', (object,), {'read': lambda s, n: body_bytes})()

    def _send_json(self, code, data=None, message=None):
        self.sent = {'code': code, 'data': data, 'message': message}

    def _read_body(self):
        if self._body:
            return json.loads(self._body)
        return {}


def _add_result(conn, result_id, review_status='pending_review', department='技术部', month='2026-07'):
    conn.execute(
        '''INSERT INTO attendance_results
           (id, employeeNo, name, department, date, month, status, review_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (result_id, 'T001', '张三', department, '2026-07-01', month, 'normal', review_status)
    )
    conn.commit()


class TestReviewStatusFlow:
    def test_pending_to_confirmed(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'pending_review')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='admin', body={'review_status': 'confirmed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 0
        assert handler.sent['data']['review_status'] == 'confirmed'
        assert handler.sent['data']['reviewed_by'] == 'admin'

    def test_confirmed_to_disputed(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'confirmed')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='admin', body={'review_status': 'disputed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 0
        assert handler.sent['data']['review_status'] == 'disputed'

    def test_disputed_back_to_confirmed(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'disputed')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='admin', body={'review_status': 'confirmed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 0
        assert handler.sent['data']['review_status'] == 'confirmed'

    def test_locked_cannot_be_changed(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'locked')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='admin', body={'review_status': 'disputed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 400
        assert '不允许' in handler.sent['message']

    def test_employee_cannot_review(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'pending_review')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='employee', body={'review_status': 'confirmed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 403

    def test_dept_submit_confirmed_records(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'confirmed', '技术部')
        _add_result(conn, 2, 'confirmed', '技术部')
        _add_result(conn, 3, 'pending_review', '技术部')
        conn.close()

        from handlers.attendance import handle_dept_submit
        handler = MockHandler(token='deptadmin', body={'month': '2026-07'})
        handle_dept_submit(handler)

        assert handler.sent['code'] == 0
        assert handler.sent['data']['submitted'] == 2

    def test_employee_cannot_submit_dept(self, setup_db):
        from handlers.attendance import handle_dept_submit
        handler = MockHandler(token='employee', body={'month': '2026-07'})
        handle_dept_submit(handler)

        assert handler.sent['code'] == 403

    def test_lock_only_submitted(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'submitted', '技术部')
        _add_result(conn, 2, 'pending_review', '技术部')
        conn.close()

        from handlers.attendance import handle_attendance_lock
        handler = MockHandler(token='admin', body={'month': '2026-07'})
        handle_attendance_lock(handler)

        assert handler.sent['code'] == 400
        assert '未提交' in handler.sent['message']

    def test_lock_submitted_records(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'submitted', '技术部')
        _add_result(conn, 2, 'submitted', '技术部')
        conn.close()

        from handlers.attendance import handle_attendance_lock
        handler = MockHandler(token='admin', body={'month': '2026-07'})
        handle_attendance_lock(handler)

        assert handler.sent['code'] == 0
        assert handler.sent['data']['locked'] == 2

    def test_non_hradmin_cannot_lock(self, setup_db):
        from handlers.attendance import handle_attendance_lock
        handler = MockHandler(token='deptadmin', body={'month': '2026-07'})
        handle_attendance_lock(handler)

        assert handler.sent['code'] == 403

    def test_summary_requires_hradmin(self, setup_db):
        from handlers.attendance import handle_attendance_summary
        handler = MockHandler(token='deptadmin', path='/api/attendance/summary?month=2026-07')
        handle_attendance_summary(handler)

        assert handler.sent['code'] == 403

    def test_summary_counts_by_department(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'confirmed', '技术部')
        _add_result(conn, 2, 'pending_review', '技术部')
        _add_result(conn, 3, 'submitted', '销售部')
        _add_result(conn, 4, 'locked', '销售部')
        conn.close()

        from handlers.attendance import handle_attendance_summary
        handler = MockHandler(token='admin', path='/api/attendance/summary?month=2026-07')
        handle_attendance_summary(handler)

        assert handler.sent['code'] == 0
        depts = handler.sent['data']['departments']
        assert len(depts) == 2
        for d in depts:
            if d['department'] == '技术部':
                assert d['confirmed'] == 1
                assert d['pending_review'] == 1
            if d['department'] == '销售部':
                assert d['submitted'] == 1
                assert d['locked'] == 1

    def test_review_requires_auth(self, setup_db):
        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token=None, body={'review_status': 'confirmed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 401

    def test_exists_pending_to_confirmed_allows(self, setup_db):
        import database
        conn = database.get_db()
        _add_result(conn, 1, 'pending_review')
        conn.close()

        from handlers.attendance import handle_attendance_review
        handler = MockHandler(token='deptadmin', body={'review_status': 'confirmed'}, path='/api/attendance/1/review')
        handle_attendance_review(handler, 1)

        assert handler.sent['code'] == 0
