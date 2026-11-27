import json
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import AttendanceQR

_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _safe_identifier(value: str, label: str) -> str:
    if not value or not _IDENTIFIER_RE.match(value):
        raise ValueError(f'Invalid {label}: {value!r}')
    return connection.ops.quote_name(value)


def _resolve_column(schema_name: str, table_name: str, preferred: str, *, fallbacks=None, required=False):
    candidates = []
    if preferred:
        candidates.append(preferred)
    for item in (fallbacks or []):
        if item and item not in candidates:
            candidates.append(item)

    with connection.cursor() as cursor:
        for candidate in candidates:
            cursor.execute(
                '''
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                LIMIT 1
                ''',
                [schema_name, table_name, candidate],
            )
            if cursor.fetchone():
                return connection.ops.quote_name(candidate), candidate

    if required:
        raise ValueError(f'Column not found: {preferred!r}')
    return None, None


def _to_text(value):
    if value is None:
        return ''
    return str(value).strip()


def _to_int(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _combine_groups(*values):
    groups = []
    seen = set()
    for value in values:
        text = _to_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        groups.append(text)
    return ' / '.join(groups)


def _split_groups(primary_group, secondary_group):
    return _to_text(primary_group), _to_text(secondary_group)


def _available_groups(primary_group, secondary_group):
    groups = []
    seen = set()
    for value in (primary_group, secondary_group):
        text = _to_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        groups.append(text)
    return groups


def _normalize_student_groups(primary_group, secondary_group, secondary_group_reason):
    primary = _to_text(primary_group)
    secondary = _to_text(secondary_group)
    reason = _to_text(secondary_group_reason).casefold()

    if secondary and reason == 'transferred':
        return secondary, '', [secondary]

    return primary, secondary, _available_groups(primary, secondary)


def _all_table_groups(schema, table, group_col, other_group_col):
    if not group_col and not other_group_col:
        return []

    sources = []
    if group_col:
        sources.append(f"SELECT TRIM({group_col}) AS group_name FROM {schema}.{table}")
    if other_group_col:
        sources.append(f"SELECT TRIM({other_group_col}) AS group_name FROM {schema}.{table}")

    sql = " UNION ".join(sources)
    sql = f"SELECT DISTINCT group_name FROM ({sql}) AS all_groups WHERE group_name IS NOT NULL AND group_name <> '' ORDER BY group_name"

    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [row[0] for row in cursor.fetchall()]


def _update_student_transfer_group(
    schema,
    table,
    id_col,
    student_id,
    previous_other_group,
    last_group_col,
    other_group_col,
    other_group_reason_col,
    selected_group,
):
    if not other_group_col or not other_group_reason_col or student_id is None:
        return

    set_clauses = [
        f"{other_group_col} = %s",
        f"{other_group_reason_col} = %s",
    ]
    params = [selected_group, 'Transferred']

    if last_group_col:
        set_clauses.append(f"{last_group_col} = %s")
        params.append(previous_other_group)

    sql = (
        f"UPDATE {schema}.{table} "
        f"SET {', '.join(set_clauses)} "
        f"WHERE {id_col} = %s"
    )
    params.append(student_id)

    with connection.cursor() as cursor:
        cursor.execute(sql, params)


def _client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip() or 'unknown'
    return request.META.get('REMOTE_ADDR', 'unknown')


def _cache_incr(key: str, timeout: int) -> int:
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def _is_rate_limited(request, email: str) -> bool:
    ip = _client_ip(request)
    normalized_email = email.lower()
    window = max(1, int(getattr(settings, 'LOGIN_RATE_LIMIT_WINDOW_SECONDS', 300)))
    per_ip = max(1, int(getattr(settings, 'LOGIN_RATE_LIMIT_PER_IP', 30)))
    per_email = max(1, int(getattr(settings, 'LOGIN_RATE_LIMIT_PER_EMAIL', 8)))
    block_seconds = max(1, int(getattr(settings, 'LOGIN_BLOCK_SECONDS', 900)))

    ip_block_key = f'login:block:ip:{ip}'
    email_block_key = f'login:block:email:{normalized_email}'
    if cache.get(ip_block_key) or cache.get(email_block_key):
        return True

    ip_count = _cache_incr(f'login:count:ip:{ip}', timeout=window)
    email_count = _cache_incr(f'login:count:email:{normalized_email}', timeout=window)

    limited = False
    if ip_count > per_ip:
        cache.set(ip_block_key, 1, timeout=block_seconds)
        limited = True
    if email_count > per_email:
        cache.set(email_block_key, 1, timeout=block_seconds)
        limited = True

    return limited


@ensure_csrf_cookie
def login_page(request):
    return render(request, 'login.html')


def favicon(request):
    templates_dir = Path(settings.BASE_DIR) / 'templates'
    for name in ('icon.png', 'images.png'):
        icon_path = templates_dir / name
        if icon_path.exists():
            return FileResponse(open(icon_path, 'rb'), content_type='image/png')
    raise Http404('Icon not found')


def brand_logo(request):
    templates_dir = Path(settings.BASE_DIR) / 'templates'
    logo_path = templates_dir / 'Kent-Business-College-e1768393206822.webp'
    if logo_path.exists():
        return FileResponse(open(logo_path, 'rb'), content_type='image/webp')
    raise Http404('Logo not found')


def healthz(request):
    return JsonResponse({'status': 'ok'})


@require_POST
def student_login(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON body'}, status=400)

    email = (payload.get('email') or '').strip()
    selected_group = _to_text(payload.get('selected_group'))
    attendance_reason = _to_text(payload.get('attendance_reason')).lower()
    valid_reasons = {'catch_up', 'transferred'}
    if not email:
        return JsonResponse({'detail': 'Please enter your Aptem email'}, status=400)
    if _is_rate_limited(request, email):
        return JsonResponse(
            {'detail': 'Too many attempts. Please try again later.'},
            status=429,
        )

    schema_name = settings.KBC_TABLE_SCHEMA
    table_name = settings.KBC_TABLE_NAME

    try:
        schema = _safe_identifier(schema_name, 'schema name')
        table = _safe_identifier(table_name, 'table name')

        email_col, _ = _resolve_column(
            schema_name,
            table_name,
            settings.KBC_EMAIL_COLUMN,
            fallbacks=['Email', 'email'],
            required=True,
        )
        id_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_ID_COLUMN', 'ID'),
            fallbacks=['ID', 'id'],
            required=True,
        )
        name_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_NAME_COLUMN', 'FullName'),
            fallbacks=['FullName', 'fullname', 'FirstName', 'full_name'],
            required=False,
        )
        group_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_GROUP_COLUMN', 'group'),
            fallbacks=['group', 'Group', 'Program Name'],
            required=False,
        )
        other_group_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_OTHER_GROUP_COLUMN', 'other_group'),
            fallbacks=['other_group', 'Other Group', 'other group'],
            required=False,
        )
        other_group_reason_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_OTHER_GROUP_REASON_COLUMN', 'other_group_reason'),
            fallbacks=['other_group_reason', 'Other Group Reason', 'other group reason'],
            required=False,
        )
        last_group_col, _ = _resolve_column(
            schema_name,
            table_name,
            getattr(settings, 'KBC_LAST_GROUP_COLUMN', 'last_group'),
            fallbacks=['last_group', 'Last Group', 'last group'],
            required=False,
        )
        all_groups = _all_table_groups(schema, table, group_col, other_group_col)
    except ValueError:
        return JsonResponse({'detail': 'Server configuration error'}, status=500)

    select_fields = ['1 AS ok']
    select_fields.append(f'{id_col} AS student_id')
    if name_col:
        select_fields.append(f'{name_col} AS student_name')
    if group_col:
        select_fields.append(f'{group_col} AS student_group')
    if other_group_col:
        select_fields.append(f'{other_group_col} AS student_other_group')
    if other_group_reason_col:
        select_fields.append(f'{other_group_reason_col} AS student_other_group_reason')

    sql = (
        f"SELECT {', '.join(select_fields)} "
        f"FROM {schema}.{table} "
        f"WHERE LOWER({email_col}) = LOWER(%s) "
        "LIMIT 1"
    )

    with connection.cursor() as cursor:
        cursor.execute(sql, [email])
        row = cursor.fetchone()
        if row is None:
            return JsonResponse({'ok': False, 'detail': 'Please enter your Aptem email'}, status=401)
        columns = [col[0] for col in cursor.description]

    row_data = dict(zip(columns, row))

    response_data = {'ok': True, 'message': 'Attendance recorded successfully.'}
    student_id = _to_int(row_data.get('student_id'))
    student_name = _to_text(row_data.get('student_name'))
    primary_group, secondary_group = _split_groups(
        row_data.get('student_group'),
        row_data.get('student_other_group'),
    )
    raw_secondary_group = secondary_group
    secondary_group_reason = _to_text(row_data.get('student_other_group_reason'))
    student_group, secondary_group, available_groups = _normalize_student_groups(
        primary_group,
        raw_secondary_group,
        secondary_group_reason,
    )
    now = timezone.now()

    if student_id is None:
        return JsonResponse({'detail': 'Student ID is missing or invalid in source table.'}, status=500)

    existing_record = (
        AttendanceQR.objects.filter(student_id=student_id)
        .only('date')
        .order_by('-date')
        .first()
    )

    if existing_record and existing_record.date:
        next_allowed_at = existing_record.date + timedelta(hours=2)
        if now < next_allowed_at:
            next_allowed_local = timezone.localtime(next_allowed_at)
            return JsonResponse(
                {
                    'ok': False,
                    'detail': 'Attendance already recorded.',
                    'name': student_name,
                    'group': student_group,
                    'other_group': secondary_group,
                    'available_groups': available_groups,
                    'all_groups': all_groups,
                    'needs_selection': True,
                    'next_allowed_at': next_allowed_local.isoformat(),
                },
                status=429,
            )

    if not available_groups:
        return JsonResponse({'detail': 'No group is configured for this student.'}, status=400)

    if not selected_group:
        return JsonResponse(
            {
                'ok': False,
                'needs_selection': True,
                'message': 'Choose group and attendance reason.',
                'name': student_name,
                'group': student_group,
                'other_group': secondary_group,
                'available_groups': available_groups,
                'all_groups': all_groups,
            },
            status=200,
        )

    valid_groups = set(available_groups) | set(all_groups)

    if selected_group not in valid_groups:
        return JsonResponse(
            {
                'detail': 'Selected group is invalid.',
                'name': student_name,
                'group': student_group,
                'other_group': secondary_group,
                'available_groups': available_groups,
                'all_groups': all_groups,
            },
            status=400,
        )

    selected_from_other_module = bool(selected_group) and selected_group not in available_groups
    needs_reason = selected_from_other_module

    if needs_reason and attendance_reason not in valid_reasons:
        return JsonResponse(
            {
                'detail': 'Please choose attendance reason.',
                'name': student_name,
                'group': student_group,
                'other_group': secondary_group,
                'available_groups': available_groups,
                'all_groups': all_groups,
            },
            status=400,
        )

    saved_other_group = raw_secondary_group
    saved_second_module_reason = secondary_group_reason

    if not selected_from_other_module:
        selected_group = student_group
        attendance_reason = ''
    elif attendance_reason == 'transferred':
        _update_student_transfer_group(
            schema,
            table,
            id_col,
            student_id,
            raw_secondary_group,
            last_group_col,
            other_group_col,
            other_group_reason_col,
            selected_group,
        )
        saved_other_group = selected_group
        saved_second_module_reason = 'Transferred'

    record_data = {
        'student_id': student_id,
        'name': student_name,
        'group': primary_group,
        'other_group': saved_other_group,
        'second_module_reason': saved_second_module_reason,
        'selected_group': selected_group,
        'attendance_reason': attendance_reason,
        'email': email,
        'date': now,
        'time': timezone.localtime().time().replace(microsecond=0),
    }

    saved_record = AttendanceQR.objects.create(**record_data)
    next_allowed_at = saved_record.date + timedelta(hours=2)

    response_data['name'] = student_name
    response_data['group'] = student_group
    response_data['other_group'] = saved_other_group
    response_data['second_module_reason'] = saved_second_module_reason
    response_data['selected_group'] = selected_group
    response_data['attendance_reason'] = attendance_reason
    response_data['available_groups'] = available_groups
    response_data['all_groups'] = all_groups
    response_data['needs_selection'] = False
    response_data['next_allowed_at'] = timezone.localtime(next_allowed_at).isoformat()

    return JsonResponse(response_data)

