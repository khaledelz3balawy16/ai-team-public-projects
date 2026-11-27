"""
Custom JWT authentication for DRF.
Token is stored as HttpOnly cookie named 'psycho_token'.

This implementation resolves the decoded JWT to an existing auth table row.
"""
import jwt
from datetime import datetime, timezone
from django.conf import settings
from django.db import connection
from .db_utils import get_db_user_by_email
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed




def _make_name_from_user(user):
    full = (getattr(user, 'first_name', '') or '') + (' ' + (getattr(user, 'last_name', '') or '') if getattr(user, 'last_name', '') else '')
    return full.strip() or getattr(user, 'username', '') or getattr(user, 'email', '')





class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get('psycho_token')
        if not token:
            # Also accept Bearer header for dev/testing
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1]

        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=['HS256'],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired. Please log in again.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token.')

        # Resolve to an existing user_auth/auth_user row.
        email = (payload.get('email') or '').strip()
        name = payload.get('name') or ''

        user = None
        if email:
            user = get_db_user_by_email(email)

        if not user:
            raise AuthenticationFailed('User is not registered.')

        if not user.is_active:
            raise AuthenticationFailed('User account is inactive.')

        # provide convenience attributes used across the codebase
        user.name = name or _make_name_from_user(user)

        return (user, token)
