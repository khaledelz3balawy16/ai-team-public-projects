from django.db import migrations, models
from collections import defaultdict


def consolidate_responses(apps, schema_editor):
    """Merge multiple rows per learner into one row with all assessments in JSON."""
    SelfAssessmentQuizResponse = apps.get_model('psycho', 'SelfAssessmentQuizResponse')

    by_email = defaultdict(lambda: {'learner_id': None, 'learner_name': '', 'assessments': {}})

    for row in SelfAssessmentQuizResponse.objects.order_by('id'):
        email = (row.learner_email or '').strip().lower()
        if not email:
            continue
        by_email[email]['learner_id'] = row.learner_id
        by_email[email]['learner_name'] = row.learner_name or ''
        quiz_type = (row.assessment_type or 'unknown').strip()
        by_email[email]['assessments'][quiz_type] = {
            'answers': row.answers or {},
            'scores': row.scores or {},
            'total_score': row.total_score,
            'submitted_at': row.submitted_at.isoformat() if row.submitted_at else None,
        }

    SelfAssessmentQuizResponse.objects.all().delete()

    for email, data in by_email.items():
        SelfAssessmentQuizResponse.objects.create(
            learner_email=email,
            learner_id=data['learner_id'],
            learner_name=data['learner_name'],
            assessments=data['assessments'],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('psycho', '0002_selfassessmentquestion_selfassessmentquizresponse_and_more'),
    ]

    operations = [
        # 1. Add new assessments column
        migrations.AddField(
            model_name='selfassessmentquizresponse',
            name='assessments',
            field=models.JSONField(default=dict),
        ),
        # 2. Add created_at column (submitted_at is being replaced)
        migrations.AddField(
            model_name='selfassessmentquizresponse',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # 3. Migrate data — runs while old fields still exist
        migrations.RunPython(consolidate_responses, migrations.RunPython.noop),
        # 4. Remove old columns
        migrations.RemoveField(model_name='selfassessmentquizresponse', name='assessment_type'),
        migrations.RemoveField(model_name='selfassessmentquizresponse', name='answers'),
        migrations.RemoveField(model_name='selfassessmentquizresponse', name='scores'),
        migrations.RemoveField(model_name='selfassessmentquizresponse', name='total_score'),
        migrations.RemoveField(model_name='selfassessmentquizresponse', name='submitted_at'),
        # 5. Make learner_email unique (now safe — one row per learner)
        migrations.AlterField(
            model_name='selfassessmentquizresponse',
            name='learner_email',
            field=models.TextField(unique=True, db_index=True),
        ),
        # 6. Fix created_at to not be nullable
        migrations.AlterField(
            model_name='selfassessmentquizresponse',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        # 7. Update ordering meta
        migrations.AlterModelOptions(
            name='selfassessmentquizresponse',
            options={'ordering': ['-updated_at']},
        ),
    ]
