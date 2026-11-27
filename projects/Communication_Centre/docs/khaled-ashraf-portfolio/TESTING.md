# Testing and validation

## Preparation checks completed

- Captured source at the recorded commit.
- Checked archive paths, symlinks, and file inclusion rules.
- Replaced detected credential literals, connection strings, and contact addresses with placeholders.
- Removed data exports, runtime environments, private keys, generated output, and internal assistant artifacts.
- Re-scanned the prepared text for the supported sensitive-value patterns.
- Parsed generated JSON documents and package manifests.

## Application validation

Dependencies were not installed. Application tests, servers, migrations, seeders, and database or external-service requests were not run. Runtime correctness after configuration and data removal remains to be verified by the project maintainer.

## Existing test sources

- `backend/api/test_lms_holidays.py`
- `backend/api/test_lms_reference.py`
- `backend/api/test_lms_session_counts.py`
- `backend/api/test_lms_source_setup.py`
- `backend/api/test_manual_match_persistence.py`
- `backend/api/tests.py`
- `backend/callcentre/test_active_learners.py`
- `backend/callcentre/test_alternative_sessions.py`
- `backend/callcentre/test_attendance_edits.py`
- `backend/callcentre/test_authorised_absence.py`
- `backend/callcentre/test_call_flow.py`
- `backend/callcentre/test_call_scope.py`
- `backend/callcentre/test_call_snapshot.py`
- `backend/callcentre/test_case_filters.py`
- `backend/callcentre/test_coach_centre.py`
- `backend/callcentre/test_cycle_lock.py`
- `backend/callcentre/test_delegation.py`
- `backend/callcentre/test_desk_progress.py`
- `backend/callcentre/test_do_not_call.py`
- `backend/callcentre/test_events_hub.py`
- `backend/callcentre/test_history.py`
- `backend/callcentre/test_identity.py`
- `backend/callcentre/test_inbound.py`
- `backend/callcentre/test_learner_satisfaction.py`
- `backend/callcentre/test_lecture_details.py`
- `backend/callcentre/test_phone_numbers.py`
- `backend/callcentre/test_reported_absence.py`
- `backend/callcentre/test_review_meetings.py`
- `backend/callcentre/test_satisfaction_insights.py`
- `backend/callcentre/test_source_bridge.py`
- `backend/callcentre/test_voicemail_calls.py`
- `backend/callcentre/tests.py`
- `backend/check_isolated_tests.py`
- `backend/login/test_administration.py`
- `backend/login/test_permissions.py`
- `backend/login/tests.py`
- `backend/training_plan_lms_reference_dev/test_reference.py`
- `frontend/src/mocks/testimonials.ts`
- `frontend/src/pages/call-centre/engagement/EmployerSpecialists.tsx`
- `frontend/src/pages/call-centre/engagement/Specialists.tsx`
- `frontend/src/pages/home/components/LatestNewsSection.tsx`
- `frontend/src/pages/home/components/TestimonialsSection.tsx`
- `frontend/tests/ui/administration.spec.ts`
- `frontend/tests/ui/allocation.spec.ts`
- `frontend/tests/ui/call-log.spec.ts`
- `frontend/tests/ui/call-sheet-dates.spec.ts`
- `frontend/tests/ui/delegation.spec.ts`
- `frontend/tests/ui/desk-today.spec.ts`
- `frontend/tests/ui/director-dashboard.spec.ts`
- `frontend/tests/ui/full-case.spec.ts`
- `frontend/tests/ui/learner-satisfaction.spec.ts`
- `frontend/tests/ui/missed-calls.spec.ts`
- `frontend/tests/ui/monthly-history.spec.ts`
- `frontend/tests/ui/permissions.spec.ts`
- `frontend/tests/ui/phone-numbers.spec.ts`
- `frontend/tests/ui/review-meetings.spec.ts`
- `frontend/tests/ui/training-plan-comparison.spec.ts`
- `frontend/tests/ui/training-plan-dates.spec.ts`
- `frontend/tests/ui/training-plan-identity.spec.ts`
- `frontend/tests/ui/training-plan-lms-holiday-schedule.spec.ts`
- `frontend/tests/ui/training-plan-lms-holidays.spec.ts`
- `frontend/tests/ui/training-plan-manual-matching.spec.ts`
- `frontend/tests/ui/training-plan-merged-rendering.spec.ts`
- `frontend/tests/ui/training-plan-now.spec.ts`
- `frontend/tests/ui/training-plan-timeline-undo.spec.ts`
- `frontend/tests/ui/zoom-setup.spec.ts`
