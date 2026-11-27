from django.db import migrations, models


def copy_primary_key_to_student_id(apps, schema_editor):
    AttendanceQR = apps.get_model('authapp', 'AttendanceQR')
    AttendanceQR.objects.filter(student_id__isnull=True).update(student_id=models.F('id'))


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0006_attendanceqr_attendance_reason_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendanceqr',
            name='student_id',
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(copy_primary_key_to_student_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='attendanceqr',
            name='student_id',
            field=models.BigIntegerField(db_index=True),
        ),
        migrations.RunSQL(
            sql="""
            SELECT setval(
                pg_get_serial_sequence('"attendance_QR"', 'id'),
                COALESCE((SELECT MAX(id) FROM "attendance_QR"), 1),
                true
            );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
