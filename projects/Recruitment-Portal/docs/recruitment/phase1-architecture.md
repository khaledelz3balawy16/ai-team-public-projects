# Phase 1 architecture

## Repository assessment before implementation

The inspected repository contained only a 20-byte `README.md`, a Python-oriented
`.gitignore`, and `.git/`. Git status was clean. No AGENTS.md was found. There was no
frontend directory/package.json, backend/manage.py, settings, environment file,
authentication model, database/Neon connection, migration, DRF/Channels/ASGI setup,
test framework, or established application naming convention to extend. The original
README heading and ignore rules were retained. Missing project contents were not assumed.

The implementation therefore adds `backend/config`, one domain app named
`backend/recruitment`, and `docs/recruitment`. No existing application or data was
replaced. There are no React interfaces or API endpoints in this phase.

## System and stack

The future public student portal accepts one track per anonymous application; the
future staff dashboard manages event configuration and reviews submissions. Both
will use the same Django domain and transactional services. Applicants are domain
records, not authentication users. Staff use the existing Django AUTH_USER_MODEL
mechanism (the standard auth.User in this initially empty repository).

Backend: Python 3.12+, Django **6.0.10**, DRF, Channels/Daphne, psycopg 3, PostgreSQL
on Neon. Implementation verification uses Python 3.13.12. Direct dependencies are
in `backend/requirements.txt`; the resolved verification environment is captured in
`backend/requirements-lock.txt`. No unrelated dependencies existed to upgrade.

Compatibility was checked against primary documentation:

- [Django 6.0 Python compatibility](https://docs.djangoproject.com/en/6.0/faq/install/)
- [Django 6.0.10 security fixes, November 3, 2026](https://docs.djangoproject.com/en/6.0/releases/6.0.10/)
- [DRF supported Django versions](https://www.django-rest-framework.org/)
- [Channels changelog, including Django 6.0 support](https://github.com/django/channels/blob/main/CHANGELOG.txt)
- [Neon pooling](https://neon.com/docs/connect/connection-pooling)

The planned frontend stack remains React 19, TypeScript 5.8, Vite 8 and Tailwind CSS
3. No frontend manifest or UI was created: no frontend was provided, and Phase 1
requires domain/project foundations only. Frontend scaffolding and compatibility
verification belong to the interface phase.

## Components and source structure

```text
backend/
  manage.py
  requirements.txt, requirements-lock.txt, .env.example
  config/
    base.py                 shared middleware, auth, DRF, templates
    database.py             credential-redacted PostgreSQL URL parser, mandatory TLS
    settings.py             explicit runtime environment and PostgreSQL connection
    migration_settings.py   explicit direct connection for migration operations
    offline.py              credential-free in-memory schema checks/generation
    test_settings.py        disposable in-memory tests
    postgres_test_settings.py optional loopback-only PostgreSQL tests
    urls.py, asgi.py, wsgi.py
  recruitment/
    apps.py, admin.py
    models/
      base.py, event.py, track.py, question.py, applicant.py,
      application.py, cv_document.py, status_history.py, __init__.py
    services/__init__.py     reserved for Phase 2; no submission implementation
    management/commands/seed_career_fair.py
    migrations/0001_initial.py
    tests/                  models, DB constraints, seed, configuration, permissions
docs/recruitment/
  phase1-architecture.md, database-schema.md
```

The HTTP ASGI application uses Channels ProtocolTypeRouter and Daphne. No WebSocket
route, consumer, notification feed or production channel layer is configured yet.
Authentication, CSRF, sessions, SecurityMiddleware and clickjacking protection remain
enabled. DRF defaults require staff authentication; there are no public model routes.

## Model and validation design

All ten domain models use UUID identities. Date/time fields are timezone aware
(`USE_TZ=True`, storage convention UTC). Mutable domain records have created/updated
timestamps; append-only conditions/history and CV metadata use their required
created/uploaded/changed timestamps. Options also have created/updated timestamps.

Events own tracks; applications independently reference an event, its selected track,
and an applicant identity shared across events. A normalized email expression unique
index and an event/applicant unique constraint provide concurrency-safe duplicate
protection. Typed JSON responses use stable option values, not translated labels.
CV records contain metadata and generated storage keys, never binary data or URLs.

See [database-schema.md](database-schema.md) for all columns, relationships, deletion
behaviors, indexes, condition semantics, and the BR-001–BR-020 responsibility map.

`ValidatedModel.save()` calls `full_clean()` for ordinary saves, including Admin.
This deliberately improves on Django's default save behavior. Django constraints
are also created in the database for row-local and uniqueness rules. Cross-table
checks (event/track, answer/track, option compatibility, graph ordering) are model
validation, **not PostgreSQL CHECK constraints**. QuerySet.update(), bulk_create(),
bulk_update(), direct SQL, concurrent writes and related-object changes can bypass
model validation. Phase 2 services must use transactions, row locks, explicit
validation and a consistent lock order; the model layer alone is not sufficient for
concurrent business workflows. Do not expose generic writable model viewsets.

## Security boundaries and operational configuration

- Runtime settings require a random secret, PostgreSQL URL and absolute private CV
  root. They load only `backend/.env`, without overriding process variables.
- `DJANGO_ENV` defaults to production and debug defaults off. Secure cookies and
  HTTPS redirection are enabled outside local debug mode. Deployment/proxy, HSTS,
  host and TLS certificate configuration require a later server deployment review.
- Connection parsing accepts only PostgreSQL URLs with TLS `require`, `verify-ca`
  or `verify-full`; explicit insecure modes are rejected. Credentials never appear
  in parser exceptions. Do not print settings, URL strings or `.env` contents.
- Runtime may use Neon's pooled host; `migration_settings` requires the explicit
  `DATABASE_MIGRATION_URL` and rejects `-pooler` hosts. Neither importing settings
  nor installing dependencies runs migrations.
- No real credentials or `.env` was found/created. `.env` variants and local private
  data are ignored; `.env.example` contains placeholders only.
- No public media mapping, CV upload/download endpoint or unauthenticated applicant
  endpoint exists. `CV_PRIVATE_STORAGE_ROOT` is not MEDIA_ROOT and no directories
  or files are served from it. Operators must place it outside every web root.
- Django Admin requires staff status plus model permissions. Staff membership alone
  does not grant candidate access. Application/answer/CV/history screens are read
  only; no unaudited status editing or CV safety overrides are offered. Catalog
  editing is supported, with stable identifiers protected by model validation.
- Applicant string representations use UUIDs. No custom PII logging was added.
  Admin's normal audit log can contain authorized form change details; restrict its
  access and retention. Keep names, answers, filenames, emails and URLs out of future
  request logs, exception payloads, analytics and metrics.
- Privacy acknowledgement/version, external CV sharing authorization and optional
  future communications opt-in are separate. The last defaults to false. These
  records do not by themselves determine the legal basis for processing.

## Seed safety

`seed_career_fair` requires both development/test environment settings and explicit
`RECRUITMENT_ALLOW_SEED=true`; debug alone is insufficient. Operators must confirm
the URL targets an isolated development database before enabling it. Environment
flags cannot prove that credentials point to a nonproduction server.

The command is atomic, inserts only missing configuration with get_or_create,
preserves existing row values and real candidate/application data, and never
deletes or updates records. It refuses to seed an existing non-draft example event.
It creates a DRAFT Career Fair 2026, four tracks, 22 questions, choice options and two
boolean visibility conditions. No applicant/user/CV is seeded. Repeated runs are
tested, including preservation of custom titles and existing applications.

## Verification and limitations

Tests use Django TestCase and a disposable in-memory SQLite database, independently
of runtime environment variables. Test setup applies auth/admin/session and
recruitment migrations to that temporary database and teardown destroys it.
DB-constraint tests intentionally bypass model.save with bulk writes to prove actual
unique/check constraints, in addition to ordinary validation tests.

No local PostgreSQL binaries or running Docker engine were available during initial
inspection. PostgreSQL/Neon execution and PostgreSQL-specific SQL are therefore an
outstanding verification step; SQLite success must not be described as PostgreSQL
verification. Optional `postgres_test_settings` reads only `TEST_DATABASE_URL`, requires
loopback and `test_recruitment_*`, and creates a separate `*_runner` test database.
It never imports runtime settings or reads DATABASE_URL. Do not use `--keepdb` unless
you explicitly manage that disposable test database. No Neon connection, project,
branch, production schema or production data was touched.

Actual verification on November 4, 2026:

| Check | Observed result |
| --- | --- |
| Django model/constraint/seed/security tests | 63 tests passed on disposable in-memory SQLite; its migrations were applied by the test runner and the database was destroyed afterward. |
| Django system check (`config.offline`) | No issues, zero silenced. |
| Migration drift (`makemigrations --check --dry-run`) | No changes detected. |
| Migration inspection | Ten CreateModel, five AddIndex, twelve AddConstraint operations, in addition to indexes/constraints embedded in CreateModel options. Plan and SQLite SQL generated successfully. |
| Dependency integrity (`pip check`) | No broken requirements found. |
| Python compileall | Completed without syntax errors. |
| Git diff whitespace check | Passed; Windows Git reported its usual LF-to-CRLF conversion notice for README. |
| PostgreSQL/Neon integration | Not run: no supplied isolated database or running local PostgreSQL. |

Runtime configuration remains intentionally incomplete until the operator supplies
DJANGO_SECRET_KEY, DATABASE_URL and CV_PRIVATE_STORAGE_ROOT; direct-connection
migration settings additionally require DATABASE_MIGRATION_URL. No `.env` containing
real credentials was created. This does not block the credential-free checks/tests.

The migration is initial and additive: ten CreateModel operations and their indexes
and constraints plus an AUTH_USER_MODEL swappable dependency. No existing tables
are altered, renamed or dropped. The offline plan/SQLite SQL can be inspected using
README commands without loading credentials. PostgreSQL SQL must be reviewed against
an isolated development connection before application.

## Phase boundaries and continuation

Phase 1 implements the schema, basic consistency validation, settings, migration,
development seed, permission-controlled Admin inspection and documentation/tests.
It does not implement student accounts, application APIs, UI forms/dashboards,
uploads, submission or resume tokens, condition evaluation, recruitment decisions,
exports, live monitoring, retention jobs or production deployment.

Phase 2 should implement transactional submission and status services, condition
evaluation and server-side required-answer validation, event publication/window and
active-track checks, protected anonymous draft tokens, typed API serializers,
rate limits, idempotency, private file validation/scanning/download authorization,
atomic attributed status history, retention/purge workflows and PostgreSQL integration
tests. Later stages can add React interfaces, aggregated statistics excluding drafts,
authorized exports, real-time notifications and server deployment. Do not start those
features by exposing unrestricted CRUD endpoints over the Phase 1 models.
