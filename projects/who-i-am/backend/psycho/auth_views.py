"""
Microsoft Azure OAuth2 flow — same pattern as superadminDashboard.
GET  /api/auth/login/    → redirect to Microsoft
GET  /api/auth/callback/ → exchange code, set cookie, redirect to frontend
POST /api/auth/logout/   → clear cookie
GET  /api/auth/me/       → return current user info
"""
import jwt
import msal
import requests as http_requests
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.hashers import check_password
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from .db_utils import get_auth_user_table, get_db_user_by_email, get_db_user_by_login


def _msal_app():
    missing = [
        name
        for name in (
            'AZURE_CLIENT_ID',
            'AZURE_CLIENT_SECRET',
            'AZURE_TENANT_ID',
            'AZURE_REDIRECT_URI',
        )
        if not getattr(settings, name, '')
    ]
    if missing:
        raise ValueError(f"Missing Azure OAuth settings: {', '.join(missing)}")

    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=f'https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}',
    )


def _make_token(user_info: dict) -> str:
    payload = {
        'email':    user_info.get('mail') or user_info.get('userPrincipalName', ''),
        'name':     user_info.get('displayName', ''),
        'azure_id': user_info.get('id', ''),
        'exp':      datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat':      datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def _make_token_for_user(user) -> str:
    full_name = ' '.join(
        part for part in (getattr(user, 'first_name', ''), getattr(user, 'last_name', '')) if part
    ).strip()
    payload = {
        'email':    getattr(user, 'email', '') or '',
        'name':     full_name or getattr(user, 'username', '') or getattr(user, 'email', ''),
        'azure_id': '',
        'exp':      datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat':      datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def _set_auth_cookie(response, token: str):
    response.set_cookie(
        'psycho_token',
        token,
        max_age=settings.JWT_EXPIRY_HOURS * 3600,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path='/',
    )
    return response


@require_http_methods(['GET'])
def login_redirect(request):
    try:
        app = _msal_app()
    except ValueError:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?auth_error=azure_config")

    auth_url = app.get_authorization_request_url(
        scopes=['User.Read'],
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )
    return HttpResponseRedirect(auth_url)


@require_http_methods(['GET'])
def oauth_callback(request):
    code  = request.GET.get('code')
    error = request.GET.get('error')

    if error or not code:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?auth_error=1")

    try:
        app = _msal_app()
    except ValueError:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?auth_error=azure_config")

    result = app.acquire_token_by_authorization_code(
        code,
        scopes=['User.Read'],
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )

    if 'error' in result:
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?auth_error=1")

    # Fetch user profile from Graph API
    graph_resp = http_requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers={'Authorization': f"Bearer {result['access_token']}"},
        timeout=10,
    )
    user_info = graph_resp.json()

    token = _make_token(user_info)
    # Create or update a corresponding Django `auth_user` row so the
    # frontend/backend can rely on Django's user table. Use raw DB helpers
    # so we don't require `django.contrib.auth` to be installed in INSTALLED_APPS.
    email = user_info.get('mail') or user_info.get('userPrincipalName', '')
    full_name = user_info.get('displayName', '') or ''
    first_name = full_name.split(' ')[0] if full_name else ''
    last_name = ' '.join(full_name.split(' ')[1:]) if full_name and len(full_name.split(' ')) > 1 else ''

    if not email or not get_db_user_by_email(email):
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?auth_error=not_registered")

    response = HttpResponseRedirect(settings.FRONTEND_URL)
    return _set_auth_cookie(response, token)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def password_login(request):
    identifier = (request.data.get('identifier') or request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    if not identifier or not password:
        return Response({'detail': 'Enter your username or email and password.'}, status=400)

    record = get_db_user_by_login(identifier)
    if not record:
        if not get_auth_user_table():
            return Response(
                {'detail': 'Auth database is not configured for this environment.'},
                status=503,
            )
        return Response({'detail': 'Invalid username/email or password.'}, status=401)

    user, password_hash = record
    if not user.is_active:
        return Response({'detail': 'This account is inactive.'}, status=403)

    if not password_hash or not check_password(password, password_hash):
        return Response({'detail': 'Invalid username/email or password.'}, status=401)

    token = _make_token_for_user(user)
    response = Response({
        'ok': True,
        'user': {
            'email': user.email,
            'name': ' '.join(part for part in (user.first_name, user.last_name) if part).strip() or user.username,
        },
    })
    return _set_auth_cookie(response, token)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def logout(request):
    response = Response({'ok': True})
    response.delete_cookie('psycho_token', path='/')
    return response


@require_http_methods(['GET'])
def dev_login(request):
    """Dev-only: ?email=... sets auth cookie and redirects to frontend."""
    if not settings.DEBUG:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Not available in production.')

    email = (request.GET.get('email') or '').strip()
    if not email:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest('Missing ?email= parameter.')

    payload = {
        'email':    email,
        'name':     email.split('@')[0].replace('.', ' ').title(),
        'azure_id': '',
        'exp':      datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat':      datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    response = HttpResponseRedirect(settings.FRONTEND_URL)
    return _set_auth_cookie(response, token)


@api_view(['GET'])
def me(request):
    user = request.user
    if not user or not getattr(user, 'is_authenticated', False):
        return Response({'detail': 'Authentication required.'}, status=401)

    return Response({
        'email': user.email,
        'name':  user.name,
    })
