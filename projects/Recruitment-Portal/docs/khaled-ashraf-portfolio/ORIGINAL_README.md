# Recruitment-Portal

Phase 1 Django recruitment foundation. No student UI, React dashboard or public API
is implemented. See [architecture](docs/recruitment/phase1-architecture.md) and
[database schema and rules](docs/recruitment/database-schema.md).

## Install (PowerShell, repository root)

Python 3.12+ is required; implementation was verified using Python 3.13.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
```

`requirements.txt` specifies supported direct dependencies; `requirements-lock.txt`
captures the resolved verification environment (including psycopg 3 and Daphne).

## Safe checks and tests without Neon

These settings never load `.env` or runtime DATABASE_URL. Tests create and destroy
an in-memory SQLite database; they do not verify PostgreSQL-specific behavior.

```powershell
.\.venv\Scripts\python.exe backend/manage.py check --settings=config.offline
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run --settings=config.offline
.\.venv\Scripts\python.exe backend/manage.py migrate --plan --settings=config.offline
.\.venv\Scripts\python.exe backend/manage.py sqlmigrate recruitment 0001 --settings=config.offline
.\.venv\Scripts\python.exe backend/manage.py test recruitment --settings=config.test_settings --noinput
.\.venv\Scripts\python.exe -m pip check
```

To verify on **disposable local PostgreSQL** with TLS, provision a dedicated role
allowed to create databases and set `TEST_DATABASE_URL` securely in your shell to a
loopback database named `test_recruitment_*`. Do not copy production credentials.
The runner creates/deletes a separate database suffixed `_runner`.

```powershell
.\.venv\Scripts\python.exe backend/manage.py test recruitment --settings=config.postgres_test_settings --noinput
```

## Isolated development Neon setup

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` privately: generate a random secret of at least 50 characters;
set DJANGO_ENV=development, local debug/hosts and an absolute private storage root.
Supply the pooled `DATABASE_URL` and direct `DATABASE_MIGRATION_URL` for an
**isolated development Neon branch**. TLS is required. No credentials are included
in this repository; `.env` is ignored. Never print the connection strings. No code
creates or replaces a Neon project/branch.

First inspect the connection target privately and confirm it is disposable or an
explicit development branch. Then inspect the plan and PostgreSQL SQL:

```powershell
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py migrate --plan --settings=config.migration_settings
.\.venv\Scripts\python.exe backend/manage.py sqlmigrate recruitment 0001 --settings=config.migration_settings
```

Only after verifying that safe target and reviewing the plan, apply migrations to it:

```powershell
.\.venv\Scripts\python.exe backend/manage.py migrate --settings=config.migration_settings
```

There is no automatic migration or production initialization. The foundation's
initial migration creates only recruitment tables; Django also needs its standard
auth/admin/session migrations when initializing a fresh development database.

## Example configuration and Admin

After safe development migration, set RECRUITMENT_ALLOW_SEED=true in `backend/.env`
only for that development database. Run the seed through the direct connection:

```powershell
.\.venv\Scripts\python.exe backend/manage.py seed_career_fair --settings=config.migration_settings
.\.venv\Scripts\python.exe backend/manage.py createsuperuser
.\.venv\Scripts\python.exe backend/manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/`. Use a development superuser, or staff explicitly
granted the necessary recruitment view/change permissions. Staff without model
permissions cannot inspect applicants. Event/track/question configuration is editable;
applications, answers, CV metadata and status history are inspection-only pending
audited workflows. No public CV links are exposed. Seed inserts a draft event,
four tracks, 22 questions and two visibility conditions; it preserves existing rows
and never creates candidates. Disable RECRUITMENT_ALLOW_SEED after use.

Daphne's HTTP-only ASGI entry point is `config.asgi:application`; future WebSocket
consumers/shared channel layers and production server settings remain out of scope.

Phase 2 will add submission/status services, condition evaluation, private CV
validation/scanning/access, protected draft resume, APIs and frontend workflows.
