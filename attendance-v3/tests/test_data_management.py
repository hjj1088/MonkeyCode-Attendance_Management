"""
D3 数据管理测试：seed 后各表数量、reset 后业务表清空而 users/settings 保留
"""
TEST_PORT = 18082


def _create_employee(client, username='emp001'):
    status, body = client.call('POST', '/api/users', {
        'username': username, 'name': '测试员工', 'department': '技术部',
        'role': 'employee', 'password': '123456',
    }, token=client.admin_token)
    assert status == 200
    return body['data']


def test_seed_creates_test_data(e2e_server):
    client = e2e_server
    assert client.admin_token

    status, body = client.call('POST', '/api/system/seed-test-data', token=client.admin_token)
    assert status == 200
    assert body['code'] == 0

    status, body = client.call('GET', '/api/users', token=client.admin_token)
    usernames = [u['username'] for u in body['data']]
    assert '技001' in usernames and 'dept_技' in usernames
    assert sum(1 for u in body['data'] if u['role'] == 'employee') >= 15

    # seed 生成：用户、打卡、请假
    for table in ('punch_records', 'leave_records'):
        status, body = client.call('GET', '/api/store/' + table, token=client.admin_token)
        assert len(body['data']) > 0, table


def test_seed_does_not_duplicate_users(e2e_server):
    client = e2e_server
    status, body = client.call('GET', '/api/users', token=client.admin_token)
    count_before = len(body['data'])

    status, body = client.call('POST', '/api/system/seed-test-data', token=client.admin_token)
    assert body['code'] == 0

    status, body = client.call('GET', '/api/users', token=client.admin_token)
    assert len(body['data']) == count_before


def test_reset_clears_business_tables_keeps_users_settings(e2e_server):
    client = e2e_server
    status, body = client.call('POST', '/api/system/reset-data', token=client.admin_token)
    assert status == 200

    status, body = client.call('GET', '/api/users', token=client.admin_token)
    assert len(body['data']) >= 19

    status, body = client.call('GET', '/api/store/settings', token=client.admin_token)
    keys = [s['key'] for s in body['data']]
    assert 'attendance_config' in keys

    for table in ('punch_records', 'leave_records', 'overtime_records', 'travel_records',
                  'miss_punch_records', 'schedules', 'attendance_results', 'employees'):
        status, body = client.call('GET', '/api/store/' + table, token=client.admin_token)
        assert len(body['data']) == 0, table


def test_seed_reset_requires_hradmin(e2e_server):
    client = e2e_server
    client._emp = client.login('技001', 'test123')
    assert client._emp

    status, body = client.call('POST', '/api/system/seed-test-data', token=client._emp)
    assert status == 403
    status, body = client.call('POST', '/api/system/reset-data', token=client._emp)
    assert status == 403
