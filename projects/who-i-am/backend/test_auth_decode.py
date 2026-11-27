from types import SimpleNamespace
import jwt, os
from datetime import datetime, timedelta, timezone

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from psycho.authentication import JWTAuthentication

payload = {
    'email': 'test.user@example.com',
    'name': 'Test User',
    'azure_id': 'test-azure-123',
    'exp': datetime.now(timezone.utc) + timedelta(hours=1),
    'iat': datetime.now(timezone.utc),
}
secret = os.environ.get('JWT_SECRET_KEY') or 'CHANGE_ME'
token = jwt.encode(payload, secret, algorithm='HS256')

req = SimpleNamespace(COOKIES={'psycho_token': token}, META={})

auth = JWTAuthentication()
user_token = auth.authenticate(req)
print('AUTH RESULT:', user_token)
