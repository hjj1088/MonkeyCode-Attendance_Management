import json
from database import get_db
from middleware import verify_token


def handle_migrate(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='仅人事管理员可执行迁移')
        return

    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    report = {'tables': {}, 'errors': []}
    conn = get_db()

    try:
        _migrate_records(conn, body, report)
    except Exception as e:
        conn.rollback()
        report['errors'].append('迁移失败，已回滚: ' + str(e))
    else:
        conn.commit()

    conn.close()
    handler._send_json(0, data=report)


def _migrate_records(conn, data, report):
    mappings = [
        ('punch_records', 'punch', {
            'employeeNo': 'employeeNo', 'name': 'name', 'department': 'department',
            'date': 'date', 'period': 'period', 'signIn': 'signIn', 'signOut': 'signOut',
            'lateMinutes': 'lateMinutes', 'earlyMinutes': 'earlyMinutes',
            'overtimeHours': 'overtimeHours', 'scheduleStart': 'scheduleStart',
            'scheduleEnd': 'scheduleEnd', 'absent': 'absent', 'workHours': 'workHours',
        }),
        ('leave_records', 'leave', {
            'applicant': 'applicant', 'department': 'department', 'leaveType': 'leaveType',
            'startDate': 'startDate', 'endDate': 'endDate',
            'leaveDays': 'leaveDays', 'leaveHours': 'leaveHours', 'reason': 'reason',
        }),
        ('overtime_records', 'overtime', {
            'applicant': 'applicant', 'department': 'department',
            'overtimeHours': 'overtimeHours', 'content': 'content',
            'startTime': 'startTime', 'endTime': 'endTime',
        }),
        ('travel_records', 'travel', {
            'applicant': 'applicant', 'department': 'department', 'destination': 'destination',
            'startDate': 'startDate', 'endDate': 'endDate', 'reason': 'reason',
            'travelers': 'travelers', 'travelType': 'travelType',
        }),
        ('miss_punch_records', 'miss_punch', {
            'applicant': 'applicant', 'department': 'department',
            'missDate': 'missDate', 'reason': 'reason',
            'missPerson': 'missPerson', 'missTime': 'missTime', 'cardTime': 'cardTime',
        }),
        ('schedules', 'schedule', {
            'employeeNo': 'employeeNo', 'name': 'name', 'department': 'department',
            'year': 'year', 'month': 'month', 'workDays': 'workDays',
        }),
        ('employees', 'employee', {
            'employeeNo': 'employeeNo', 'name': 'name', 'department': 'department',
        }),
        ('holidays', 'holiday', {
            'date': 'date', 'name': 'name', 'isWorkday': 'isWorkday', 'isHoliday': 'isHoliday',
        }),
    ]

    for table, key, field_map in mappings:
        if key not in data or not data[key]:
            report['tables'][table] = {'imported': 0, 'skipped': 0}
            continue

        src = data[key]
        imported = 0
        skipped = 0
        for row in src:
            try:
                mapped = {}
                for dst_field, src_field in field_map.items():
                    val = row.get(src_field)
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val, ensure_ascii=False)
                    mapped[dst_field] = val

                cols = ', '.join(mapped.keys())
                placeholders = ', '.join(['?'] * len(mapped))
                conn.execute(
                    'INSERT OR IGNORE INTO {}({}) VALUES ({})'.format(table, cols, placeholders),
                    list(mapped.values())
                )
                imported += 1
            except Exception as e:
                skipped += 1
                report['errors'].append('{} 第{}条: {}'.format(table, imported + skipped + 1, str(e)))

        report['tables'][table] = {'imported': imported, 'skipped': skipped}

    # Migrate attendance_results if present
    if 'attendance_results' in data and data['attendance_results']:
        results = data['attendance_results']
        imported = 0
        skipped = 0
        for row in results:
            try:
                mapped = {
                    'employeeNo': row.get('employeeNo', ''),
                    'name': row.get('name', ''),
                    'department': row.get('department', ''),
                    'date': row.get('date', ''),
                    'month': row.get('month', ''),
                    'status': row.get('status', ''),
                    'signIn': row.get('signIn', ''),
                    'signOut': row.get('signOut', ''),
                    'lateMinutes': row.get('lateMinutes', 0),
                    'earlyMinutes': row.get('earlyMinutes', 0),
                    'overtimeHours': row.get('overtimeHours', 0),
                    'travelHours': row.get('travelHours', 0),
                    'workHours': row.get('workHours', 0),
                    'leaveType': row.get('leaveType', ''),
                    'leaveHours': row.get('leaveHours', 0),
                    'absent': 1 if row.get('absent') else 0,
                    'isRestDay': 1 if row.get('isRestDay') else 0,
                }
                if row.get('sourcePunchIds'):
                    mapped['sourcePunchIds'] = json.dumps(row['sourcePunchIds'], ensure_ascii=False)
                if row.get('sourceLeaveIds'):
                    mapped['sourceLeaveIds'] = json.dumps(row['sourceLeaveIds'], ensure_ascii=False)
                if row.get('sourceTravelIds'):
                    mapped['sourceTravelIds'] = json.dumps(row['sourceTravelIds'], ensure_ascii=False)
                if row.get('sourceMissIds'):
                    mapped['sourceMissIds'] = json.dumps(row['sourceMissIds'], ensure_ascii=False)
                if row.get('sourceOvertimeIds'):
                    mapped['sourceOvertimeIds'] = json.dumps(row['sourceOvertimeIds'], ensure_ascii=False)

                cols = ', '.join(mapped.keys())
                placeholders = ', '.join(['?'] * len(mapped))
                conn.execute(
                    'INSERT OR IGNORE INTO attendance_results({}) VALUES ({})'.format(cols, placeholders),
                    list(mapped.values())
                )
                imported += 1
            except Exception as e:
                skipped += 1
                report['errors'].append('attendance_results 第{}条: {}'.format(imported + skipped + 1, str(e)))
        report['tables']['attendance_results'] = {'imported': imported, 'skipped': skipped}

    # Migrate carry_over
    if 'carry_over' in data and data['carry_over']:
        imported = 0
        skipped = 0
        for row in data['carry_over']:
            try:
                conn.execute(
                    'INSERT OR REPLACE INTO carry_over(employeeNo, name, month, overtimeBalance) VALUES (?, ?, ?, ?)',
                    (row.get('employeeNo', ''), row.get('name', ''), row.get('month', ''), row.get('overtimeBalance', 0))
                )
                imported += 1
            except Exception as e:
                skipped += 1
                report['errors'].append('carry_over 第{}条: {}'.format(imported + skipped + 1, str(e)))
        report['tables']['carry_over'] = {'imported': imported, 'skipped': skipped}

    # Migrate settings
    if 'settings' in data and data['settings']:
        imported = 0
        for key, val in data['settings'].items():
            try:
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)
                conn.execute(
                    'INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)',
                    (key, str(val))
                )
                imported += 1
            except Exception:
                pass
        report['tables']['settings'] = {'imported': imported, 'skipped': 0}
