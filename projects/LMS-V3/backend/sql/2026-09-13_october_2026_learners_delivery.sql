-- Set the 30 learners imported from october 2026/*.md to Delivery.
-- Programme_status is the delivery stage; account Status stays unchanged.
BEGIN;

SET LOCAL lock_timeout = '10s';

SET LOCAL statement_timeout = '30s';

LOCK TABLE enrolment."Created_users", "Learner".learners IN SHARE ROW EXCLUSIVE MODE;

DO $delivery$
DECLARE
  emails CONSTANT text[] := ARRAY[
  'contact+5211e5178212@example.com',
  'contact+c498b1eeb48e@example.com',
  'contact+f02b5ede9eb3@example.com',
  'contact+b14484e464de@example.com',
  'contact+de971639e26a@example.com',
  'contact+7524d7ea16c7@example.com',
  'contact+0e97d05996c9@example.com',
  'contact+5eb6d3fff4fc@example.com',
  'contact+17996b6942c3@example.com',
  'contact+f829a240a017@example.com',
  'contact+2da7c33fb56c@example.com',
  'contact+5bdeb390f363@example.com',
  'contact+c8fea66209c9@example.com',
  'contact+c899ebc6bf96@example.com',
  'contact+b24ec36dd626@example.com',
  'contact+f738eaf54f61@example.com',
  'contact+9804a11704e0@example.com',
  'contact+8eea1721c84f@example.com',
  'contact+c82efa4ee94c@example.com',
  'contact+c74f75384a30@example.com',
  'contact+9fe3e81ed992@example.com',
  'contact+7a27ab85c17f@example.com',
  'contact+454e85960168@example.com',
  'contact+0bbad251c55e@example.com',
  'contact+652d7144261c@example.com',
  'contact+c52716e47484@example.com',
  'contact+7d01716daed5@example.com',
  'contact+144958520b69@example.com',
  'contact+0b5176137a1e@example.com',
  'contact+d4f0e8d8ec68@example.com'
  ];
  changed integer;
BEGIN
  IF (SELECT count(*) FROM enrolment."Created_users"
      WHERE lower(btrim("Email")) = ANY(emails)) <> 30
     OR (SELECT count(*) FROM "Learner".learners
         WHERE lower(btrim(email)) = ANY(emails)) <> 30
     OR (SELECT count(*) FROM enrolment."Created_users" e
         JOIN "Learner".learners l ON l.enrolment_id = e.id AND l.uuid = e.uuid
         WHERE lower(btrim(e."Email")) = ANY(emails)
           AND lower(btrim(l.email)) = lower(btrim(e."Email"))) <> 30 THEN
    RAISE EXCEPTION 'Expected exactly 30 linked enrolment and learner records';
  END IF;

  UPDATE enrolment."Created_users"
  SET "Programme_status" = 'Delivery'
  WHERE lower(btrim("Email")) = ANY(emails);
  GET DIAGNOSTICS changed = ROW_COUNT;
  IF changed <> 30 THEN RAISE EXCEPTION 'Expected 30 enrolments, got %', changed; END IF;

  UPDATE "Learner".learners
  SET programme_status = 'Delivery', lifecycle_status = 'delivery', updated_at = now()
  WHERE lower(btrim(email)) = ANY(emails);
  GET DIAGNOSTICS changed = ROW_COUNT;
  IF changed <> 30 THEN RAISE EXCEPTION 'Expected 30 profiles, got %', changed; END IF;

  IF (SELECT count(*) FROM enrolment."Created_users" e
      JOIN "Learner".learners l ON l.enrolment_id = e.id AND l.uuid = e.uuid
      WHERE lower(btrim(e."Email")) = ANY(emails)
        AND lower(btrim(l.email)) = lower(btrim(e."Email"))
        AND e."Programme_status" = 'Delivery'
        AND l.programme_status = 'Delivery' AND l.lifecycle_status = 'delivery') <> 30 THEN
    RAISE EXCEPTION 'Delivery status verification failed';
  END IF;
END;
$delivery$;

COMMIT;
