from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AssessmentScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(db_index=True, unique=True)),
                ('wellbeing_score',      models.JSONField(blank=True, null=True)),
                ('psychological_score',  models.JSONField(blank=True, null=True)),
                ('personality_score',    models.JSONField(blank=True, null=True)),
                ('career_score',         models.JSONField(blank=True, null=True)),
                ('riasec_score',         models.JSONField(blank=True, null=True)),
                ('ei_score',             models.JSONField(blank=True, null=True)),
                ('work_score',           models.JSONField(blank=True, null=True)),
                ('cognitive_score',      models.JSONField(blank=True, null=True)),
                ('logical_score',        models.JSONField(blank=True, null=True)),
                ('knowledge_score',      models.JSONField(blank=True, null=True)),
                ('skills_score',         models.JSONField(blank=True, null=True)),
                ('behaviors_score',      models.JSONField(blank=True, null=True)),
                ('learning_style_score', models.JSONField(blank=True, null=True)),
                ('career_recommendations', models.JSONField(blank=True, null=True)),
                ('skills_to_develop',    models.JSONField(blank=True, null=True)),
                ('career_path_last_shown', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'assessment_scores'},
        ),
    ]
