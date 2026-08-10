import json
from datetime import datetime, timedelta
from database import get_db
from middleware import verify_token


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


def _get_setting(conn, key):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row['value'] if row else None


def _set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value)
    )


def handle_rules_config_get(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    config = {
        'work_start_time': _get_setting(conn, 'work_start_time') or '08:30',
        'work_end_time': _get_setting(conn, 'work_end_time') or '17:30',
        'late_threshold': _get_setting(conn, 'late_threshold') or '0',
        'early_threshold': _get_setting(conn, 'early_threshold') or '0',
        'overtime_multiplier': _get_setting(conn, 'overtime_multiplier') or '1.5',
    }
    conn.close()
    handler._send_json(0, data=config)


def handle_rules_config_put(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    conn = get_db()
    for key in ('work_start_time', 'work_end_time', 'late_threshold', 'early_threshold', 'overtime_multiplier'):
        if key in body:
            _set_setting(conn, key, str(body[key]))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '考勤规则已更新'})


def handle_tolerance_get(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    config = {
        'tolerance_count': _get_setting(conn, 'tolerance_count') or '2',
        'tolerance_minutes': _get_setting(conn, 'tolerance_minutes') or '30',
    }
    conn.close()
    handler._send_json(0, data=config)


def handle_tolerance_put(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    conn = get_db()
    for key in ('tolerance_count', 'tolerance_minutes'):
        if key in body:
            _set_setting(conn, key, str(body[key]))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '容错规则已更新'})


def handle_holidays_get(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    year = None
    parsed = __import__('urllib.parse', fromlist=['parse']).urlparse(handler.path)
    params = __import__('urllib.parse', fromlist=['parse_query']).parse_qs(parsed.query)
    if 'year' in params:
        year = params['year'][0]
    if year:
        rows = conn.execute(
            "SELECT * FROM holidays WHERE strftime('%Y', date) = ? ORDER BY date",
            (year,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM holidays ORDER BY date").fetchall()
    conn.close()
    holidays = [dict(r) for r in rows]
    handler._send_json(0, data=holidays)


def handle_holidays_post(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    dates = body.get('dates', [])
    name = body.get('name', '')
    is_workday = body.get('is_workday', 0)

    if not dates or not name:
        handler._send_json(400, message='缺少必要参数')
        return

    conn = get_db()
    count = 0
    for date_str in dates:
        existing = conn.execute("SELECT id FROM holidays WHERE date = ?", (date_str,)).fetchone()
        if existing:
            continue
        conn.execute(
            "INSERT INTO holidays (date, name, is_workday, is_holiday) VALUES (?, ?, ?, ?)",
            (date_str, name, is_workday, 0 if is_workday else 1)
        )
        count += 1
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '已添加 {} 条假期'.format(count), 'added': count})


def handle_holidays_delete(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    import re
    match = re.match(r'/api/rules/holidays/(\d+)', handler.path)
    if not match:
        handler._send_json(400, message='无效的假期ID')
        return
    holiday_id = int(match.group(1))
    conn = get_db()
    conn.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '假期已删除'})


def handle_work_schedule_get(handler):
    import urllib.parse
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    conn = get_db()
    rows = []
    if month and '-' in month:
        year, mon = month.split('-')
        rows = conn.execute(
            "SELECT * FROM schedules WHERE year = ? AND month = ?",
            (int(year), int(mon))
        ).fetchall()
    elif month:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE month LIKE ?",
            (month + '%',)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM schedules").fetchall()

    ws_row = conn.execute("SELECT value FROM settings WHERE key = 'work_start_time'").fetchone()
    we_row = conn.execute("SELECT value FROM settings WHERE key = 'work_end_time'").fetchone()
    default_ws = ws_row['value'] if ws_row else '08:30'
    default_we = we_row['value'] if we_row else '17:30'
    conn.close()

    result = []
    for r in rows:
        work_days = r['work_days']
        if isinstance(work_days, str):
            try:
                work_days = json.loads(work_days)
            except (json.JSONDecodeError, TypeError):
                work_days = {}
        result.append({
            'id': r['id'],
            'employee_no': r['employee_no'],
            'name': r['name'],
            'department': r['department'],
            'year': r['year'],
            'month': r['month'],
            'work_days': work_days,
            'work_start_time': default_ws,
            'work_end_time': default_we,
        })
    handler._send_json(0, data=result)
