"""OA 字段映射 / 代申请匹配"""
import os
import subprocess

CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'client')
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join('/tmp', 'opencode')
STUB = os.path.join(OUT_DIR, 'field_map_under_test.mjs')


def test_field_map_and_proxy_match():
    os.makedirs(OUT_DIR, exist_ok=True)
    src_path = os.path.join(CLIENT_DIR, 'src', 'shared', 'fieldMap.js')
    with open(src_path, encoding='utf-8') as f:
        src = f.read()
    src = src.replace(
        "import Store from './store';",
        "const Store = { getByKey: async () => null, put: async () => {} };",
    )
    with open(STUB, 'w', encoding='utf-8') as f:
        f.write(src)
    matcher = os.path.join(CLIENT_DIR, 'src', 'shared', 'matcher.js')
    result = subprocess.run(
        ['node', os.path.join(TESTS_DIR, 'field_map.mjs'), STUB, matcher],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, 'stdout: {}\nstderr: {}'.format(result.stdout, result.stderr)
