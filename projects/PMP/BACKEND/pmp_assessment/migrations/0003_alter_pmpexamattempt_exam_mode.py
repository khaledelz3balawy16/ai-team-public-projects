from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pmp_assessment", "0002_alter_pmpexamattempt_exam_mode")]

    operations = [
        migrations.AlterField(
            model_name="pmpexamattempt",
            name="exam_mode",
            field=models.CharField(
                choices=[
                    ("random", "Random"),
                    ("domain", "Domain"),
                    ("topic", "Topic"),
                    ("exam_simulator", "PMP exam simulator"),
                    ("full_practice", "Full question practice"),
                    ("practice_1", "Practice exam 1"),
                    ("practice_2", "Practice exam 2"),
                    ("practice_3", "Practice exam 3"),
                    ("practice_4", "Practice exam 4"),
                ],
                max_length=20,
            ),
        )
    ]
