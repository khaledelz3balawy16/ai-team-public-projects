-- Adds curriculum.cohorts.excluded_holiday_ids -- the holidays a human has
-- unticked in the cohort drawer's "Bank holidays in this cohort's period"
-- list, now that each one carries a checkbox.
--
-- A deny-list, not the selection itself: every England bank holiday inside a
-- cohort's own start_date..end_date still applies by default (see
-- holidays_in_range / holiday_ids on this same table), and this column only
-- names the ones turned off. That is why the column defaults to '[]' rather
-- than to "every holiday" -- an empty deny-list already means "nothing
-- excluded", which is exactly today's behaviour for every existing cohort, so
-- no backfill is needed. It is also why a holiday that enters a cohort's
-- period later (its dates move, or GOV.UK publishes a new one) is selected by
-- default too: nothing named it as excluded, so nothing takes it out.
--
-- Equivalent to Django migration 0061_cohort_excluded_holiday_ids. Forward-only
-- and safe to re-run: `add column if not exists` is a no-op once applied.
--
-- After running this in the SQL editor, mark the migration as already applied
-- so `manage.py migrate` does not try to run it again -- see the
-- django_migrations insert at the bottom, or run:
--   python manage.py migrate curriculum_api 0061 --fake

BEGIN;

ALTER TABLE curriculum."cohorts"
  ADD COLUMN IF NOT EXISTS excluded_holiday_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

-- Portfolio: top-level data statement omitted.

COMMIT;
