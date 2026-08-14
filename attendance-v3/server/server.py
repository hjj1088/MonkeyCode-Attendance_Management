# V3.1 server.py
# REST API for V2.0 Store interface, backed by SQLite

import http.server
import json
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db, init_db

PORT = 8001

# Map tables whose primary key is not the autoincrement `id` column
# (mirrors V2.0 IndexedDB primary keys, keeps Store.getByKey/deleteByKey signature-compatible)
PRIMARY_KEYS = {
    'employees': 'employeeNo',
    'settings': 'key',
}


def json_serialize(val):
    """Convert row dict for JSON response -- deserialize JSON text fields."""
    if isinstance(val, dict):
        result = {}
        for k, v in val.items():
            if k in ('workDays', 'fields', 'sourcePunchIds', 'sourceLeaveIds',
                     'sourceTravelIds', 'sourceMissIds', 'sourceOvertimeIds', 'value'):
                try:
                    result[k] = json.loads(v) if isinstance(v, str) else v
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            elif k in ('isWorkday', 'isHoliday', 'isDefault', 'absent', 'isRestDay'):
                result[k] = bool(v) if v is not None else False
            else:
                result[k] = v
        return result
    return val


class APIHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def _send_json(self, code, **kwargs):
        self.send_response(200 if code == 0 else (code if code >= 400 else 400))
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.end_headers()
        self.wfile.write(json.dumps({'code': code, **kwargs}, ensure_ascii=False).encode())

    def _authenticate(self):
        from middleware import verify_token as verify_jwt
        auth = self.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        if not token:
            self._send_json(401, message='未提供认证令牌')
            return None
        payload = verify_jwt(token)
        if payload is None:
            self._send_json(401, message='令牌已过期或无效')
            return None
        return payload

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == '/api/auth/login-check':
            self._handle_login_check()
            return

        if path == '/api/system/version':
            from handlers.system import handle_system_version
            handle_system_version(self)
            return

        # V3.2 handlers (self-contained auth, mounted before /api/store/*)
        if path == '/api/system/status':
            from handlers.system import handle_system_status
            handle_system_status(self)
            return

        if path == '/api/system/check-default-password':
            from handlers.system import handle_check_default_password
            handle_check_default_password(self)
            return

        if path == '/api/system/config':
            from handlers.system import handle_system_config
            handle_system_config(self)
            return

        if path == '/api/rules/config':
            from handlers.rules import handle_rules_config_get
            handle_rules_config_get(self)
            return

        if path == '/api/rules/tolerance':
            from handlers.rules import handle_tolerance_get
            handle_tolerance_get(self)
            return

        if path == '/api/rules/holidays':
            from handlers.rules import handle_holidays_get
            handle_holidays_get(self)
            return

        if path == '/api/rules/work-schedule':
            from handlers.rules import handle_work_schedule_get
            handle_work_schedule_get(self)
            return

        if path == '/api/users':
            from handlers.users import handle_users_list
            handle_users_list(self)
            return

        if path.startswith('/api/users/'):
            from handlers.users import handle_users_list
            handle_users_list(self)
            return

        if path == '/api/attendance/my':
            from handlers.attendance import handle_attendance_my
            handle_attendance_my(self)
            return

        if path in ('/api/attendance/dept', '/api/attendance/all'):
            from handlers.attendance import handle_attendance_all
            handle_attendance_all(self)
            return

        if path == '/api/attendance/summary':
            from handlers.attendance import handle_attendance_summary
            handle_attendance_summary(self)
            return

        if path == '/api/attendance/leaves':
            from handlers.attendance import handle_leave_get
            handle_leave_get(self)
            return

        if path == '/api/attendance/travels':
            from handlers.attendance import handle_travel_get
            handle_travel_get(self)
            return

        if path == '/api/attendance/misses':
            from handlers.attendance import handle_miss_get
            handle_miss_get(self)
            return

        if path == '/api/attendance/overtime':
            from handlers.attendance import handle_overtime_all_get
            handle_overtime_all_get(self)
            return

        if path == '/api/attendance/data-month':
            from handlers.attendance import handle_data_month
            handle_data_month(self)
            return

        # GET /api/* paths require auth
        if path.startswith('/api/'):
            if not self._authenticate():
                return
            # GET /api/store/:table
            if path.startswith('/api/store/'):
                parts = path.split('/')
                if len(parts) == 4:
                    table = parts[3]
                    self._handle_store_get_all(table, params)
                    return
                elif len(parts) == 5 and parts[4] == 'range':
                    table = parts[3]
                    self._handle_store_get_range(table, params)
                    return
                elif len(parts) == 5:
                    table = parts[3]
                    key = parts[4]
                    self._handle_store_get_by_key(table, key)
                    return
            self._send_json(404, message='Not Found')
            return

        # Non-API paths → serve static files
        self._serve_static(path)

    def _serve_static(self, path):
        if path == '/' or path == '':
            path = '/index.html'
        client_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client')
        file_path = os.path.normpath(os.path.join(client_dir, path.lstrip('/')))
        if not file_path.startswith(os.path.normpath(client_dir)):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
            return
        if os.path.isfile(file_path):
            content_type_map = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.ico': 'image/x-icon',
            }
            ext = os.path.splitext(file_path)[1].lower()
            ct = content_type_map.get(ext, 'application/octet-stream')
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(302)
            self.send_header('Location', '/index.html')
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/auth/login':
            from handlers.auth import handle_login
            handle_login(self)
            return

        if path == '/api/auth/change-password':
            from handlers.auth import handle_change_password
            handle_change_password(self)
            return

        if path == '/api/users':
            from handlers.users import handle_users_create
            handle_users_create(self)
            return

        if path == '/api/users/reset-password':
            from handlers.users import handle_users_reset_password
            handle_users_reset_password(self)
            return

        if path == '/api/attendance/import':
            from handlers.attendance import handle_import
            handle_import(self)
            return

        if path == '/api/attendance/calculate':
            from handlers.attendance import handle_attendance_calculate
            handle_attendance_calculate(self)
            return

        if path == '/api/system/seed-test-data':
            from handlers.system import handle_seed_test_data
            handle_seed_test_data(self)
            return

        if path == '/api/system/reset-data':
            from handlers.system import handle_reset_data
            handle_reset_data(self)
            return

        if path == '/api/migrate':
            from handlers.migrate import handle_migrate
            handle_migrate(self)
            return

        if not self._authenticate():
            return

        # POST /api/store/:table
        if path.startswith('/api/store/'):
            parts = path.split('/')
            if len(parts) == 4:
                table = parts[3]
                self._handle_store_put(table)
                return
            elif len(parts) == 5 and parts[4] == 'bulk':
                table = parts[3]
                self._handle_store_bulk_put(table)
                return

        if path == '/api/store/reset':
            self._handle_reset_all()
            return

        if path == '/api/export/flat':
            self._handle_export_flat()
            return

        if path == '/api/export/calendar':
            self._handle_export_calendar()
            return

        self._send_json(404, message='Not Found')

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/users/reset-password':
            from handlers.users import handle_users_reset_password
            handle_users_reset_password(self)
            return

        import re
        m = re.match(r'/api/users/(\d+)/status$', path)
        if m:
            from handlers.users import handle_users_status
            self.path = '/api/users/' + m.group(1) + '/status'
            handle_users_status(self)
            return

        m = re.match(r'/api/attendance/(\d+)/review$', path)
        if m:
            from handlers.attendance import handle_attendance_review
            handle_attendance_review(self, int(m.group(1)))
            return

        if path == '/api/attendance/dept/submit':
            from handlers.attendance import handle_dept_submit
            handle_dept_submit(self)
            return

        if path == '/api/attendance/lock':
            from handlers.attendance import handle_attendance_lock
            handle_attendance_lock(self)
            return

        self._send_json(404, message='Not Found')

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        import re
        m = re.match(r'/api/users/(\d+)$', path)
        if m:
            from handlers.users import handle_users_update
            self.path = '/api/users/' + m.group(1)
            handle_users_update(self)
            return

        m = re.match(r'/api/users/(\d+)/status$', path)
        if m:
            from handlers.users import handle_users_status
            self.path = '/api/users/' + m.group(1) + '/status'
            handle_users_status(self)
            return

        if path == '/api/system/admin-password':
            from handlers.system import handle_admin_password
            handle_admin_password(self)
            return

        if path == '/api/system/config':
            from handlers.system import handle_system_config_update
            handle_system_config_update(self)
            return

        if path == '/api/rules/config':
            from handlers.rules import handle_rules_config_put
            handle_rules_config_put(self)
            return

        if path == '/api/rules/tolerance':
            from handlers.rules import handle_tolerance_put
            handle_tolerance_put(self)
            return

        if path == '/api/rules/holidays':
            from handlers.rules import handle_holidays_post
            handle_holidays_post(self)
            return

        self._send_json(404, message='Not Found')

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        import re
        m = re.match(r'/api/rules/holidays/(\d+)$', path)
        if m:
            from handlers.rules import handle_holidays_delete
            handle_holidays_delete(self)
            return

        if not self._authenticate():
            return

        if path.startswith('/api/store/'):
            parts = path.split('/')
            if len(parts) == 4:
                table = parts[3]
                self._handle_store_clear(table)
                return
            elif len(parts) == 5:
                table = parts[3]
                key = parts[4]
                self._handle_store_delete_by_key(table, key)
                return

        self._send_json(404, message='Not Found')

    # --- Auth ---

    def _handle_login_check(self):
        from middleware import verify_token as verify_jwt
        auth = self.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        if token and verify_jwt(token):
            self._send_json(0, data={'valid': True})
        else:
            self._send_json(401, message='令牌无效')

    # --- Store CRUD ---

    def _resolve_table(self, table):
        return {
            'punch': 'punch_records',
            'leave': 'leave_records',
            'overtime': 'overtime_records',
            'travel': 'travel_records',
            'miss_punch': 'miss_punch_records',
            'schedule': 'schedules',
        }.get(table, table)

    def _handle_store_get_all(self, table, params):
        table = self._resolve_table(table)
        conn = get_db()
        try:
            index_name = params.get('index', [None])[0]
            index_value = params.get('value', [None])[0]
            if index_name and index_value is not None:
                rows = conn.execute(
                    f'SELECT * FROM {table} WHERE "{index_name}" = ?',
                    (index_value,)
                ).fetchall()
            else:
                rows = conn.execute(f'SELECT * FROM {table}').fetchall()
            conn.close()
            self._send_json(0, data=[json_serialize(dict(r)) for r in rows])
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_get_range(self, table, params):
        table = self._resolve_table(table)
        conn = get_db()
        try:
            index_name = params.get('index', [''])[0]
            lower = params.get('lower', [''])[0]
            upper = params.get('upper', [''])[0]
            if not index_name:
                conn.close()
                self._send_json(400, message='Missing index parameter')
                return
            rows = conn.execute(
                f'SELECT * FROM {table} WHERE "{index_name}" >= ? AND "{index_name}" <= ?',
                (lower, upper)
            ).fetchall()
            conn.close()
            self._send_json(0, data=[json_serialize(dict(r)) for r in rows])
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_get_by_key(self, table, key):
        table = self._resolve_table(table)
        conn = get_db()
        try:
            pk = PRIMARY_KEYS.get(table, 'id')
            row = conn.execute(f'SELECT * FROM {table} WHERE "{pk}" = ?', (key,)).fetchone()
            conn.close()
            if row:
                self._send_json(0, data=json_serialize(dict(row)))
            else:
                self._send_json(0, data=None)
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_put(self, table):
        table = self._resolve_table(table)
        body = self._read_body()
        conn = get_db()
        try:
            record = body.get('record', body)
            clean = {}
            for k, v in record.items():
                if k in ('workDays', 'fields', 'sourcePunchIds', 'sourceLeaveIds',
                         'sourceTravelIds', 'sourceMissIds', 'sourceOvertimeIds', 'value'):
                    clean[k] = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                elif isinstance(v, bool):
                    clean[k] = 1 if v else 0
                else:
                    clean[k] = v

            if table == 'settings':
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (clean.get('key', ''), clean.get('value', ''))
                )
            else:
                if 'id' in clean and clean['id']:
                    # Update existing
                    cols = ', '.join(f'"{k}" = ?' for k in clean.keys())
                    vals = list(clean.values()) + [clean['id']]
                    conn.execute(f'UPDATE {table} SET {cols} WHERE id = ?', vals)
                else:
                    clean.pop('id', None)
                    cols = ', '.join(f'"{k}"' for k in clean.keys())
                    placeholders = ', '.join(['?'] * len(clean))
                    vals = list(clean.values())
                    conn.execute(f'INSERT INTO {table} ({cols}) VALUES ({placeholders})', vals)
            conn.commit()
            conn.close()
            self._send_json(0, data={'ok': True})
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_bulk_put(self, table):
        table = self._resolve_table(table)
        body = self._read_body()
        records = body.get('records', body if isinstance(body, list) else [])
        if not records:
            self._send_json(0, data={'count': 0})
            return
        conn = get_db()
        count = 0
        try:
            for record in records:
                clean = {}
                for k, v in record.items():
                    if k in ('workDays', 'fields', 'sourcePunchIds', 'sourceLeaveIds',
                             'sourceTravelIds', 'sourceMissIds', 'sourceOvertimeIds', 'value'):
                        clean[k] = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                    elif isinstance(v, bool):
                        clean[k] = 1 if v else 0
                    else:
                        clean[k] = v
                if table == 'settings':
                    conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (clean.get('key', ''), clean.get('value', ''))
                    )
                else:
                    clean.pop('id', None)
                    cols = ', '.join(f'"{k}"' for k in clean.keys())
                    placeholders = ', '.join(['?'] * len(clean))
                    vals = list(clean.values())
                    conn.execute(f'INSERT INTO {table} ({cols}) VALUES ({placeholders})', vals)
                count += 1
            conn.commit()
            conn.close()
            self._send_json(0, data={'count': count})
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_clear(self, table):
        table = self._resolve_table(table)
        conn = get_db()
        try:
            conn.execute(f'DELETE FROM {table}')
            conn.commit()
            conn.close()
            self._send_json(0, data={'ok': True})
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_store_delete_by_key(self, table, key):
        table = self._resolve_table(table)
        conn = get_db()
        try:
            pk = PRIMARY_KEYS.get(table, 'id')
            conn.execute(f'DELETE FROM {table} WHERE "{pk}" = ?', (key,))
            conn.commit()
            conn.close()
            self._send_json(0, data={'ok': True})
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    def _handle_reset_all(self):
        conn = get_db()
        try:
            tables = [
                'raw_files', 'punch_records', 'leave_records', 'overtime_records',
                'travel_records', 'miss_punch_records', 'schedules',
                'attendance_results', 'carry_over', 'holidays', 'settings',
                'export_templates', 'employees'
            ]
            for t in tables:
                conn.execute(f'DELETE FROM {t}')
            conn.commit()
            from database import _init_settings
            _init_settings(conn)
            conn.commit()
            conn.close()
            self._send_json(0, data={'ok': True})
        except Exception as e:
            conn.close()
            self._send_json(500, message=str(e))

    # --- Export ---

    def _handle_export_flat(self):
        body = self._read_body()
        try:
            from handlers.export import handle_export_flat
            handle_export_flat(self, body)
        except ImportError:
            self._send_json(500, message='导出模块未就绪')

    def _handle_export_calendar(self):
        body = self._read_body()
        try:
            from handlers.export import handle_export_calendar
            handle_export_calendar(self, body)
        except ImportError:
            self._send_json(500, message='导出模块未就绪')


def main():
    init_db()
    from handlers.auth import ensure_admin_user
    from handlers.system import set_start_time
    ensure_admin_user()
    set_start_time()
    server = http.server.HTTPServer(('0.0.0.0', PORT), APIHandler)
    print(f'[V3.2] Server running on port {PORT}')
    server.serve_forever()


if __name__ == '__main__':
    main()
