"""
D3 考勤计算测试：esbuild bundle 前端 rules.js，用 Node 子进程驱动（mock store）
覆盖：排班+请假→leave、容错豁免（月2次≤30min）、加班调休结余
"""
import os
import subprocess
import pytest

CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'client')
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.join('/tmp', 'opencode', 'd3_rules.bundle.mjs')


@pytest.fixture(scope='module', autouse=True)
def bundle_rules():
    esbuild = os.path.join(CLIENT_DIR, 'node_modules', '.bin', 'esbuild')
    if not os.path.exists(esbuild):
        pytest.skip('esbuild not installed')
    os.makedirs(os.path.dirname(BUNDLE), exist_ok=True)
    subprocess.run(
        [esbuild, os.path.join(CLIENT_DIR, 'src', 'shared', 'rules.js'),
         '--bundle', '--format=esm', '--outfile=' + BUNDLE, '--log-level=error'],
        check=True,
    )


def test_calculate_month_flow(bundle_rules):
    assert os.path.exists(BUNDLE)
    result = subprocess.run(
        ['node', os.path.join(TESTS_DIR, 'calc_flow.mjs'), BUNDLE],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, 'stdout: {}\nstderr: {}'.format(result.stdout, result.stderr)
