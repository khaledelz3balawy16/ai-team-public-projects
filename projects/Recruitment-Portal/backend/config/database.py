"""Parse PostgreSQL URLs without including credentials in error messages."""
from urllib.parse import parse_qs, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def postgres_database(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port or 5432
        query = parse_qs(parsed.query)
        if parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname or not parsed.path.strip("/"):
            raise ValueError
        sslmode = query.get("sslmode", ["require"])[0]
        if sslmode not in ("require", "verify-ca", "verify-full"):
            raise ValueError
    except (ValueError, TypeError):
        raise ImproperlyConfigured("A valid PostgreSQL URL with required TLS is needed.") from None
    options = {"sslmode": sslmode, "connect_timeout": 10}
    if "channel_binding" in query:
        options["channel_binding"] = query["channel_binding"][0]
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": port,
        "CONN_MAX_AGE": 0,
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "OPTIONS": options,
    }
