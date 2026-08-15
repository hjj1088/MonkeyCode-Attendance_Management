"""
D3 迁移测试：V2.0 JSON 迁移后数据完整性 + 失败回滚 + 权限
"""
TEST_PORT = 18084

V20_DATA = {
    'employee': [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部'},
        {'employeeNo': 'T002', 'name': '李四', 'department': '技术部'},
    ],
    'punch': [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
         'date': '2026-06-01', 'signIn': '08:20', 'signOut': '17:40',
         'scheduleStart': '08:30', 'scheduleEnd': '17:30',
         'lateMinutes': 0, 'earlyMinutes': 0, 'overtimeHours': 0, 'absent': 0, 'workHours': 9.3},
    ],
    'leave': [
        {'applicant': '张三', 'department': '技术部', 'leaveType': '事假',
         'startDate': '2026-06-02', 'endDate': '2026-06-02', 'leaveDays': 1,
         'leaveHours': 0, 'reason': '私事'},
    ],
    'schedule': [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
         'year': 2026, 'month': 6, 'workDays': {'01': True, '02': False}},
    ],
    'holiday': [
        {'date': '2026-10-01', 'name': '国庆节', 'isWorkday': 0, 'isHoliday': 1},
    ],
    'settings': {
        'company_name': '测试公司',
        'attendance_config': {
            'workStartTime': '09:00', 'workEndTime': '18:00',
            'lateThreshold': 5, 'earlyThreshold': 5,
            'graceTimes': 3, 'graceMinutes': 40,
        },
    },
    'attendance_results': [
        {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
         'date': '2026-06-01', 'month': '2026-06', 'status': 'normal',
         'signIn': '08:20', 'signOut': '17:40', 'lateMinutes': 0, 'earlyMinutes': 0,
         'overtimeHours': 0, 'travelHours': 0, 'workHours': 9.3,
         'absent': 0, 'isRestDay': 0, 'leaveType': '', 'leaveHours': 0,
         'sourcePunchIds': [1, 2]},
    ],
    'carry_over': [
        {'employeeNo': 'T001', 'name': '张三', 'month': '2026-06', 'overtimeBalance': 5},
    ],
}


def test_migrate_requires_hradmin(e2e_server):
    client = e2e_server
    emp_token = client.login('zhangsan', '123456')
    if not emp_token:
        client.call('POST', '/api/users', {
            'username': 'zhangsan', 'name': '张三', 'department': '技术部',
            'role': 'employee', 'password': '123456',
        }, token=client.admin_token)
        emp_token = client.login('zhangsan', '123456')

    status, body = client.call('POST', '/api/migrate', V20_DATA, token=emp_token)
    assert status == 403


def test_migrate_requires_auth(e2e_server):
    status, body = e2e_server.call('POST', '/api/migrate', V20_DATA)
    assert status == 401


def test_migrate_preserves_data_integrity(e2e_server):
    client = e2e_server
    status, body = client.call('POST', '/api/migrate', V20_DATA, token=client.admin_token)
    assert status == 200
    assert body['code'] == 0
    report = body['data']
    assert report['tables']['employees']['imported'] == 2
    assert report['tables']['punch_records']['imported'] == 1
    assert report['tables']['leave_records']['imported'] == 1
    assert report['tables']['schedules']['imported'] == 1
    assert report['tables']['holidays']['imported'] == 1
    assert report['tables']['attendance_results']['imported'] == 1
    assert report['tables']['carry_over']['imported'] == 1
    assert report['tables']['settings']['imported'] == 2

    status, body = client.call('GET', '/api/store/punch_records', token=client.admin_token)
    assert len(body['data']) == 1
    assert body['data'][0]['signIn'] == '08:20'

    status, body = client.call('GET', '/api/store/employees', token=client.admin_token)
    assert len(body['data']) == 2

    status, body = client.call('GET', '/api/store/attendance_results', token=client.admin_token)
    row = body['data'][0]
    assert row['status'] == 'normal'
    assert row['sourcePunchIds'] == [1, 2]

    status, body = client.call('GET', '/api/store/settings/attendance_config', token=client.admin_token)
    # 后端 json_serialize 已把 value 反序列化为对象
    assert body['data']['value']['workStartTime'] == '09:00'
    assert body['data']['value']['graceTimes'] == 3


def test_migrate_failure_rolls_back(e2e_server):
    client = e2e_server
    # malformed body triggers an uncaught exception inside migration -> rollback
    bad_data = {'punch': 12345}
    status, body = client.call('POST', '/api/migrate', bad_data, token=client.admin_token)
    assert status == 200
    assert any('已回滚' in e for e in body['data']['errors'])

    status, body = client.call('GET', '/api/store/punch_records', token=client.admin_token)
    assert len(body['data']) == 1  # unchanged from previous test
