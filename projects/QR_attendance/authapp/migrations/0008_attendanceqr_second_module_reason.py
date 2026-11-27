from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0007_attendanceqr_student_id_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendanceqr',
            name='second_module_reason',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunSQL(
            sql="""
            UPDATE "attendance_QR"
            SET "second_module_reason" = COALESCE("second_module", '')
            WHERE "second_module_reason" = '';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
