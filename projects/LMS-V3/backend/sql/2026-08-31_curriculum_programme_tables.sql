-- Curriculum per-programme snapshot tables built from the programme_audit schema.
-- curriculum."PCP" / "MM" / "ME": one row per authored component, carrying its
-- module and week identity, for Project Controls Professional, Marketing Manager
-- and Marketing Executive respectively.
-- Re-runnable: each table is dropped and rebuilt from programme_audit.

BEGIN;

-- ===== PCP - Project Controls Professional (PROG-PCP-L6) =====
DROP TABLE IF EXISTS curriculum."PCP";

CREATE TABLE curriculum."PCP" (
    programme_code           varchar(8)   NOT NULL DEFAULT 'PCP',
    curriculum_programme_id  varchar(64)  NOT NULL DEFAULT 'PROG-PCP-L6',
    source_table             varchar(120) NOT NULL,
    copied_at                timestamptz  NOT NULL DEFAULT now(),
    LIKE programme_audit.earned_value_management_portfolio_management INCLUDING DEFAULTS
);

ALTER TABLE curriculum."PCP" ADD CONSTRAINT "PCP_pkey" PRIMARY KEY (id);

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

CREATE INDEX "PCP_module_idx"    ON curriculum."PCP" (module_catalogue_id);

CREATE INDEX "PCP_week_idx"      ON curriculum."PCP" (week_id);

CREATE INDEX "PCP_week_no_idx"   ON curriculum."PCP" (module_catalogue_id, week_number);

CREATE INDEX "PCP_type_idx"      ON curriculum."PCP" (component_type);

CREATE INDEX "PCP_source_idx"    ON curriculum."PCP" (source_table);

-- ===== MM - Marketing Manager (PROG-MM-L6) =====
DROP TABLE IF EXISTS curriculum."MM";

CREATE TABLE curriculum."MM" (
    programme_code           varchar(8)   NOT NULL DEFAULT 'MM',
    curriculum_programme_id  varchar(64)  NOT NULL DEFAULT 'PROG-MM-L6',
    source_table             varchar(120) NOT NULL,
    copied_at                timestamptz  NOT NULL DEFAULT now(),
    LIKE programme_audit.ai_in_marketing INCLUDING DEFAULTS
);

ALTER TABLE curriculum."MM" ADD CONSTRAINT "MM_pkey" PRIMARY KEY (id);

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

CREATE INDEX "MM_module_idx"    ON curriculum."MM" (module_catalogue_id);

CREATE INDEX "MM_week_idx"      ON curriculum."MM" (week_id);

CREATE INDEX "MM_week_no_idx"   ON curriculum."MM" (module_catalogue_id, week_number);

CREATE INDEX "MM_type_idx"      ON curriculum."MM" (component_type);

CREATE INDEX "MM_source_idx"    ON curriculum."MM" (source_table);

-- ===== ME - Marketing Executive (PROG-ME-L4) =====
DROP TABLE IF EXISTS curriculum."ME";

CREATE TABLE curriculum."ME" (
    programme_code           varchar(8)   NOT NULL DEFAULT 'ME',
    curriculum_programme_id  varchar(64)  NOT NULL DEFAULT 'PROG-ME-L4',
    source_table             varchar(120) NOT NULL,
    copied_at                timestamptz  NOT NULL DEFAULT now(),
    LIKE programme_audit.impact_planning INCLUDING DEFAULTS
);

ALTER TABLE curriculum."ME" ADD CONSTRAINT "ME_pkey" PRIMARY KEY (id);

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

-- Portfolio: top-level data statement omitted.

CREATE INDEX "ME_module_idx"    ON curriculum."ME" (module_catalogue_id);

CREATE INDEX "ME_week_idx"      ON curriculum."ME" (week_id);

CREATE INDEX "ME_week_no_idx"   ON curriculum."ME" (module_catalogue_id, week_number);

CREATE INDEX "ME_type_idx"      ON curriculum."ME" (component_type);

CREATE INDEX "ME_source_idx"    ON curriculum."ME" (source_table);

COMMIT;
