import json
import bcrypt
import re
from database import get_db
from middleware import verify_token


ADMIN_ROLES = ('hradmin', 'superadmin')


def _require_admin(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return None
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return None
    if payload.get('role') not in ADMIN_ROLES:
        handler._send_json(403, message='无权限访问')
        return None
    return payload


def _get_target_user(conn, user_id):
    return conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()


def _can_manage(actor_role, target_role):
    return actor_role == 'superadmin' or target_role != 'superadmin'


def handle_users_list(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, name, department, role, employee_no, enabled, locked_until, login_attempts, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    users = [dict(r) for r in rows]
    if payload.get('role') != 'superadmin':
        users = [u for u in users if u['role'] != 'superadmin']
    handler._send_json(0, data=users)


def handle_users_create(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    username = (body.get('username') or '').strip()
    name = (body.get('name') or '').strip()
    department = (body.get('department') or '').strip()
    role = (body.get('role') or 'employee').strip()
    employee_no = (body.get('employee_no') or '').strip() or username
    password = (body.get('password') or '123456').strip()

    if not username or not name:
        handler._send_json(400, message='用户名和姓名不能为空')
        return

    if role not in ('employee', 'deptadmin', 'hradmin', 'superadmin'):
        handler._send_json(400, message='无效的角色类型')
        return
    if role == 'superadmin' and payload.get('role') != 'superadmin':
        handler._send_json(403, message='仅超级管理员可创建该角色')
        return

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        handler._send_json(400, message='用户名已存在')
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "INSERT INTO users (username, password_hash, name, department, role, employee_no) VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, name, department, role, employee_no)
    )
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '用户创建成功'})


def handle_users_import_from_punch(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT employeeNo, name, department FROM employees "
        "WHERE employeeNo IS NOT NULL AND employeeNo != ''"
    ).fetchall()
    if not rows:
        rows = conn.execute(
            "SELECT DISTINCT employeeNo, name, department FROM punch_records "
            "WHERE employeeNo IS NOT NULL AND employeeNo != ''"
        ).fetchall()
    existing = {r[0] for r in conn.execute("SELECT username FROM users").fetchall()}
    password_hash = bcrypt.hashpw('123456'.encode(), bcrypt.gensalt()).decode()
    created = 0
    skipped = 0
    for r in rows:
        emp_no = (r['employeeNo'] or '').strip()
        name = (r['name'] or '').strip()
        department = (r['department'] or '').strip()
        if not emp_no:
            continue
        # 用户名取姓名；无姓名或重名时回退为考勤号
        uname = name if name and name not in existing else emp_no
        if uname in existing:
            skipped += 1
            continue
        conn.execute(
            "INSERT INTO users (username, password_hash, name, department, role, employee_no) VALUES (?, ?, ?, ?, 'employee', ?)",
            (uname, password_hash, name or uname, department, emp_no)
        )
        existing.add(uname)
        created += 1
    conn.commit()
    conn.close()
    handler._send_json(0, data={
        'created': created,
        'skipped': skipped,
        'message': '成功导入 {} 个账号，跳过 {} 个已存在账号'.format(created, skipped),
    })


def handle_users_update(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    import re
    match = re.match(r'/api/users/(\d+)', handler.path)
    if not match:
        handler._send_json(400, message='无效的用户ID')
        return
    user_id = int(match.group(1))

    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    conn = get_db()
    target = _get_target_user(conn, user_id)
    if not target:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return
    if not _can_manage(payload.get('role', ''), target['role']):
        conn.close()
        handler._send_json(403, message='无权操作该用户')
        return

    updates = []
    values = []
    for field in ('name', 'department', 'role', 'employee_no'):
        val = body.get(field)
        if val is not None:
            val = val.strip()
            if field == 'role':
                if val not in ('employee', 'deptadmin', 'hradmin', 'superadmin'):
                    conn.close()
                    handler._send_json(400, message='无效的角色类型')
                    return
                if val == 'superadmin' and payload.get('role') != 'superadmin':
                    conn.close()
                    handler._send_json(403, message='仅超级管理员可分配该角色')
                    return
            updates.append('{} = ?'.format(field))
            values.append(val)

    if not updates:
        conn.close()
        handler._send_json(400, message='没有要更新的字段')
        return

    values.append(user_id)
    conn.execute("UPDATE users SET {} WHERE id = ?".format(', '.join(updates)), values)
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '用户更新成功'})


def handle_users_status(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    match = re.match(r'/api/users/(\d+)/status', handler.path)
    if not match:
        handler._send_json(400, message='无效的用户ID')
        return
    user_id = int(match.group(1))

    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return
    enabled = body.get('enabled', 1)

    conn = get_db()
    target = conn.execute(
        "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not target:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return
    if target['username'] == 'admin':
        conn.close()
        handler._send_json(403, message='内置超级管理员账号不可禁用')
        return
    if not _can_manage(payload.get('role', ''), target['role']):
        conn.close()
        handler._send_json(403, message='无权操作该用户')
        return

    conn.execute("UPDATE users SET enabled = ? WHERE id = ?", (enabled, user_id))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '状态已更新'})


def handle_users_delete(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    match = re.match(r'/api/users/(\d+)', handler.path)
    if not match:
        handler._send_json(400, message='无效的用户ID')
        return
    user_id = int(match.group(1))

    conn = get_db()
    target = conn.execute(
        "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not target:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return
    if target['username'] == 'admin':
        conn.close()
        handler._send_json(403, message='内置超级管理员账号不可删除')
        return
    if payload.get('uid') == user_id:
        conn.close()
        handler._send_json(400, message='不能删除自己')
        return
    if not _can_manage(payload.get('role', ''), target['role']):
        conn.close()
        handler._send_json(403, message='无权操作该用户')
        return

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '用户已删除'})


def handle_users_reset_password(handler):
    payload = _require_admin(handler)
    if payload is None:
        return
    body = handler._read_body()
    if not body:
        handler._send_json(400, message='请求体为空')
        return

    user_id = body.get('user_id')
    new_password = (body.get('new_password') or '123456').strip()

    if not user_id:
        handler._send_json(400, message='缺少用户ID')
        return

    conn = get_db()
    target = _get_target_user(conn, user_id)
    if not target:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return
    if not _can_manage(payload.get('role', ''), target['role']):
        conn.close()
        handler._send_json(403, message='无权操作该用户')
        return

    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "UPDATE users SET password_hash = ?, login_attempts = 0, locked_until = NULL WHERE id = ?",
        (password_hash, user_id)
    )
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '密码已重置', 'new_password': new_password})
