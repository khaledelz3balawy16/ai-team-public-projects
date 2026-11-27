-- Review Type becomes the canonical classification of a Curriculum Review,
-- replacing curriculum.review_templates.coach_surface.
--
-- Why: coach_surface was a two-value routing enum ('mcr' | 'progress_review')
-- with no identity of its own -- a third kind of Review could not exist
-- without a CHECK-constraint change and a deploy. A Review Type is a real
-- record, so Curriculum can add "Career Review" / "Six Week Review" from the
-- UI, and Coach still routes by a STABLE code instead of a display name.
--
-- Review Type classifies ONLY. It carries no recurrence (a Monthly Coaching
-- Meeting scheduled every 6 weeks stays valid), no questions, no signatures,
-- no eligibility -- those all remain on the Review Template.
--
-- Run against Neon directly -- see backend/sql conventions.
BEGIN;

CREATE TABLE IF NOT EXISTS curriculum.review_types (
    id varchar(128) PRIMARY KEY,
    name varchar(255) NOT NULL DEFAULT '',
    -- Derived once from the name at creation and then FROZEN: renaming a type
    -- must never change how its Reviews are routed.
    code varchar(64) NOT NULL,
    -- A system type is seeded here, is referenced by code in application
    -- logic, and can never be deleted or deactivated from the UI.
    is_system boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    created_by varchar(255) NOT NULL DEFAULT '',
    updated_by varchar(255) NOT NULL DEFAULT '',
    created_at timestamp NOT NULL DEFAULT current_timestamp,
    updated_at timestamp NOT NULL DEFAULT current_timestamp
);

CREATE UNIQUE INDEX IF NOT EXISTS review_types_code_uniq
    ON curriculum.review_types (lower(code));

-- Two active types may not share a name, compared case-insensitively with
-- surrounding whitespace collapsed -- the same comparison review_types.py
-- makes before it writes, so the UI reports the clash instead of the database.
CREATE UNIQUE INDEX IF NOT EXISTS review_types_active_name_uniq
    ON curriculum.review_types (lower(btrim(name)))
    WHERE is_active = true;

-- Portfolio: top-level data statement omitted.

ALTER TABLE curriculum.review_templates
    ADD COLUMN IF NOT EXISTS review_type_id varchar(128);

ALTER TABLE curriculum.review_templates
    DROP CONSTRAINT IF EXISTS review_templates_review_type_fk;

ALTER TABLE curriculum.review_templates
    ADD CONSTRAINT review_templates_review_type_fk
    FOREIGN KEY (review_type_id) REFERENCES curriculum.review_types (id);

CREATE INDEX IF NOT EXISTS review_templates_review_type_idx
    ON curriculum.review_templates (review_type_id)
    WHERE review_type_id IS NOT NULL;

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

COMMIT;

-- FOLLOW-UP, deliberately NOT part of this transaction. Nothing in the
-- application reads coach_surface after this migration; the column and its
-- constraint/index are left in place only so the backfill above can be
-- re-checked against the original data. Run this once the deploy is
-- confirmed good:
--
--   BEGIN;
--   DROP INDEX IF EXISTS curriculum.review_templates_coach_surface_uniq;
--   ALTER TABLE curriculum.review_templates
--       DROP CONSTRAINT IF EXISTS review_templates_coach_surface_valid;
--   ALTER TABLE curriculum.review_templates DROP COLUMN IF EXISTS coach_surface;
--   COMMIT;
