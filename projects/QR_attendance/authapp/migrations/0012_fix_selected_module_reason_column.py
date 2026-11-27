from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0011_rebuild_attendanceqr_selected_module_reason'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'attendance_QR'
                    AND column_name = 'attendance_reason'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'attendance_QR'
                    AND column_name = 'selected_module_reason'
                ) THEN
                    ALTER TABLE "attendance_QR"
                    RENAME COLUMN "attendance_reason" TO "selected_module_reason";
                END IF;
            END
            $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'attendance_QR'
                    AND column_name = 'selected_module_reason'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'attendance_QR'
                    AND column_name = 'attendance_reason'
                ) THEN
                    ALTER TABLE "attendance_QR"
                    RENAME COLUMN "selected_module_reason" TO "attendance_reason";
                END IF;
            END
            $$;
            """,
        ),
    ]
