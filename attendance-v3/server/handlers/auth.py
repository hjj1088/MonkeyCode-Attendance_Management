import bcrypt
from database import get_db, get_user_by_username, reset_login_attempts, increment_login_attempt, clear_locked_if_expired
from middleware import generate_token, verify_token, _send_json


def ensure_admin_user():
    conn = get_db()
    user = get_user_by_username(conn, 'admin')
    if not user:
        from database import create_user
        password_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        create_user(conn, 'admin', password_hash, '系统管理员', '总部', 'hradmin')
    conn.close()


def handle_login(handler):
    try:
        data = handler._read_body()
    except Exception:
        handler._send_json(1, message='无效的请求格式')
        return

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        handler._send_json(1, message='用户名和密码不能为空')
        return

    conn = get_db()
    user = get_user_by_username(conn, username)
    if not user:
        conn.close()
        handler._send_json(1, message='账号或密码错误')
        return

    if not user['enabled']:
        conn.close()
        handler._send_json(1, message='账号已被禁用')
        return

    if user['locked_until']:
        from datetime import datetime
        if datetime.fromisoformat(user['locked_until']) > datetime.now():
            conn.close()
            handler._send_json(1, message='账号已被锁定，请稍后再试')
            return
        clear_locked_if_expired(conn, user['id'])

    if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        attempt_info = increment_login_attempt(conn, user['id'])
        conn.close()
        if attempt_info['login_attempts'] >= 5:
            handler._send_json(1, message='密码错误次数过多，账号已锁定30分钟')
        else:
            handler._send_json(1, message='账号或密码错误')
        return

    reset_login_attempts(conn, user['id'])
    conn.close()

    need_change = False
    if user['username'] == 'admin' and user['role'] == 'hradmin':
        need_change = bcrypt.checkpw('admin123'.encode(), user['password_hash'].encode())

    token = generate_token(user['id'], user['username'], user['role'], user['department'])
    handler._send_json(0, data={
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'department': user['department'],
            'role': user['role'],
        },
        'need_change_password': need_change,
    })


def handle_change_password(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if not token:
        handler._send_json(401, message='未提供认证令牌')
        return

    payload = verify_token(token)
    if payload is None:
        handler._send_json(401, message='令牌无效或已过期')
        return

    try:
        data = handler._read_body()
    except Exception:
        handler._send_json(1, message='无效的请求格式')
        return

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        handler._send_json(1, message='旧密码和新密码不能为空')
        return

    if len(new_password) < 6:
        handler._send_json(1, message='新密码长度不能少于6位')
        return

    conn = get_db()
    user = get_user_by_username(conn, payload['username'])
    if not user:
        conn.close()
        handler._send_json(1, message='用户不存在')
        return

    if not bcrypt.checkpw(old_password.encode(), user['password_hash'].encode()):
        conn.close()
        handler._send_json(1, message='旧密码不正确')
        return

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
    conn.commit()
    conn.close()

    handler._send_json(0, data={'message': '密码修改成功'})
