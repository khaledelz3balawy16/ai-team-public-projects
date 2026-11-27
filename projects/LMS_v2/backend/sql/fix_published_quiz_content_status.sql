-- Fix: 43 quiz components carry contentStatus = 'Published', which is not one of
-- the four authoring statuses (Draft, Ready for QA, Needs changes, Approved).
-- The Module Builder validates every component before it saves, so a single bad
-- value refuses the whole module save -- including edits to CHANGE_ME components.
--
-- Where they came from: a one-off quiz import on 2026-09-22
-- (settings.importBatch = 'risk-weeks00-06-20260922') wrote the quiz bank's own
-- word 'Published' into the authoring status field.
--
-- contentStatus is an authoring/QA label only: it gates nothing for learners and
-- appears in the component Status select and the version-control badge. Nothing
-- else in the module is changed by this.
--
-- Run the statements in order. 1 and 2 are read-only.

-- 1. Before: expect 43 rows, all quiz, all in one module.
select module_catalogue_id,
       type,
       count(*) as components,
       min(title) as sample_title
from curriculum.components
where settings_json->>'contentStatus' = 'Published'
group by 1, 2;

-- 2. The rows themselves, for the record.
select id, module_catalogue_id, title, settings_json->>'importBatch' as import_batch
from curriculum.components
where settings_json->>'contentStatus' = 'Published'
order by module_catalogue_id, display_order;

-- Portfolio: top-level data statement omitted.

-- 4. After: the first query must return no rows, and the second must show 43.
select count(*) as still_published
from curriculum.components
where settings_json->>'contentStatus' = 'Published';

select count(*) as repaired
from curriculum.components
where settings_json->>'importBatch' = 'risk-weeks00-06-20260922'
  and settings_json->>'contentStatus' = 'Approved';
