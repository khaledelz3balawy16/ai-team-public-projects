from django.conf import settings
from django.db import migrations


def quote_identifier(connection, value):
    return connection.ops.quote_name(value)


def backfill_second_module_reason(apps, schema_editor):
    connection = schema_editor.connection
    schema_name = getattr(settings, 'KBC_TABLE_SCHEMA', 'public')
    table_name = getattr(settings, 'KBC_TABLE_NAME', 'student_alternative_details')
    id_col = getattr(settings, 'KBC_ID_COLUMN', 'ID')
    reason_col = getattr(settings, 'KBC_OTHER_GROUP_REASON_COLUMN', 'other_group_reason')

    attendance_table = quote_identifier(connection, 'attendance_QR')
    source_table = f"{quote_identifier(connection, schema_name)}.{quote_identifier(connection, table_name)}"
    source_id_col = quote_identifier(connection, id_col)
    source_reason_col = quote_identifier(connection, reason_col)

    sql = f"""
        UPDATE {attendance_table} AS attendance
        SET second_module_reason = COALESCE(source.{source_reason_col}, '')
        FROM {source_table} AS source
        WHERE attendance.student_id = source.{source_id_col}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0008_attendanceqr_second_module_reason'),
    ]

    operations = [
        migrations.RunPython(backfill_second_module_reason, migrations.RunPython.noop),
    ]
