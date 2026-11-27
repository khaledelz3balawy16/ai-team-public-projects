from dataclasses import dataclass
from django.conf import settings
from django.db import connection


@dataclass
class SimpleUser:
    username: str = ''
    email: str = ''
    first_name: str = ''
    last_name: str = ''
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True
    is_authenticated: bool = True


def _quote_table_name(table_name: str) -> str:
    return connection.ops.quote_name(table_name)


def get_auth_user_tables() -> list[str]:
    configured_tables = getattr(settings, 'AUTH_USER_TABLES', ['user_auth', 'auth_user'])
    try:
        existing_tables = set(connection.introspection.table_names())
    except Exception:
        return []

    return [table_name for table_name in configured_tables if table_name in existing_tables]


def get_auth_user_table() -> str | None:
    tables = get_auth_user_tables()
    return tables[0] if tables else None


def get_db_user_by_email(email: str):
    table_names = get_auth_user_tables()
    if not table_names:
        return None

    for table_name in table_names:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    f"SELECT username, first_name, last_name, email, is_staff, is_superuser, is_active FROM {_quote_table_name(table_name)} WHERE lower(email)=lower(%s) LIMIT 1",
                    [email],
                )
                row = cur.fetchone()
        except Exception:
            continue

        if not row:
            continue

        username, first_name, last_name, email, is_staff, is_superuser, is_active = row
        return SimpleUser(username=username or '', email=email or '', first_name=first_name or '', last_name=last_name or '', is_staff=bool(is_staff), is_superuser=bool(is_superuser), is_active=bool(is_active))

    return None


def get_db_user_by_login(identifier: str):
    table_names = get_auth_user_tables()
    if not table_names:
        return None

    login = (identifier or '').strip()
    if not login:
        return None

    for table_name in table_names:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT username, first_name, last_name, email, password, is_staff, is_superuser, is_active
                    FROM {_quote_table_name(table_name)}
                    WHERE lower(email)=lower(%s) OR lower(username)=lower(%s)
                    LIMIT 1
                    """,
                    [login, login],
                )
                row = cur.fetchone()
        except Exception:
            continue

        if not row:
            continue

        username, first_name, last_name, email, password, is_staff, is_superuser, is_active = row
        user = SimpleUser(
            username=username or '',
            email=email or '',
            first_name=first_name or '',
            last_name=last_name or '',
            is_staff=bool(is_staff),
            is_superuser=bool(is_superuser),
            is_active=bool(is_active),
        )
        return user, password or ''

    return None


def create_db_user(email: str, name: str, azure_id: str | None):
    table_name = get_auth_user_table()
    if not table_name:
        return None

    first_name = name.split(' ')[0] if name else ''
    last_name = ' '.join(name.split(' ')[1:]) if name and len(name.split(' ')) > 1 else ''
    base_username = (azure_id or (email.split('@')[0] if email else 'user'))
    username = base_username
    quoted_table = _quote_table_name(table_name)

    try:
        with connection.cursor() as cur:
            # ensure unique username
            suffix = 1
            while True:
                cur.execute(f'SELECT 1 FROM {quoted_table} WHERE username=%s LIMIT 1', [username])
                if not cur.fetchone():
                    break
                username = f"{base_username}{suffix}"
                suffix += 1

            try:
                cur.execute(
                    f'INSERT INTO {quoted_table} (username, password, first_name, last_name, email, is_staff, is_active, is_superuser, date_joined) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)',
                    [username, '', first_name, last_name, email, False, True, False],
                )
            except Exception:
                cur.execute(
                    f'INSERT INTO {quoted_table} (username, password, first_name, last_name, email, is_staff, is_active, is_superuser) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                    [username, '', first_name, last_name, email, False, True, False],
                )

            return SimpleUser(username=username, email=email, first_name=first_name, last_name=last_name, is_staff=False, is_superuser=False, is_active=True)
    except Exception:
        return None
