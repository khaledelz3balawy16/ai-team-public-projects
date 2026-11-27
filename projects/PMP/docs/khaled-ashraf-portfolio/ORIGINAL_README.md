# PMP AI Assessment Platform

Standalone Django REST Framework + React assessment flow backed by PostgreSQL.

## Setup

The project is split into `BACKEND` and `FRONTEND`. Copy `BACKEND/.env.example` values into your environment and create the PostgreSQL database, then run:

```powershell
cd BACKEND
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_pmp_questions
python manage.py createsuperuser
python manage.py runserver
```

In a second terminal:

```powershell
cd FRONTEND
npm install
npm run dev
```

Open `http://localhost:5173/pmp-assessment`. The six seed questions are development fixtures; a 50/60-question exam requires importing enough valid active questions first. Use Django admin at `http://localhost:8000/admin/` or the staff-only React question bank at `/admin/pmp-question-bank`.

For a quick local SQLite smoke test only, set `PMP_USE_SQLITE=true`. Production should use PostgreSQL.
