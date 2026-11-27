from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quizapp", "0015_add_onboarding_report_emailed_at")]
    operations = [migrations.CreateModel(
        name="LMSLoginAttempt",
        fields=[
            ("state", models.CharField(max_length=64, primary_key=True, serialize=False)),
            ("expires_at", models.DateTimeField(db_index=True)),
        ],
    )]
