-- England's bank holidays, as published by GOV.UK.
--
-- Source: https://www.gov.uk/bank-holidays.json -- the feed behind the
-- https://www.gov.uk/bank-holidays page. It carries three divisions; England
-- takes the 'england-and-wales' one, England and Wales sharing a single set of
-- bank holidays. The division is stored so a row states which set it came from.
--
-- Each event carries a title, a date, a notes field (only ever 'Substitute day',
-- marking a holiday moved because the real date fell on a weekend) and a bunting
-- flag (whether GOV.UK marks the day as a flag-flying one). All four are kept.
--
-- Keyed on (division, holiday_date): the feed never lists two events on the same
-- date within a division. fetched_at is the last time the feed still listed the
-- date, so it moves on every load; updated_at moves only when the holiday itself
-- changed. A stale load is the gap between the two.
--
-- This is reference data nobody here edits -- distinct from curriculum.holidays,
-- which holds this organisation's own authored closure periods.
--
-- The seed below is the feed as it stood on 2026-09-13: 83 holidays spanning
-- 2019-01-01 to 2028-12-26. Re-running refreshes a changed title/note rather than
-- duplicating the row. GOV.UK publishes a rolling window of roughly ten years,
-- so keep it current with:
--
--     python manage.py fetch_england_holidays --apply
--
-- Forward-only, idempotent, non-destructive. Safe to re-run.

BEGIN;

CREATE SCHEMA IF NOT EXISTS curriculum;

CREATE TABLE IF NOT EXISTS curriculum.england_holidays (
    id            varchar(128)  PRIMARY KEY,
    division      varchar(64)   NOT NULL DEFAULT 'england-and-wales',
    title         varchar(255)  NOT NULL,
    holiday_date  date          NOT NULL,
    notes         varchar(255)  NOT NULL DEFAULT '',
    bunting       boolean       NOT NULL DEFAULT false,
    fetched_at    timestamptz,
    created_at    timestamptz   NOT NULL DEFAULT now(),
    updated_at    timestamptz   NOT NULL DEFAULT now()
);

-- One row per date per division is the rule the feed itself follows, and it is
-- what makes the re-runnable upsert below safe.
CREATE UNIQUE INDEX IF NOT EXISTS england_holidays_division_date_idx
    ON curriculum.england_holidays (division, holiday_date);

-- Every read is "which bank holidays fall in this range", for scheduling.
CREATE INDEX IF NOT EXISTS england_holidays_date_idx
    ON curriculum.england_holidays (holiday_date);

-- Portfolio: top-level data statement omitted.

COMMIT;
