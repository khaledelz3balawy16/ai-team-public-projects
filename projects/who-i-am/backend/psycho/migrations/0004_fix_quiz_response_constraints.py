from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('psycho', '0003_consolidate_quiz_responses'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE self_assessment_quiz_responses
                    ALTER COLUMN learner_id DROP NOT NULL,
                    ALTER COLUMN assessments SET DEFAULT '{}',
                    ALTER COLUMN assessments DROP NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE self_assessment_quiz_responses
                    ALTER COLUMN learner_id SET NOT NULL,
                    ALTER COLUMN assessments DROP DEFAULT,
                    ALTER COLUMN assessments SET NOT NULL;
            """,
        ),
    ]
