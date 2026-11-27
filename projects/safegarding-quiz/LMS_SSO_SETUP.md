# LMS sign-in deployment

Changes are required in both this repository and the adjacent `LMS_v2` repository.
The feature defaults to disabled until both applications are deployed and configured.

## Configuration

Generate a dedicated random secret with at least 32 characters (for example,
`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Store the same value
in the two backend environments. Never put it in frontend variables or Git.

Safeguarding backend environment:

```dotenv
LMS_SSO_ENABLED=True
LMS_SSO_SECRET=<shared-random-secret>
LMS_BASE_URL=https://lms.kentbusinesscollege.org
FRONTEND_BASE_URL=https://safeguarding.kentbusinesscollege.net
```

LMS backend environment:

```dotenv
SAFEGUARDING_SSO_SECRET=<same-shared-random-secret>
SAFEGUARDING_SSO_CALLBACK_URL=https://safeguarding.kentbusinesscollege.net/auth/lms/callback
```

For local testing, set LMS_BASE_URL to the local LMS frontend and set the callback
to `http://127.0.0.1:5173/auth/lms/callback` (or your Safeguarding frontend port).
The LMS frontend must proxy `/login_api/` to its backend as it does for normal login.
The learner home page's Safeguarding button opens the public Safeguarding URL.
For local testing, set the LMS frontend's `VITE_SAFEGUARDING_URL` to the local
Safeguarding frontend URL before starting or building it.

The Safeguarding production frontend uses `/api` on its own origin. If your API
is hosted elsewhere, set `VITE_API_BASE_URL` to its full HTTPS `/api` URL before
building, and allow the frontend origin on that backend. Development defaults
to `http://127.0.0.1:8000/api`.

## Deploy

1. Deploy the LMS backend and frontend changes and configure its secret/callback.
2. With the feature still disabled, deploy the Safeguarding backend changes and run
   `python manage.py migrate quizapp` against its default database. Review pending
   migrations first with `python manage.py migrate quizapp --plan`. Migration 0016
   creates the temporary login-attempt table. Existing pending migrations retain
   their own database requirements; do not blindly run them on a new database.
3. Configure the Safeguarding secret and enable `LMS_SSO_ENABLED=True`, restart its
   backend, and deploy its frontend build (`npm run build`).
4. Ensure `/auth/lms/callback` serves the Safeguarding SPA, and `/login_api/` is
   routed to the LMS backend. Use HTTPS for both public applications.
5. Open Safeguarding in a private window, sign in on LMS, and verify you return to
   `/onboarding`. Repeat with an existing session, Microsoft sign-in, an existing
   Safeguarding learner and an LMS account without a Safeguarding record.

No production deployment or database migration is performed by this code change.

## Behavior

- LMS authenticates using its existing `login."Login_accounts"` and session logic.
- Only LMS can issue the signed assertion. It expires after 60 seconds and is
  bound to a browser verifier held in Safeguarding's sessionStorage.
- The ten-minute login attempt can be consumed once, atomically across workers.
  Assertion transport uses a URL fragment; the callback immediately removes it.
- An existing WSMS record is matched by normalized email, preserving its answers.
  A new account gets a WSMS record and starts the normal onboarding flow. PostgreSQL
  transaction locks serialize SSO provisioning for the same email.
- New records contain the LMS name/email. Programme, coach and manager details
  remain empty until populated by the existing data process; LMS login alone
  does not supply these fields.
- LMS roles do not grant access to other people's Safeguarding records.
- Email-only login and direct Safeguarding password/Microsoft login are disabled
  in SSO mode. Previously issued learner tokens become invalid when switching
  modes. Safeguarding sessions retain the existing eight-hour lifetime; LMS
  logout does not revoke an already-issued Safeguarding token.

## Automated validation

```text
# Safeguarding backend, isolated SQLite database and mocked WSMS provisioning
python manage.py test quizapp.test_lms_sso --settings=core.settings_test
# LMS backend, isolated settings; no production database access
python manage.py test login.tests_safeguarding_sso --settings=config.settings_sqlite_test
```
