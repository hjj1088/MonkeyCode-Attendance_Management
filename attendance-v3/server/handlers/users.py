import json
import bcrypt
import re
from database import get_db
from middleware import verify_token


def _require_hradmin(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return None
    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return None
    if payload.get('role') != 'hradmin':
        handler._send_json(403, message='无权限访问')
        return None
    return payload


def handle_users_list(handler):
    payload = _require_hradmin(handler)
    if payload is None:
        return
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, name, department, role, enabled, locked_until, login_attempts, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    users = [dict(r) for r in rows]
    handler._send_json(0, data=users)


def handle_users_create(handler):
    payload = _require_hradmin(handler)
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
    password = (body.get('password') or '123456').strip()

    if not username or not name:
        handler._send_json(400, message='用户名和姓名不能为空')
        return

    if role not in ('employee', 'deptadmin', 'hradmin'):
        handler._send_json(400, message='无效的角色类型')
        return

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        handler._send_json(400, message='用户名已存在')
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "INSERT INTO users (username, password_hash, name, department, role) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, name, department, role)
    )
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '用户创建成功'})


def handle_users_update(handler):
    payload = _require_hradmin(handler)
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
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return

    updates = []
    values = []
    for field in ('name', 'department', 'role'):
        val = body.get(field)
        if val is not None:
            val = val.strip()
            if field == 'role' and val not in ('employee', 'deptadmin', 'hradmin'):
                conn.close()
                handler._send_json(400, message='无效的角色类型')
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
    payload = _require_hradmin(handler)
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
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return

    conn.execute("UPDATE users SET enabled = ? WHERE id = ?", (enabled, user_id))
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '状态已更新'})


def handle_users_reset_password(handler):
    payload = _require_hradmin(handler)
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
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        handler._send_json(404, message='用户不存在')
        return

    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute(
        "UPDATE users SET password_hash = ?, login_attempts = 0, locked_until = NULL WHERE id = ?",
        (password_hash, user_id)
    )
    conn.commit()
    conn.close()
    handler._send_json(0, data={'message': '密码已重置', 'new_password': new_password})
