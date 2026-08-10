"""
V3.1 frontend api-store integration test runner.
Starts an isolated backend (temp DB + port 8002), runs tests/integration_api_store.js,
then shuts down.
"""
import os
import sys
import json
import time
import tempfile
import urllib.request
import subprocess
import threading
import http.server

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

import database

TEST_PORT = 8002
TEST_DIR = tempfile.mkdtemp(prefix='attendance-v3-integration-')
database.DB_DIR = TEST_DIR
database.DB_PATH = os.path.join(TEST_DIR, 'attendance.db')
database.init_db()

import server as server_module
server_module.PORT = TEST_PORT
server_module.ADMIN_PASSWORD_HASH = __import__('hashlib').sha256('admin123'.encode()).hexdigest()

srv = None


def wait_ready(url, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main():
    global srv
    srv = http.server.HTTPServer(('127.0.0.1', TEST_PORT), server_module.APIHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    if not wait_ready(f'http://127.0.0.1:{TEST_PORT}/api/system/version'):
        print('FAIL: server not ready')
        sys.exit(1)

    script = os.path.join(os.path.dirname(__file__), 'integration_api_store.js')
    env = dict(os.environ, TEST_PORT=str(TEST_PORT))
    proc = subprocess.run(['node', script], capture_output=True, text=True, env=env)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    srv.shutdown()
    return 0 if proc.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
