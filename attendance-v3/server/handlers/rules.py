import json
from database import get_db
from middleware import verify_token

# V3.2 rules.py
# 与 V3.1 前端契约对齐：考勤规则 + 容错规则均存放在 settings.attendance_config 单键
# 字段 camelCase，与 V3.1 Store.getByKey('settings','attendance_config').value 一致。

DEFAULT_CONFIG = {
    'workStartTime': '08:30',
    'workEndTime': '17:30',
    'lateThreshold': 0,
    'earlyThreshold': 0,
    'graceTimes': 2,
    'graceMinutes': 30,
}


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


def _get_config(conn):
    row = conn.execute("SELECT value FROM settings WHERE key = 'attendance_config'").fetchone()
    if not row:
        return dict(DEFAULT_CONFIG)
    try:
        cfg = json.loads(row['value'])
        if not isinstance(cfg, dict):
            return dict(DEFAULT_CONFIG)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except (json.JSONDecodeError, TypeError):
        return dict(DEFAULT_CONFIG)


def _set_config(conn, cfg):
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('attendance_config', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(cfg, ensure_ascii=False),)
    )


def handle_rules_config_get(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    cfg = _get_config(conn)
    conn.close()
    handler._send_json(0, data={
        'workStartTime': cfg.get('workStartTime', '08:30'),
        'workEndTime': cfg.get('workEndTime', '17:30'),
        'lateThreshold': cfg.get('lateThreshold', 0),
        'earlyThreshold': cfg.get('earlyThreshold', 0),
    })


def handle_rules_config_put(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    conn = get_db()
    cfg = _get_config(conn)
    for key in ('workStartTime', 'workEndTime', 'lateThreshold', 'earlyThreshold'):
        if key in body:
            cfg[key] = body[key]
    _set_config(conn, cfg)
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '考勤规则已更新'})


def handle_tolerance_get(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    cfg = _get_config(conn)
    conn.close()
    handler._send_json(0, data={
        'graceTimes': cfg.get('graceTimes', 2),
        'graceMinutes': cfg.get('graceMinutes', 30),
    })


def handle_tolerance_put(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    conn = get_db()
    cfg = _get_config(conn)
    for key in ('graceTimes', 'graceMinutes'):
        if key in body:
            cfg[key] = body[key]
    _set_config(conn, cfg)
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
    is_workday = body.get('is_workday', body.get('isWorkday', 0))

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
            "INSERT INTO holidays (date, name, isWorkday, isHoliday) VALUES (?, ?, ?, ?)",
            (date_str, name, 1 if is_workday else 0, 0 if is_workday else 1)
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

    cfg = _get_config(conn)
    conn.close()

    result = []
    for r in rows:
        work_days = r['workDays']
        if isinstance(work_days, str):
            try:
                work_days = json.loads(work_days)
            except (json.JSONDecodeError, TypeError):
                work_days = {}
        result.append({
            'id': r['id'],
            'employeeNo': r['employeeNo'],
            'name': r['name'],
            'department': r['department'],
            'year': r['year'],
            'month': r['month'],
            'workDays': work_days,
            'workStartTime': cfg.get('workStartTime', '08:30'),
            'workEndTime': cfg.get('workEndTime', '17:30'),
        })
    handler._send_json(0, data=result)
