# Server Setup Guide — psycho-dash on srv1281908

## 1. Clone repo & create venv

```bash
cd /var/www
git clone <your-repo-url> psycho-dash
cd psycho-dash

python3 -m venv venv
venv/bin/pip install -r backend/requirements.txt
```

## 2. Create .env

```bash
cp backend/.env.example backend/.env
nano backend/.env
# Fill in: SECRET_KEY, DATABASE_URL (Neon), AZURE_*, FRONTEND_URL
```

## 3. Run migrations (creates tables in Neon)

```bash
venv/bin/python backend/manage.py migrate
```

## 4. Setup log directory

```bash
mkdir -p /var/log/psycho-dash
chown www-data:www-data /var/log/psycho-dash
```

## 5. Install systemd service

```bash
cp psycho-dash.service /etc/systemd/system/gunicorn-psycho-dash.service
systemctl daemon-reload
systemctl enable gunicorn-psycho-dash
systemctl start gunicorn-psycho-dash
systemctl status gunicorn-psycho-dash
```

## 6. Build frontend

```bash
cd /var/www/psycho-dash/frontend
npm ci
npm run build
# Output: /var/www/psycho-dash/backend/staticfiles/dist/
```

## 7. OLS Virtual Host

Follow instructions in `openlitespeed.conf`
Doc root: `/var/www/psycho-dash/backend/staticfiles`

## 8. Azure OAuth — register redirect URI

In Azure Portal → App Registration → Authentication:
Add redirect URI: `https://psycho.kentbusinesscollege.net/api/auth/callback/`

## 9. Test auth flow

Visit: `https://psycho.kentbusinesscollege.net/api/auth/login/`
→ Microsoft login → redirect back → cookie set → `/` shows dashboard

## 10. Migrate data from WordPress MySQL

```bash
# Export from WordPress (run on WP server)
mysql -u root -p wordpress_db \
  -e "SELECT * FROM wp_assessment_scores" \
  > assessment_scores_export.sql

# Or via Python migration script:
venv/bin/python backend/manage.py migrate_wp_data \
  --mysql-host=localhost \
  --mysql-db=wordpress_db \
  --mysql-user=root \
  --mysql-password=xxx
```

## 11. "Login to Student Dashboard" redirect (from the Kent site)

The Kent "More sites" modal has a button that opens the dashboard with the
learner's email in the query string, e.g.:

```html
<a class="opts-btn opts-btn-student"
   href="https://psycho.kentbusinesscollege.net/?email=Mahmoud.Fouda%40kentbusinesscollege.com"
   target="_blank" rel="noopener">Login to Student Dashboard</a>
```

How it works:

1. The frontend reads `?email=` and forwards it on every `/api/*` request
   (`frontend/src/api/client.ts`).
2. The backend resolves that email against **`kbc_users_data`** (over the
   separate `USER_DATABASE_URL` connection) to get the learner's `id`, `name`,
   and `email`.
3. Those values are attached to every stored `self_assessment_quiz_responses`
   row (`learner_id`, `learner_name`, `learner_email`).

Required `.env` settings for this flow:

```bash
USER_DATABASE_URL=CHANGE_ME
KBC_USERS_TABLE=kbc_users_data
PUBLIC_DASHBOARD_ENABLED=True      # required to honor the ?email= redirect
KBC_REQUIRE_KNOWN_EMAIL=True       # only let real kbc_users_data learners in
```

> The `users` database is read-only and is **not** migrated. To point the
> WordPress button anywhere else, just change its `href` to the dashboard URL
> with `?email=<learner-email>`.

## Future deploys

```bash
bash /var/www/psycho-dash/deploy.sh
```
