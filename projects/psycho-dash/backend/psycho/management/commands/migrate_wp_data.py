"""
Management command to migrate assessment data from WordPress MySQL → Neon Postgres.

Usage:
  python manage.py migrate_wp_data \
    --mysql-host=localhost \
    --mysql-db=wordpress_db \
    --mysql-user=root \
    --mysql-password=xxx \
    [--wp-prefix=wp_]         # default: wp_
    [--dry-run]
"""
import json
import MySQLdb  # pip install mysqlclient
from django.core.management.base import BaseCommand
from psycho.models import AssessmentScore


FIELD_MAP = {
    # WP column           : Django field
    'wellbeing_score':     'wellbeing_score',
    'Psychological_score': 'psychological_score',
    'Personality_score':   'personality_score',
    'Career_score':        'career_score',
    'RIASEC_score':        'riasec_score',
    'EI_score':            'ei_score',
    'Work_score':          'work_score',
    'CognitiveSkills_score':  'cognitive_score',
    'LogicalSkills_score':    'logical_score',
    'Knowledge_score':     'knowledge_score',
    'Skills_score':        'skills_score',
    'Behaviors_score':     'behaviors_score',
    'learning_style_score':'learning_style_score',
}


class Command(BaseCommand):
    help = 'Migrate wp_assessment_scores from MySQL to Neon Postgres'

    def add_arguments(self, parser):
        parser.add_argument('--mysql-host',     default='localhost')
        parser.add_argument('--mysql-db',       required=True)
        parser.add_argument('--mysql-user',     required=True)
        parser.add_argument('--mysql-password', required=True)
        parser.add_argument('--mysql-port',     type=int, default=3306)
        parser.add_argument('--wp-prefix',      default='wp_')
        parser.add_argument('--dry-run',        action='store_true')

    def handle(self, *args, **opts):
        conn = MySQLdb.connect(
            host=opts['mysql_host'],
            user=opts['mysql_user'],
            password=opts['mysql_password'],
            db=opts['mysql_db'],
            port=opts['mysql_port'],
            charset='utf8mb4',
        )
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        table  = f"{opts['wp_prefix']}assessment_scores"

        cursor.execute(f"SELECT * FROM `{table}`")
        rows = cursor.fetchall()
        self.stdout.write(f"Found {len(rows)} rows in {table}")

        created = updated = skipped = 0

        for row in rows:
            email = (row.get('email') or '').strip().lower()
            if not email:
                skipped += 1
                continue

            defaults = {}
            for wp_col, django_field in FIELD_MAP.items():
                raw = row.get(wp_col)
                if raw:
                    try:
                        defaults[django_field] = json.loads(raw)
                    except json.JSONDecodeError:
                        defaults[django_field] = None

            if opts['dry_run']:
                self.stdout.write(f"  [dry-run] Would upsert: {email}")
                continue

            obj, was_created = AssessmentScore.objects.update_or_create(
                email=email,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        conn.close()
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Done — created={created} updated={updated} skipped={skipped}"
            )
        )
