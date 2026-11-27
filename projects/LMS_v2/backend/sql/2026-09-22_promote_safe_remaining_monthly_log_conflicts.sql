-- Safely promote the remaining LMS-material conflicts into the canonical
-- journal where doing so does not reopen a finalized month or overwrite a
-- manually overridden activity date.
--
-- This script is intentionally narrower than the first promotion script:
--   * it is scoped to the same 13 Aptem IDs and August 2026;
--   * it requires exactly one live canonical LMS-material match per source row;
--   * it moves a canonical row to the reconstructed month only when both the
--     old and new months are open and the date is not a manual override;
--   * it fills only empty Planned/Actual/KSB fields, preserving approved
--     revisions and existing values;
--   * rows touching finalized months or manual date overrides remain
--     provisional and are reported as blocked.
--
-- The source row is retained as audit history. The transaction commits only
-- the safe subset; no trigger is disabled and no finalized history is edited.

BEGIN;

SET LOCAL lock_timeout = '5s';

SET LOCAL statement_timeout = '10min';

LOCK TABLE structured_manual_activities.manual_learner_activities
  IN SHARE ROW EXCLUSIVE MODE;

CREATE TEMP TABLE _monthly_log_safe_meta ON COMMIT DROP AS
SELECT gen_random_uuid() AS run_id,
       'sql-promote-safe-conflicts-2026-08'::text AS actor;

-- A material conflict is safe to consider only when it resolves to exactly
-- one live canonical row. The window count makes ambiguous matches fail
-- closed instead of picking an arbitrary row.
CREATE TEMP TABLE _monthly_log_safe_map ON COMMIT DROP AS
WITH provisional AS (
  SELECT p.*,
         CASE WHEN p.payload->>'planned_hours' ~ '^[0-9]+(\\.[0-9]+)?$'
              THEN (p.payload->>'planned_hours')::numeric ELSE 0 END AS candidate_planned,
         CASE WHEN p.payload->>'actual_hours' ~ '^[0-9]+(\\.[0-9]+)?$'
              THEN (p.payload->>'actual_hours')::numeric ELSE 0 END AS candidate_actual,
         CASE WHEN p.payload->>'activity_date' ~ '^\\d{4}-\\d{2}-\\d{2}$'
              THEN (p.payload->>'activity_date')::date ELSE NULL END AS candidate_date,
         CASE WHEN p.payload->>'activity_time' ~ '^\\d{2}:\\d{2}(:\\d{2})?$'
              THEN (p.payload->>'activity_time')::time ELSE NULL END AS candidate_time
  FROM structured_manual_activities.monthly_log_provisional_rows p
  WHERE p.status = 'provisional'
    AND p.aptem_id = ANY (ARRAY[
      4605,4778,4737,4937,4765,4579,4275,
      4336,4124,4445,4626,4841,4002
    ]::bigint[])
    AND p.month <= '2026-08'
), matched AS (
  SELECT p.id AS provisional_id,
         p.run_id AS source_run_id,
         p.aptem_id,
         p.month AS provisional_month,
         p.source_ref,
         p.payload,
         p.provisional_fields,
         p.formula_rule,
         p.candidate_planned,
         p.candidate_actual,
         p.candidate_date,
         p.candidate_time,
         m.id AS canonical_id,
         m.month AS canonical_month,
         m.activity_date_manual_override,
         count(m.id) OVER (PARTITION BY p.id) AS match_count
  FROM provisional p
  LEFT JOIN structured_manual_activities.manual_learner_activities m
    ON m.aptem_id = p.aptem_id
   AND m.deleted_at IS NULL
   AND structured_manual_activities.lms_material_activity_ids(
         m.source_ref, m.activity_id)
       && structured_manual_activities.lms_material_activity_ids(
         p.source_ref,
         CASE WHEN p.payload->>'activity_id' ~ '^[0-9]+$'
              THEN (p.payload->>'activity_id')::bigint END)
)
SELECT matched.*,
       (matched.provisional_month = matched.canonical_month) AS same_month,
       EXISTS (
         SELECT 1
         FROM structured_manual_activities.manual_month_finalization_events f
         WHERE f.aptem_id = matched.aptem_id
           AND f.report_month = matched.provisional_month
           AND f.event_type = 'finalized'
       ) AS provisional_month_finalized,
       EXISTS (
         SELECT 1
         FROM structured_manual_activities.manual_month_finalization_events f
         WHERE f.aptem_id = matched.aptem_id
           AND f.report_month = matched.canonical_month
           AND f.event_type = 'finalized'
       ) AS canonical_month_finalized
FROM matched;

CREATE INDEX _monthly_log_safe_map_provisional_idx
  ON _monthly_log_safe_map (provisional_id);

CREATE INDEX _monthly_log_safe_map_canonical_idx
  ON _monthly_log_safe_map (canonical_id);

-- Pre-flight. Any zero/ambiguous match is deliberately excluded below.
SELECT
  count(DISTINCT provisional_id) AS provisional_rows,
  count(DISTINCT provisional_id) FILTER (WHERE match_count = 1) AS unique_matches,
  count(DISTINCT provisional_id) FILTER (WHERE match_count = 0) AS no_match,
  count(DISTINCT provisional_id) FILTER (WHERE match_count > 1) AS ambiguous_match,
  count(DISTINCT provisional_id) FILTER (
    WHERE match_count = 1
      AND NOT provisional_month_finalized
      AND NOT canonical_month_finalized
      AND (
        same_month OR (
          NOT activity_date_manual_override
          AND candidate_date IS NOT NULL
          AND to_char(candidate_date, 'YYYY-MM') = provisional_month
        )
      )
  ) AS writable_safe_rows,
  count(DISTINCT provisional_id) FILTER (
    WHERE match_count = 1
      AND same_month
      AND canonical_month_finalized
  ) AS finalized_same_month_rows,
  count(DISTINCT provisional_id) FILTER (
    WHERE match_count = 1
      AND (
        provisional_month_finalized
        OR canonical_month_finalized
        OR activity_date_manual_override
        OR (NOT same_month AND candidate_date IS NULL)
      )
  ) AS blocked_rows
FROM _monthly_log_safe_map;

-- Capture canonical values and revision guards before any field update.
CREATE TEMP TABLE _monthly_log_safe_changes ON COMMIT DROP AS
SELECT s.*,
       m.planned_hours AS old_planned_hours,
       m.actual_hours AS old_actual_hours,
       m.activity_date AS old_activity_date,
       m.activity_time AS old_activity_time,
       k.ksbs AS old_ksbs,
       r_planned.revision_id AS approved_planned_revision,
       r_actual.revision_id AS approved_actual_revision
FROM _monthly_log_safe_map s
JOIN structured_manual_activities.manual_learner_activities m
  ON m.id = s.canonical_id
 AND m.aptem_id = s.aptem_id
 AND m.deleted_at IS NULL
LEFT JOIN structured_manual_activities.learner_journal_row_ksbs k
  ON k.row_id = m.id
 AND k.aptem_id = m.aptem_id
LEFT JOIN LATERAL (
  SELECT revision_id
  FROM structured_manual_activities.manual_activity_hours_revision r
  WHERE r.row_id = m.id
    AND r.aptem_id = m.aptem_id
    AND r.status = 'approved'
    AND r.proposed_planned_hours IS NOT NULL
  ORDER BY r.revision_id DESC
  LIMIT 1
) r_planned ON true
LEFT JOIN LATERAL (
  SELECT revision_id
  FROM structured_manual_activities.manual_activity_hours_revision r
  WHERE r.row_id = m.id
    AND r.aptem_id = m.aptem_id
    AND r.status = 'approved'
    AND r.proposed_actual_hours IS NOT NULL
  ORDER BY r.revision_id DESC
  LIMIT 1
) r_actual ON true
WHERE s.match_count = 1;

ALTER TABLE _monthly_log_safe_changes
  ADD COLUMN writable_month boolean;

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- A row is promoted only when its month can safely be canonical and every
-- requested field is already present, approved, or was safely applied above.
CREATE TEMP TABLE _monthly_log_safe_promotable ON COMMIT DROP AS
SELECT c.*,
       (
         c.same_month
         OR (
           NOT c.provisional_month_finalized
           AND NOT c.canonical_month_finalized
           AND NOT c.activity_date_manual_override
           AND c.candidate_date IS NOT NULL
           AND to_char(c.candidate_date, 'YYYY-MM') = c.provisional_month
         )
       ) AS month_safe,
       (
         NOT (c.provisional_fields @> '["planned"]'::jsonb)
         OR c.old_planned_hours > 0
         OR c.approved_planned_revision IS NOT NULL
         OR (
           NOT c.provisional_month_finalized
           AND NOT c.canonical_month_finalized
           AND c.candidate_planned > 0
         )
       ) AS planned_safe,
       (
         NOT (c.provisional_fields @> '["actual"]'::jsonb)
         OR c.old_actual_hours > 0
         OR c.approved_actual_revision IS NOT NULL
         OR (
           NOT c.provisional_month_finalized
           AND NOT c.canonical_month_finalized
           AND c.candidate_actual > 0
         )
       ) AS actual_safe,
       (
         NOT (c.provisional_fields @> '["ksb"]'::jsonb)
         OR (c.old_ksbs IS NOT NULL AND c.old_ksbs <> '[]'::jsonb)
         OR (
           NOT c.provisional_month_finalized
           AND NOT c.canonical_month_finalized
           AND jsonb_typeof(c.payload->'ksb_codes') = 'array'
           AND jsonb_array_length(c.payload->'ksb_codes') > 0
         )
       ) AS ksb_safe
FROM _monthly_log_safe_changes c
WHERE c.match_count = 1;

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- POST-FLIGHT.
SELECT
  count(*) FILTER (WHERE status = 'promoted') AS promoted_total,
  count(*) FILTER (WHERE status = 'provisional') AS provisional_remaining
FROM structured_manual_activities.monthly_log_provisional_rows
WHERE aptem_id = ANY (ARRAY[
  4605,4778,4737,4937,4765,4579,4275,
  4336,4124,4445,4626,4841,4002
]::bigint[])
  AND month <= '2026-08';

SELECT reason, count(*)
FROM structured_manual_activities.monthly_log_reconciliation_audit
WHERE run_id = (SELECT run_id FROM _monthly_log_safe_meta)
GROUP BY reason
ORDER BY reason;

COMMIT;
