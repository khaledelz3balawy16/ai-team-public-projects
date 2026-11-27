import jwt, requests, os
from datetime import datetime, timedelta, timezone

payload = {
    'email': 'test.user@example.com',
    'name': 'Test User',
    'azure_id': 'test-azure-123',
    'exp': datetime.now(timezone.utc) + timedelta(hours=1),
    'iat': datetime.now(timezone.utc),
}
secret = os.environ.get('JWT_SECRET_KEY') or 'CHANGE_ME'
token = jwt.encode(payload, secret, algorithm='HS256')
resp = requests.get('http://127.0.0.1:8000/api/auth/me', cookies={'psycho_token': token}, headers={'Host': 'localhost:8000'}, timeout=10)
print('STATUS', resp.status_code)
print(resp.text)
