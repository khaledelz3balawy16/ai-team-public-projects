"""Capture imported Review changes without scanning or assigning feedback."""
from django.db import migrations


SQL = '\nSET LOCAL lock_timeout = \'3s\';\nSET LOCAL statement_timeout = \'30s\';\nDO $$\nBEGIN\n  IF to_regclass(\'"Learner".reviews\') IS NULL THEN\n    RAISE EXCEPTION \'Review source table is missing\';\n  END IF;\n  IF to_regclass(\'"Feedback".review_feedback_outbox\') IS NOT NULL\n     AND obj_description(to_regclass(\'"Feedback".review_feedback_outbox\'), \'pg_class\')\n         IS DISTINCT FROM \'LMS review feedback change outbox v1\' THEN\n    RAISE EXCEPTION \'An unrecognized review feedback outbox already exists\';\n  END IF;\nEND;\n$$;\nCREATE TABLE IF NOT EXISTS "Feedback".review_feedback_outbox (\n  source_review_id bigint PRIMARY KEY,\n  requested_version bigint NOT NULL DEFAULT 1 CHECK (requested_version > 0),\n  processed_version bigint NOT NULL DEFAULT 0,\n  requested_at timestamptz NOT NULL DEFAULT clock_timestamp(),\n  processed_at timestamptz,\n  CHECK (processed_version >= 0 AND processed_version <= requested_version)\n);\nCOMMENT ON TABLE "Feedback".review_feedback_outbox IS\n  \'LMS review feedback change outbox v1\';\nCREATE INDEX IF NOT EXISTS review_feedback_outbox_pending_idx\n  ON "Feedback".review_feedback_outbox (requested_at, source_review_id)\n  WHERE processed_version < requested_version;\nREVOKE ALL ON "Feedback".review_feedback_outbox FROM PUBLIC;\n\nDO $$\nBEGIN\n  IF to_regprocedure(\'"Feedback".capture_review_feedback_change()\') IS NOT NULL\n     AND obj_description(to_regprocedure(\'"Feedback".capture_review_feedback_change()\'), \'pg_proc\')\n         IS DISTINCT FROM \'LMS review feedback change capture v1\' THEN\n    RAISE EXCEPTION \'An unrecognized review feedback trigger function already exists\';\n  END IF;\nEND;\n$$;\nCREATE OR REPLACE FUNCTION "Feedback".capture_review_feedback_change()\nRETURNS trigger\nLANGUAGE plpgsql\nSECURITY DEFINER\nSET search_path = pg_catalog, pg_temp\nAS $$\nBEGIN\n  INSERT INTO "Feedback".review_feedback_outbox AS pending\n      (source_review_id, requested_version, requested_at)\n  VALUES (NEW.id, 1, clock_timestamp())\n  ON CONFLICT (source_review_id) DO UPDATE SET\n      requested_version = pending.requested_version + 1,\n      requested_at = EXCLUDED.requested_at;\n  RETURN NEW;\nEND;\n$$;\nCOMMENT ON FUNCTION "Feedback".capture_review_feedback_change() IS\n  \'LMS review feedback change capture v1\';\nREVOKE ALL ON FUNCTION "Feedback".capture_review_feedback_change() FROM PUBLIC;\n\nDO $$\nBEGIN\n  IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=\'"Learner".reviews\'::regclass\n             AND tgname IN (\'review_feedback_capture_insert\',\'review_feedback_capture_update\')\n             AND (tgfoid <> \'"Feedback".capture_review_feedback_change()\'::regprocedure\n                  OR tgisinternal)) THEN\n    RAISE EXCEPTION \'An CHANGE_ME trigger uses a review feedback capture name\';\n  END IF;\n  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=\'"Learner".reviews\'::regclass\n                 AND tgname=\'review_feedback_capture_insert\') THEN\n    CREATE TRIGGER review_feedback_capture_insert\n    AFTER INSERT ON "Learner".reviews FOR EACH ROW\n    WHEN (NEW.completed_date IS NOT NULL)\n    EXECUTE FUNCTION "Feedback".capture_review_feedback_change();\n  END IF;\n  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=\'"Learner".reviews\'::regclass\n                 AND tgname=\'review_feedback_capture_update\') THEN\n    CREATE TRIGGER review_feedback_capture_update\n    AFTER UPDATE OF status, completed_date ON "Learner".reviews FOR EACH ROW\n    WHEN (OLD.status IS DISTINCT FROM NEW.status\n          OR OLD.completed_date IS DISTINCT FROM NEW.completed_date)\n    EXECUTE FUNCTION "Feedback".capture_review_feedback_change();\n  END IF;\nEND;\n$$;\n'

# Stop capturing without dropping queued work or needing ownership of the source
# table. Reapplying the forward migration restores capture and preserves versions.
DISABLE_SQL = r'''
SET LOCAL lock_timeout = '3s';
CREATE OR REPLACE FUNCTION "Feedback".capture_review_feedback_change()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$ BEGIN RETURN NEW; END; $$;
COMMENT ON FUNCTION "Feedback".capture_review_feedback_change() IS
  'LMS review feedback change capture v1';
REVOKE ALL ON FUNCTION "Feedback".capture_review_feedback_change() FROM PUBLIC;
'''


def install(apps, schema_editor):
    if schema_editor.connection.vendor == 'sqlite':
        return
    if schema_editor.connection.vendor != 'postgresql' or schema_editor.connection.alias != 'default':
        raise RuntimeError('Review feedback capture requires the canonical PostgreSQL default database.')
    schema_editor.execute(SQL, params=None)


def disable(apps, schema_editor):
    if schema_editor.connection.vendor == 'sqlite':
        return
    if schema_editor.connection.vendor != 'postgresql' or schema_editor.connection.alias != 'default':
        raise RuntimeError('Review feedback capture requires the canonical PostgreSQL default database.')
    schema_editor.execute(DISABLE_SQL, params=None)


class Migration(migrations.Migration):
    dependencies = [('engagement_api', '0014_feedback_email_ticket_close')]
    operations = [migrations.RunPython(install, disable)]
