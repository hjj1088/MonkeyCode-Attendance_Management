"""
导出功能集成测试
"""
import os
import sys
import json
import pytest
import tempfile
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    import database
    db_dir = os.path.join(tempfile.gettempdir(), 'attendance-v3-test-export')
    db_path = os.path.join(db_dir, 'attendance.db')
    monkeypatch.setattr(database, 'DB_DIR', db_dir)
    monkeypatch.setattr(database, 'DB_PATH', db_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_db()
    yield db_path
    try:
        os.remove(db_path)
    except OSError:
        pass


class MockHandler:
    def __init__(self, body=None, path=''):
        self.sent = None
        self._body = json.dumps(body) if body else None
        self.path = path
        body_b = json.dumps(body).encode() if body else b''
        self.headers = {'Content-Length': str(len(body_b))}
        self.rfile = type('obj', (object,), {'read': lambda s, n: body_b})()

    def _read_body(self):
        if self._body:
            return json.loads(self._body)
        return {}

    def _send_json(self, code, data=None, message=None):
        self.sent = {'code': code, 'data': data, 'message': message}

    def send_response(self, code):
        self.sent = {'_status': code}

    def send_header(self, k, v):
        pass

    def end_headers(self):
        pass

    def wfile(self):
        return type('obj', (object,), {'write': lambda s, d: None})()


class TestExport:
    def test_build_flat_report_creates_workbook(self):
        from handlers.export import build_flat_report
        import openpyxl
        import io

        records = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'signIn': '08:30', 'signOut': '17:30', 'status': 'normal'}
        ]
        template = {'fields': [
            {'field': 'employeeNo', 'label': '工号'},
            {'field': 'name', 'label': '姓名'},
            {'field': 'signIn', 'label': '签到'},
            {'field': 'signOut', 'label': '签退'},
            {'field': 'status', 'label': '状态'},
        ]}

        output = build_flat_report(records, template, 'test.xlsx')
        wb = openpyxl.load_workbook(output, data_only=True)
        ws = wb.active
        assert ws.max_row == 2
        assert ws.max_column == 5
        assert ws.cell(1, 1).value == '工号'
        assert ws.cell(2, 1).value == 'T001'
        assert ws.cell(2, 5).value == '正常'

    def test_build_flat_report_conditional_formatting(self):
        from handlers.export import build_flat_report
        import openpyxl
        import io

        records = [
            {'employeeNo': 'T001', 'name': '张三', 'signIn': '09:30', 'signOut': '16:30', 'status': 'normal'}
        ]
        template = {'fields': [
            {'field': 'signIn', 'label': '签到'},
            {'field': 'signOut', 'label': '签退'},
        ]}

        output = build_flat_report(records, template, 'test.xlsx', startTime='08:30', endTime='17:30')
        wb = openpyxl.load_workbook(output)
        ws = wb.active

        cf_count = len(ws.conditional_formatting._cf_rules)
        assert cf_count >= 2

    def test_build_flat_report_time_abnormal_formatting(self):
        from handlers.export import build_flat_report
        import openpyxl

        # 上班迟到 > 8:30
        records_late = [
            {'employeeNo': 'T001', 'name': '张三', 'signIn': '09:30', 'signOut': '17:30', 'status': 'normal'}
        ]
        template = {'fields': [
            {'field': 'signIn', 'label': '签到'},
            {'field': 'signOut', 'label': '签退'},
        ]}

        output = build_flat_report(records_late, template, 'test_late.xlsx', startTime='08:30', endTime='17:30')
        wb = openpyxl.load_workbook(output)
        ws = wb.active

        # 检查是否有条件格式规则
        cf_count = len(ws.conditional_formatting._cf_rules)
        assert cf_count >= 1

        # 检查下班早退 < 17:30
        records_early = [
            {'employeeNo': 'T001', 'name': '张三', 'signIn': '08:30', 'signOut': '16:30', 'status': 'normal'}
        ]

        output = build_flat_report(records_early, template, 'test_early.xlsx', startTime='08:30', endTime='17:30')
        wb = openpyxl.load_workbook(output)
        ws = wb.active

        cf_count = len(ws.conditional_formatting._cf_rules)
        assert cf_count >= 1

    def test_build_calendar_report_structure(self):
        from handlers.export import build_calendar_report
        import openpyxl

        results = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '08:30', 'signOut': '17:30'}
        ]
        output = build_calendar_report('2026-07', [], results, [])
        wb = openpyxl.load_workbook(output, data_only=True)
        ws = wb.active
        assert ws.title == '2026年7月考勤明细'
        assert ws.max_row >= 2

    def test_build_calendar_with_holiday(self):
        from handlers.export import build_calendar_report
        import openpyxl

        results = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '08:30', 'signOut': '17:30'}
        ]
        holidays = [{'date': '2026-07-01', 'name': '法定假日', 'is_holiday': True}]
        output = build_calendar_report('2026-07', [], results, [], holidays)
        wb = openpyxl.load_workbook(output, data_only=True)
        ws = wb.active
        assert ws.cell(3, 2).value == '法定假日'

    def _cf_formulas(self, ws):
        formulas = []
        for rules in ws.conditional_formatting._cf_rules.values():
            for rule in rules:
                for f in getattr(rule, 'formula', []) or []:
                    formulas.append(str(f))
        return formulas

    def _is_red_font(self, cell):
        color = cell.font.color if cell.font else None
        if color is None:
            return False
        rgb = str(getattr(color, 'rgb', '') or '')
        return 'FF0000' in rgb.upper()

    def _cell_hhmm(self, cell):
        val = cell.value
        if hasattr(val, 'hour'):
            return f'{val.hour:02d}:{val.minute:02d}'
        return str(val) if val is not None else ''

    def test_build_calendar_time_abnormal_formatting(self):
        from handlers.export import build_calendar_report
        import openpyxl

        results = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '09:30', 'signOut': '16:30'}
        ]
        output = build_calendar_report('2026-07', [], results, [], [], startTime='08:30', endTime='17:30')
        wb = openpyxl.load_workbook(output)
        ws = wb.active

        formulas = self._cf_formulas(ws)
        joined = '\n'.join(formulas)
        assert len(formulas) >= 2
        assert 'ISNUMBER' in joined
        assert 'MOD(ROW(),2)=1' in joined
        assert 'MOD(ROW(),2)=0' in joined
        assert 'TIME(8,30,0)' in joined.replace(' ', '')
        assert 'TIME(17,30,0)' in joined.replace(' ', '')

        assert self._cell_hhmm(ws.cell(3, 4)) == '09:30'
        assert self._is_red_font(ws.cell(3, 4)), 'late sign-in must be red'
        assert self._cell_hhmm(ws.cell(4, 4)) == '16:30'
        assert self._is_red_font(ws.cell(4, 4)), 'early sign-out must be red'

        results_ok = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '08:30', 'signOut': '17:30'}
        ]
        output_ok = build_calendar_report('2026-07', [], results_ok, [], [], startTime='08:30', endTime='17:30')
        ws_ok = openpyxl.load_workbook(output_ok).active
        assert not self._is_red_font(ws_ok.cell(3, 4)), 'on-time sign-in stays default'
        assert not self._is_red_font(ws_ok.cell(4, 4)), 'on-time sign-out stays default'

    def test_export_reads_work_times_from_attendance_config(self):
        from handlers.export import build_calendar_report, build_flat_report
        import database
        import openpyxl

        conn = database.get_db()
        conn.execute(
            "UPDATE settings SET value = ? WHERE key = 'attendance_config'",
            (json.dumps({
                'workStartTime': '09:00:00',
                'workEndTime': '18:00',
                'lateThreshold': 0,
                'earlyThreshold': 0,
            }, ensure_ascii=False),)
        )
        conn.commit()
        conn.close()

        results = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '09:00', 'signOut': '17:30'}
        ]
        output = build_calendar_report('2026-07', [], results, [])
        ws = openpyxl.load_workbook(output).active
        joined = '\n'.join(self._cf_formulas(ws)).replace(' ', '')
        assert 'TIME(9,0,0)' in joined
        assert 'TIME(18,0,0)' in joined
        assert not self._is_red_font(ws.cell(3, 4)), '09:00 is on time vs config 09:00'
        assert self._is_red_font(ws.cell(4, 4)), '17:30 is early vs config 18:00'

        template = {'fields': [
            {'field': 'signIn', 'label': '签到'},
            {'field': 'signOut', 'label': '签退'},
        ]}
        flat = build_flat_report(
            [{'employeeNo': 'T001', 'signIn': '09:30', 'signOut': '18:00'}],
            template, 't.xlsx'
        )
        ws_flat = openpyxl.load_workbook(flat).active
        flat_joined = '\n'.join(self._cf_formulas(ws_flat)).replace(' ', '')
        assert 'TIME(9,0,0)' in flat_joined
        assert 'TIME(18,0,0)' in flat_joined
        assert self._is_red_font(ws_flat.cell(2, 1)), '09:30 late vs config 09:00'
        assert not self._is_red_font(ws_flat.cell(2, 2)), '18:00 on time vs config 18:00'

    def test_build_calendar_groups_by_department(self):
        from handlers.export import build_calendar_report
        import openpyxl

        results = [
            {'employeeNo': 'T001', 'name': '张三', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '08:30', 'signOut': '17:30'},
            {'employeeNo': 'T002', 'name': '李四', 'department': '技术部',
             'date': '2026-07-01', 'status': 'normal', 'signIn': '08:30', 'signOut': '17:30'},
            {'employeeNo': 'S001', 'name': '王五', 'department': '销售部',
             'date': '2026-07-01', 'status': 'leave', 'leaveType': '年假', 'leaveHours': 8},
        ]
        output = build_calendar_report('2026-07', [], results, [])
        wb = openpyxl.load_workbook(output, data_only=True)
        ws = wb.active

        header1 = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        header2 = [ws.cell(2, c).value for c in range(1, ws.max_column + 1)]

        # 部门名只在部门首列出现（合并单元格），技术部两人连续
        assert header1.count('技术部') == 1
        assert header1.count('销售部') == 1
        assert '张三' in header2 and '李四' in header2 and '王五' in header2

        tech_idx = header1.index('技术部')
        assert header1[tech_idx + 1] in ('', None), 'second tech employee keeps dept header empty'
        assert header1[tech_idx + 2] == '销售部', 'sales dept follows tech block'
