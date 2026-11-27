-- Read-only: expected result is 30 rows, each with one target and coach.
WITH source AS (
 SELECT * FROM jsonb_to_recordset($source$
[
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Ilaria Piscopo", "email": "contact+5211e5178212@example.com", "phone": "7472958619", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Melissa Bramall", "email": "contact+c498b1eeb48e@example.com", "phone": "7773454875", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Owen Williams", "email": "contact+f02b5ede9eb3@example.com", "phone": "7938196306", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Bethany Cobley", "email": "contact+b14484e464de@example.com", "phone": "7312087312", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Danielle Roberts", "email": "contact+de971639e26a@example.com", "phone": "7939268618", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Elizabeth Hughes", "email": "contact+7524d7ea16c7@example.com", "phone": "7984184074", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Mae Brown", "email": "contact+0e97d05996c9@example.com", "phone": "7957985288", "programme_id": "PROG-ME-L4"},
  {"programme_code": "ME", "programme_name": "Marketing Executive Level 4", "full_name": "Stephanie Smith", "email": "contact+5eb6d3fff4fc@example.com", "phone": "7877684069", "programme_id": "PROG-ME-L4"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Caris Champion", "email": "contact+17996b6942c3@example.com", "phone": "7464693758", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Kellymarie Lywood", "email": "contact+f829a240a017@example.com", "phone": "447860719966", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Katie Jenkin", "email": "contact+2da7c33fb56c@example.com", "phone": "7971550581", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Lauren Alexander", "email": "contact+5bdeb390f363@example.com", "phone": "7456839481", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Faye Baker", "email": "contact+c8fea66209c9@example.com", "phone": "7791774875", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Callum Perry", "email": "contact+c899ebc6bf96@example.com", "phone": "7944875956", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Amber Insch", "email": "contact+b24ec36dd626@example.com", "phone": "7364136087", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Jonathan Dack", "email": "contact+f738eaf54f61@example.com", "phone": "7506049077", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Flora Donnelly", "email": "contact+9804a11704e0@example.com", "phone": "7736974293", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Harriet Lacey", "email": "contact+8eea1721c84f@example.com", "phone": "7572340134", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Summer Thompson", "email": "contact+c82efa4ee94c@example.com", "phone": "7491912241", "programme_id": "PROG-MM-L6"},
  {"programme_code": "MM", "programme_name": "Marketing Manager Level 6", "full_name": "Alexandra Cayzer", "email": "contact+c74f75384a30@example.com", "phone": "7734237078", "programme_id": "PROG-MM-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Laila Rees", "email": "contact+9fe3e81ed992@example.com", "phone": "7341840427", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Jordan Garratt", "email": "contact+7a27ab85c17f@example.com", "phone": "7487543761", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Hannah MacLellan", "email": "contact+454e85960168@example.com", "phone": "7827315960", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Shelley Cant", "email": "contact+0bbad251c55e@example.com", "phone": "7784314912", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Kenan Tezcan", "email": "contact+652d7144261c@example.com", "phone": "7546336383", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Rachel Whittle", "email": "contact+c52716e47484@example.com", "phone": "7450250109", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Prashanth Sivalingam", "email": "contact+7d01716daed5@example.com", "phone": "7405801772", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Katie Johnson", "email": "contact+144958520b69@example.com", "phone": "7511105521", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Melanie Green", "email": "contact+0b5176137a1e@example.com", "phone": "7946812738", "programme_id": "PROG-PCP-L6"},
  {"programme_code": "PCP", "programme_name": "Project Controls Professional Level 6", "full_name": "Melissa Barr", "email": "contact+d4f0e8d8ec68@example.com", "phone": "7597522396", "programme_id": "PROG-PCP-L6"}
]
$source$::jsonb)
 AS x(programme_code text, programme_id text, programme_name text,
      full_name text, email text, phone text)
)
SELECT r.programme_code, r.full_name, r.email, r.phone,
       t.*, (SELECT count(*) FROM enrolment."Created_users" e
             WHERE lower(btrim(e."Email")) = r.email) AS existing_enrolment,
       (SELECT count(*) FROM "Learner".learners l
        WHERE lower(btrim(l.email)) = r.email) AS existing_profiles
FROM source r LEFT JOIN LATERAL (
SELECT p.programme_id, p.name AS programme_name,
           c.cohort_id, c.cohort_name, g.group_id, g.group_name,
           s."Username" AS coach_name, lower(btrim(s."Email")) AS coach_email
    FROM curriculum.programmes p
    JOIN curriculum.cohorts c ON c.programme_id = p.programme_id
    JOIN curriculum.groups g ON g.cohort_id = c.cohort_id
                            AND g.programme_id = p.programme_id
    JOIN enrolment."Staff_users" s
      ON lower(regexp_replace(btrim(s."Username"), '\s+', ' ', 'g'))
       = lower(regexp_replace(btrim(g.coach_name), '\s+', ' ', 'g'))
    WHERE p.programme_id = r.programme_id AND p.name = r.programme_name
      AND p.deleted_at IS NULL AND NOT coalesce(p.is_archived, false)
      AND lower(coalesce(p.status, '')) <> 'archived'
      AND lower(btrim(c.cohort_name)) = 'october 2026'
      AND c.deleted_at IS NULL AND NOT coalesce(c.is_programme_deleted, false)
      AND lower(coalesce(c.status, '')) <> 'archived'
      AND lower(btrim(g.group_name)) = 'g1'
      AND g.deleted_at IS NULL AND NOT coalesce(g.is_programme_deleted, false)
      AND lower(btrim(s."Access")) = 'coach'
      AND lower(btrim(coalesce(s." Status", ''))) NOT IN ('archived','inactive','disabled')
      AND btrim(coalesce(s."Email", '')) <> '' 
) t ON true
ORDER BY r.programme_code, r.full_name;
