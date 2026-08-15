"""
共享 E2E 测试夹具：隔离 DB + 真实 HTTP 服务器（复用 test_api_e2e 模式）。
用法：模块顶部设置 TEST_PORT / TEST_DB_NAME 后使用 e2e_server fixture。
"""
import json
import os
import sys
import threading
import time
import tempfile
import urllib.request
import urllib.error
import pytest

SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server')
sys.path.insert(0, SERVER_DIR)


class ApiClient:
    def __init__(self, base):
        self.base = base

    def call(self, method, path, body=None, token=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        if token:
            req.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                if raw:
                    return resp.status, content
                return resp.status, json.loads(content)
        except urllib.error.HTTPError as e:
            content = e.read()
            if raw:
                return e.code, content
            try:
                return e.code, json.loads(content)
            except Exception:
                return e.code, {'code': 1, 'message': content.decode('utf-8', 'ignore')}

    def login(self, username, password):
        status, body = self.call('POST', '/api/auth/login', {'username': username, 'password': password})
        if status == 200 and body.get('code') == 0:
            return body['data']['token']
        return None


@pytest.fixture(scope='module')
def e2e_server(request):
    port = getattr(request.module, 'TEST_PORT', 18082)
    db_dir = os.path.join(tempfile.gettempdir(), 'attendance-v3-d3-{}'.format(port))
    db_path = os.path.join(db_dir, 'attendance.db')

    import database
    database.DB_DIR = db_dir
    database.DB_PATH = db_path
    if os.path.exists(db_path):
        os.remove(db_path)

    import server as server_mod
    server_mod.PORT = port
    from handlers.auth import ensure_admin_user
    database.init_db()
    ensure_admin_user()

    from http.server import HTTPServer
    from server import APIHandler
    httpd = HTTPServer(('127.0.0.1', port), APIHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)

    client = ApiClient('http://127.0.0.1:{}'.format(port))
    client.admin_token = client.login('admin', 'admin123')
    assert client.admin_token
    yield client
    httpd.shutdown()
    try:
        os.remove(db_path)
    except OSError:
        pass
