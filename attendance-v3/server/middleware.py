import json
import jwt
import os
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

SECRET_KEY = os.environ.get('JWT_SECRET', 'attendance-v3-default-secret-key-change-in-production')
TOKEN_EXPIRE_HOURS = 24


def generate_token(user_id, username, role, department):
    payload = {
        'uid': user_id,
        'username': username,
        'role': role,
        'department': department,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_role(*roles):
    def decorator(handler_func):
        @wraps(handler_func)
        def wrapper(self, *args, **kwargs):
            auth_header = self.headers.get('Authorization', '')
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
            if not token:
                self._send_json(401, message='未提供认证令牌')
                return
            payload = verify_token(token)
            if payload is None:
                self._send_json(401, message='令牌无效或已过期')
                return
            user_role = payload.get('role', '')
            if roles and user_role not in roles:
                self._send_json(403, message='无权限访问')
                return
            self._current_user = payload
            return handler_func(self, *args, **kwargs)
        return wrapper
    return decorator


def _send_json(handler, code, data=None, message=None):
    body = {'code': code}
    if data is not None:
        body['data'] = data
    if message is not None:
        body['message'] = message
    status_code = 200 if code == 0 else (401 if code == 401 else (403 if code == 403 else 400))
    handler.send_response(status_code)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(json.dumps(body, ensure_ascii=False).encode('utf-8'))


def _read_body(handler):
    content_len = int(handler.headers.get('Content-Length', 0))
    if content_len == 0:
        return {}
    body = handler.rfile.read(content_len)
    return json.loads(body)
