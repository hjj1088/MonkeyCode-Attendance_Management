TEST_PORT = 18089


def test_attendance_months_requires_auth(e2e_server):
    status, _ = e2e_server.call('GET', '/api/attendance/months')
    assert status == 401, 'months requires auth'


def test_attendance_months_returns_list(e2e_server):
    client = e2e_server
    results = []
    for i in range(2):
        for d in ('05', '06'):
            results.append({
                'employeeNo': 'E%02d' % i, 'name': '员工%d' % i, 'department': '技术部',
                'date': '2026-08-' + d, 'month': '2026-08', 'status': 'normal',
            })
    status, body = client.call('POST', '/api/attendance/calculate', {
        'month': '2026-08', 'results': results,
    }, token=client.admin_token)
    assert status == 200, body

    status, body = client.call('GET', '/api/attendance/months',
                               token=client.admin_token)
    assert status == 200, body
    months = body.get('data')
    assert isinstance(months, list)
    assert '2026-08' in months
