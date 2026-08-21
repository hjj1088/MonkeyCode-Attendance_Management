import json
from database import get_db
from middleware import verify_token


def _require_any_user(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return None
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return None
    return payload


TABLE_MAP = {
    'punch': 'punch_records',
    'leave': 'leave_records',
    'overtime': 'overtime_records',
    'travel': 'travel_records',
    'miss_punch': 'miss_punch_records',
    'schedule': 'schedules',
}

TABLE_COLUMNS = {
    'punch_records': [
        'employeeNo', 'customNo', 'name', 'department', 'date', 'period',
        'scheduleStart', 'scheduleEnd', 'signIn', 'signOut',
        'lateMinutes', 'earlyMinutes', 'absent', 'overtimeHours', 'workHours',
        'isWeekday', 'isWeekend', 'isHoliday', 'weekdayOT', 'weekendOT', 'holidayOT',
    ],
    'leave_records': [
        'applicant', 'department', 'leaveType', 'startDate',
        'endDate', 'leaveDays', 'leaveHours', 'reason',
    ],
    'overtime_records': [
        'applicant', 'department', 'startTime', 'endTime',
        'overtimeHours', 'content',
    ],
    'travel_records': [
        'applicant', 'department', 'startDate', 'endDate',
        'destination', 'reason', 'travelers', 'travelType',
    ],
    'miss_punch_records': [
        'applicant', 'department', 'missDate', 'missPerson',
        'missTime', 'cardTime', 'reason',
    ],
    'schedules': [
        'employeeNo', 'name', 'department', 'year', 'month',
        'workDays',
    ],
}


def _to_str(v):
    if v is None or v == '':
        return ''
    return str(v).strip()


def _sync_employees(conn, punch_records):
    existing = set()
    for row in conn.execute("SELECT employeeNo FROM employees").fetchall():
        existing.add(row['employeeNo'])
    seen = set()
    for r in punch_records:
        no = _to_str(r.get('employeeNo', r.get('employee_no', '')))
        if not no or no in seen:
            continue
        seen.add(no)
        name = _to_str(r.get('name', ''))
        dept = _to_str(r.get('department', ''))
        if no in existing:
            conn.execute(
                "UPDATE employees SET name = ?, department = ? WHERE employeeNo = ?",
                (name, dept, no)
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO employees (employeeNo, name, department) VALUES (?, ?, ?)",
                (no, name, dept)
            )


def handle_import(handler):
    payload = _require_any_user(handler)
    if payload is None:
        return

    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    file_type = body.get('type', '')
    records = body.get('records', [])
    file_name = body.get('file_name', '')

    if file_type not in TABLE_MAP:
        handler._send_json(400, message='不支持的文件类型: ' + file_type)
        return

    if not records or not isinstance(records, list):
        handler._send_json(400, message='没有有效的记录数据')
        return

    table = TABLE_MAP[file_type]
    columns = TABLE_COLUMNS.get(table, [])

    if not columns:
        handler._send_json(400, message='未知的表结构')
        return

    conn = get_db()
    try:
        if file_name:
            existing_file = conn.execute(
                "SELECT id FROM raw_files WHERE fileName = ?", (file_name,)
            ).fetchone()
            if existing_file:
                handler._send_json(0, data={'message': '文件已导入，跳过', 'imported': 0, 'total': len(records), 'type': file_type, 'skipped': True, 'errors': []})
                return

        if file_type == 'punch':
            conn.execute("DELETE FROM punch_records")

        if file_type == 'schedule':
            employees = conn.execute("SELECT employeeNo, name, department FROM employees").fetchall()
            if not employees:
                handler._send_json(400, message='请先导入打卡记录以建立员工名册')
                return

            conn.execute("DELETE FROM schedules")
            imported = 0
            for s in records:
                year = s.get('year')
                month = s.get('month')
                work_days = s.get('workDays', {})
                if not year or not month:
                    continue
                work_days_json = json.dumps(work_days, ensure_ascii=False)
                for emp in employees:
                    conn.execute(
                        "INSERT INTO schedules (employeeNo, name, department, year, month, workDays) VALUES (?, ?, ?, ?, ?, ?)",
                        (emp['employeeNo'], emp['name'], emp['department'], year, month, work_days_json)
                    )
                    imported += 1

            conn.execute(
                "INSERT INTO raw_files (fileName, fileType, recordCount, importTime) VALUES (?, ?, ?, datetime('now'))",
                (file_name, file_type, imported)
            )
            conn.commit()
            handler._send_json(0, data={
                'message': '排班导入成功',
                'imported': imported,
                'type': file_type,
                'detail': '{} 人 x {} 月 = {} 条'.format(len(employees), len(records), imported)
            })
            return

        imported = 0
        errors = []
        for rec in records:
            values = []
            for col in columns:
                val = rec.get(col, '')
                if val is None:
                    val = ''
                elif not isinstance(val, str):
                    val = str(val)
                values.append(val)

            placeholders = ', '.join(['?'] * len(columns))
            cols_str = ', '.join(columns)
            try:
                conn.execute(
                    'INSERT INTO {} ({}) VALUES ({})'.format(table, cols_str, placeholders),
                    values
                )
                imported += 1
            except Exception as e:
                errors.append('行 ' + str(len(errors) + 1) + ': ' + str(e))

        if file_type == 'punch':
            _sync_employees(conn, records)
            months = sorted({
                str(r.get('date', ''))[:7]
                for r in records
                if str(r.get('date', ''))[:7]
            })
            if months:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('last_punch_month', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (months[0],)
                )

        conn.execute(
            "INSERT INTO raw_files (fileName, fileType, recordCount, importTime) VALUES (?, ?, ?, datetime('now'))",
            (file_name, file_type, imported)
        )
        conn.commit()
        handler._send_json(0, data={'message': '导入成功', 'imported': imported, 'total': len(records), 'type': file_type, 'errors': errors})
    except Exception as e:
        import traceback
        traceback.print_exc()
        handler._send_json(500, message='导入失败: ' + str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def handle_attendance_my(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return

    import urllib.parse
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    username = payload.get('username', '')

    conn = get_db()
    user = conn.execute("SELECT name, department FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return
    employee_name = user['name']

    if month:
        rows = conn.execute(
            "SELECT * FROM attendance_results WHERE name = ? AND month = ? ORDER BY date",
            (employee_name, month)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM attendance_results WHERE name = ? ORDER BY date DESC",
            (employee_name,)
        ).fetchall()
    conn.close()
    results = [dict(r) for r in rows]
    handler._send_json(0, data=results)


def handle_attendance_all(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return

    role = payload.get('role', '')
    department = payload.get('department', '')

    if role == 'employee':
        handler._send_json(403, message='无权限查看全部数据')
        return

    import urllib.parse
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    filter_department = params.get('department', [None])[0]
    filter_status = params.get('status', [None])[0]
    filter_review = params.get('review', [None])[0]

    conn = get_db()
    conditions = []
    values = []

    if role == 'deptadmin':
        conditions.append('department = ?')
        values.append(department)
    elif role == 'hradmin':
        if filter_department:
            conditions.append('department = ?')
            values.append(filter_department)

    if month:
        conditions.append('month = ?')
        values.append(month)

    if filter_status:
        conditions.append('status = ?')
        values.append(filter_status)

    if filter_review:
        conditions.append('review_status = ?')
        values.append(filter_review)

    where = ''
    if conditions:
        where = ' WHERE ' + ' AND '.join(conditions)

    rows = conn.execute("SELECT * FROM attendance_results{} ORDER BY date, name".format(where), values).fetchall()
    conn.close()
    results = [dict(r) for r in rows]
    handler._send_json(0, data=results)


def handle_attendance_calculate(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return

    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    results = body.get('results', [])
    month = body.get('month', '')
    carry_over = body.get('carry_over', [])

    if not results or not month:
        handler._send_json(400, message='缺少考勤结果数据')
        return

    conn = get_db()
    conn.execute("DELETE FROM attendance_results WHERE month = ?", (month,))

    columns = [
        'employeeNo', 'name', 'department', 'date', 'month', 'status',
        'signIn', 'signOut', 'lateMinutes', 'earlyMinutes',
        'overtimeHours', 'travelHours', 'workHours', 'leaveType',
        'absent', 'leaveHours', 'isRestDay', 'period',
        'scheduleStart', 'scheduleEnd', 'missTime',
        'sourcePunchIds', 'sourceLeaveIds', 'sourceTravelIds',
        'sourceMissIds', 'sourceOvertimeIds',
    ]

    json_cols = {
        'sourcePunchIds', 'sourceLeaveIds', 'sourceTravelIds',
        'sourceMissIds', 'sourceOvertimeIds',
    }

    for r in results:
        values = []
        for col in columns:
            val = r.get(col, '')
            if val is None:
                val = ''
            if col in json_cols and not isinstance(val, str):
                val = json.dumps(val, ensure_ascii=False)
            if col == 'absent' and not isinstance(val, (int, str)):
                val = 1 if val else 0
            values.append(val)

        placeholders = ', '.join(['?'] * len(columns))
        cols_str = ', '.join(columns)
        conn.execute(
            "INSERT INTO attendance_results ({}) VALUES ({})".format(cols_str, placeholders),
            values
        )

    for co in (carry_over or []):
        conn.execute(
            "INSERT OR REPLACE INTO carry_over (employeeNo, name, month, overtimeBalance) VALUES (?, ?, ?, ?)",
            (co.get('employeeNo', ''), co.get('name', ''), co.get('month', month), co.get('overtimeBalance', co.get('overtime_balance', 0)))
        )

    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '考勤计算完成', 'saved': len(results)})


def handle_attendance_review(handler, result_id):
    payload = _require_any_user(handler)
    if payload is None:
        return
    role = payload.get('role', '')
    if role not in ('deptadmin', 'hradmin'):
        handler._send_json(403, message='无权限执行确认操作')
        return

    length = int(handler.headers.get('Content-Length', 0))
    body = json.loads(handler.rfile.read(length)) if length > 0 else {}
    new_status = body.get('review_status', 'confirmed')

    if new_status not in ('confirmed', 'disputed', 'pending_review'):
        handler._send_json(400, message='无效的 review_status：' + new_status)
        return

    conn = get_db()
    row = conn.execute(
        'SELECT id, review_status FROM attendance_results WHERE id = ?',
        (result_id,)
    ).fetchone()

    if not row:
        conn.close()
        handler._send_json(404, message='考勤记录不存在')
        return

    current_status = row['review_status']
    valid_transitions = {
        'pending_review': ('confirmed', 'disputed'),
        'confirmed': ('disputed',),
        'disputed': ('confirmed',),
        'submitted': (),
        'locked': (),
    }
    allowed = valid_transitions.get(current_status, ())
    if new_status not in allowed:
        conn.close()
        handler._send_json(400, message='当前状态 ' + current_status + ' 不允许变更为 ' + new_status)
        return

    reviewer = payload.get('username', '')
    conn.execute(
        'UPDATE attendance_results SET review_status = ?, reviewed_by = ?, reviewed_at = datetime("now") WHERE id = ?',
        (new_status, reviewer, result_id)
    )

    from database import log_operation
    log_operation(conn, reviewer, 'review', json.dumps({'target': 'attendance_result:' + str(result_id), 'from': current_status, 'to': new_status}, ensure_ascii=False))

    conn.commit()
    conn.close()
    handler._send_json(0, data={'id': result_id, 'review_status': new_status, 'reviewed_by': reviewer})


def handle_dept_submit(handler):
    payload = _require_any_user(handler)
    if payload is None:
        return
    role = payload.get('role', '')
    if role not in ('deptadmin', 'hradmin'):
        handler._send_json(403, message='无权限提交部门数据')
        return

    length = int(handler.headers.get('Content-Length', 0))
    body = json.loads(handler.rfile.read(length)) if length > 0 else {}
    month = body.get('month', '')
    department = payload.get('department', '')

    conn = get_db()
    if role == 'hradmin':
        result = conn.execute(
            "UPDATE attendance_results SET review_status = 'submitted' WHERE month = ? AND review_status = 'confirmed'",
            (month,)
        )
    else:
        result = conn.execute(
            "UPDATE attendance_results SET review_status = 'submitted' WHERE month = ? AND department = ? AND review_status = 'confirmed'",
            (month, department)
        )

    updated = result.rowcount

    from database import log_operation
    log_operation(conn, payload.get('username', ''), 'dept_submit',
                  json.dumps({'department': department, 'updated': updated, 'month': month}, ensure_ascii=False))

    conn.commit()
    conn.close()
    handler._send_json(0, data={'submitted': updated, 'month': month, 'department': department})


def handle_attendance_lock(handler):
    payload = _require_any_user(handler)
    if payload is None:
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='仅人事管理员可锁定数据')
        return

    length = int(handler.headers.get('Content-Length', 0))
    body = json.loads(handler.rfile.read(length)) if length > 0 else {}
    month = body.get('month', '')
    if not month:
        handler._send_json(400, message='month 参数必填')
        return

    conn = get_db()

    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM attendance_results WHERE month = ? AND review_status != 'submitted'",
        (month,)
    ).fetchone()['cnt']
    if count > 0:
        conn.close()
        handler._send_json(400, message='仍有 {} 条记录未提交，无法锁定'.format(count))
        return

    result = conn.execute(
        "UPDATE attendance_results SET review_status = 'locked' WHERE month = ? AND review_status = 'submitted'",
        (month,)
    )
    locked = result.rowcount

    from database import log_operation
    log_operation(conn, payload.get('username', ''), 'lock',
                  json.dumps({'locked': locked, 'month': month}, ensure_ascii=False))

    conn.commit()
    conn.close()
    handler._send_json(0, data={'locked': locked, 'month': month})


def handle_attendance_summary(handler):
    payload = _require_any_user(handler)
    if payload is None:
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='仅人事管理员可查看汇总')
        return

    parsed = __import__('urllib').parse.urlparse(handler.path)
    params = __import__('urllib').parse.parse_qs(parsed.query)
    month = params.get('month', [''])[0]

    conn = get_db()

    if month:
        rows = conn.execute(
            '''SELECT department, review_status, COUNT(*) as cnt
               FROM attendance_results WHERE month = ?
               GROUP BY department, review_status
               ORDER BY department, review_status''',
            (month,)
        ).fetchall()
    else:
        rows = conn.execute(
            '''SELECT department, month, review_status, COUNT(*) as cnt
               FROM attendance_results
               GROUP BY department, month, review_status
               ORDER BY month DESC, department, review_status'''
        ).fetchall()

    if month:
        summary = {}
        for r in rows:
            dept = r['department'] or '未知'
            st = r['review_status']
            if dept not in summary:
                summary[dept] = {'department': dept, 'pending_review': 0, 'confirmed': 0, 'submitted': 0, 'locked': 0, 'disputed': 0}
            summary[dept][st] = r['cnt']

        total = conn.execute(
            'SELECT COUNT(*) as cnt FROM attendance_results WHERE month = ?', (month,)
        ).fetchone()['cnt']
        conn.close()
        handler._send_json(0, data={'month': month, 'departments': list(summary.values()), 'total': total})
    else:
        conn.close()
        handler._send_json(0, data={'months': [dict(r) for r in rows]})


def handle_leave_get(handler):
    import urllib.parse
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌'); return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期'); return
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    conn = get_db()
    if month:
        rows = conn.execute(
            "SELECT * FROM leave_records WHERE strftime('%Y-%m', startDate) = ? OR strftime('%Y-%m', endDate) = ? ORDER BY id",
            (month, month)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM leave_records ORDER BY id").fetchall()
    conn.close()
    handler._send_json(0, data=[dict(r) for r in rows])


def handle_travel_get(handler):
    import urllib.parse
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌'); return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期'); return
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    conn = get_db()
    if month:
        rows = conn.execute(
            "SELECT * FROM travel_records WHERE strftime('%Y-%m', startDate) = ? OR strftime('%Y-%m', endDate) = ? ORDER BY id",
            (month, month)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM travel_records ORDER BY id").fetchall()
    conn.close()
    handler._send_json(0, data=[dict(r) for r in rows])


def handle_miss_get(handler):
    import urllib.parse
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌'); return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期'); return
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    month = params.get('month', [None])[0]
    conn = get_db()
    if month:
        rows = conn.execute(
            "SELECT * FROM miss_punch_records WHERE strftime('%Y-%m', missDate) = ? ORDER BY id",
            (month,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM miss_punch_records ORDER BY id").fetchall()
    conn.close()
    handler._send_json(0, data=[dict(r) for r in rows])


def handle_overtime_all_get(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌'); return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期'); return
    conn = get_db()
    rows = conn.execute("SELECT * FROM overtime_records ORDER BY id").fetchall()
    conn.close()
    handler._send_json(0, data=[dict(r) for r in rows])


def handle_data_month(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌'); return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期'); return
    conn = get_db()
    row = conn.execute("SELECT date FROM punch_records ORDER BY date DESC LIMIT 1").fetchone()
    conn.close()
    if row and row['date']:
        m = row['date'][:7]
        handler._send_json(0, data={'month': m})
    else:
        from datetime import datetime
        handler._send_json(0, data={'month': datetime.now().strftime('%Y-%m')})
