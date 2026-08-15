"""
D3 导入测试：打卡 Excel 数据经 API 写入并查询确认、punch 清空、文件名去重、
schedule 需先有员工名册、员工名册同步、权限控制
"""
TEST_PORT = 18083

PUNCH_ROWS = [
    {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
     'date': '2026-07-01', 'period': '正常班', 'signIn': '08:25', 'signOut': '17:35',
     'scheduleStart': '08:30', 'scheduleEnd': '17:30'},
    {'employeeNo': 'T002', 'name': '李四', 'department': '技术部',
     'date': '2026-07-01', 'period': '正常班', 'signIn': '09:10', 'signOut': '17:40',
     'scheduleStart': '08:30', 'scheduleEnd': '17:30'},
]


def test_import_requires_auth(e2e_server):
    status, body = e2e_server.call('POST', '/api/attendance/import',
                                   {'type': 'punch', 'records': PUNCH_ROWS, 'file_name': 'p1.xlsx'})
    assert status == 401


def test_import_punch_writes_and_syncs_employees(e2e_server):
    client = e2e_server

    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'punch', 'records': PUNCH_ROWS, 'file_name': 'p1.xlsx'},
                               token=client.admin_token)
    assert status == 200
    assert body['code'] == 0
    assert body['data']['imported'] == 2

    status, body = client.call('GET', '/api/store/punch_records', token=client.admin_token)
    assert len(body['data']) == 2
    assert {r['employeeNo'] for r in body['data']} == {'T001', 'T002'}

    status, body = client.call('GET', '/api/store/employees', token=client.admin_token)
    assert len(body['data']) == 2
    assert {r['employeeNo'] for r in body['data']} == {'T001', 'T002'}


def test_import_punch_clears_previous_records(e2e_server):
    client = e2e_server
    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'punch', 'records': PUNCH_ROWS[:1], 'file_name': 'p2.xlsx'},
                               token=client.admin_token)
    assert body['code'] == 0
    assert body['data']['imported'] == 1

    status, body = client.call('GET', '/api/store/punch_records', token=client.admin_token)
    assert len(body['data']) == 1
    assert body['data'][0]['employeeNo'] == 'T001'


def test_import_duplicate_file_skipped(e2e_server):
    client = e2e_server
    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'punch', 'records': PUNCH_ROWS, 'file_name': 'p2.xlsx'},
                               token=client.admin_token)
    assert body['data']['skipped'] is True
    assert body['data']['imported'] == 0

    status, body = client.call('GET', '/api/store/punch_records', token=client.admin_token)
    assert len(body['data']) == 1


def test_import_schedule_requires_employees_first(e2e_server):
    client = e2e_server
    from database import get_db
    conn = get_db()
    conn.execute("DELETE FROM employees")
    conn.commit()
    conn.close()

    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'schedule',
                                'records': [{'year': 2026, 'month': 7, 'workDays': {'01': True}}],
                                'file_name': 's1.xlsx'},
                               token=client.admin_token)
    assert status == 400
    assert '名册' in body['message']


def test_import_schedule_after_punch(e2e_server):
    client = e2e_server
    # 上个用例清空了 employees，先重建名册
    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'punch', 'records': PUNCH_ROWS, 'file_name': 'p_rebuild.xlsx'},
                               token=client.admin_token)
    assert body['code'] == 0
    assert body['data']['imported'] == 2

    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'schedule',
                                'records': [
                                    {'year': 2026, 'month': 7, 'workDays': {'01': True, '02': False}},
                                    {'year': 2026, 'month': 8, 'workDays': {'01': True}},
                                ],
                                'file_name': 's2.xlsx'},
                               token=client.admin_token)
    assert status == 200
    assert body['data']['imported'] == 4  # 2 员工 x 2 月

    status, body = client.call('GET', '/api/store/schedules?index=year&value=2026', token=client.admin_token)
    assert len(body['data']) == 4
    july = [s for s in body['data'] if s['month'] == 7]
    assert len(july) == 2


def test_import_leave_and_query(e2e_server):
    client = e2e_server
    status, body = client.call('POST', '/api/attendance/import',
                               {'type': 'leave',
                                'records': [{'applicant': '张三', 'department': '技术部',
                                             'leaveType': '年假', 'startDate': '2026-07-03',
                                             'endDate': '2026-07-03', 'leaveDays': 1,
                                             'reason': '家事'}],
                                'file_name': 'l1.xlsx'},
                               token=client.admin_token)
    assert status == 200
    assert body['data']['imported'] == 1

    status, body = client.call('GET', '/api/store/leave_records', token=client.admin_token)
    assert len(body['data']) == 1
    assert body['data'][0]['applicant'] == '张三'
    assert body['data'][0]['leaveType'] == '年假'


def test_import_unknown_type_rejected(e2e_server):
    status, body = e2e_server.call('POST', '/api/attendance/import',
                                   {'type': 'bogus', 'records': [], 'file_name': 'x.xlsx'},
                                   token=e2e_server.admin_token)
    assert status == 400
