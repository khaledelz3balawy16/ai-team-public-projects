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

- `.github/ci/test_aptem_learner_sync.py`
- `.github/ci/test_calendar_change_detection.py`
- `.github/ci/test_calendar_deploy.py`
- `.github/ci/test_calendar_release.py`
- `.github/ci/test_calendar_schema_gate.py`
- `.github/ci/test_learner_assignment_release.py`
- `.github/ci/test_recording_runtime.py`
- `backend/audit_api/test_actual_hours_rules.py`
- `backend/audit_api/test_actual_hours_views.py`
- `backend/audit_api/test_last_audit_ledger_views.py`
- `backend/audit_api/test_learner_exclusions.py`
- `backend/audit_api/test_reconcile_accepted_assignment_files.py`
- `backend/audit_api/tests.py`
- `backend/audit_api/tests_contract_hours.py`
- `backend/chat/tests.py`
- `backend/chat/tests_session_precondition.py`
- `backend/coach_api/management/commands/cleanup_named_test_review_events.py`
- `backend/coach_api/management/commands/cleanup_test_review_data.py`
- `backend/coach_api/run_recording_tests.py`
- `backend/coach_api/test_absence_recovery_constraint_no_db.py`
- `backend/coach_api/test_activity_plan_snapshots_no_db.py`
- `backend/coach_api/test_actual_session_resolution.py`
- `backend/coach_api/test_ai_evidence.py`
- `backend/coach_api/test_aptem_attendance_stabilization.py`
- `backend/coach_api/test_aptem_intelligence_failures.py`
- `backend/coach_api/test_aptem_review_reconciliation_no_db.py`
- `backend/coach_api/test_attendance_last_four_no_db.py`
- `backend/coach_api/test_attendance_profiles_no_db.py`
- `backend/coach_api/test_audit_review_instance_consistency_no_db.py`
- `backend/coach_api/test_auto_review_reconciliation_no_db.py`
- `backend/coach_api/test_auto_review_reconciliation_postgres.py`
- `backend/coach_api/test_background_attendance_safety.py`
- `backend/coach_api/test_background_meeting_context.py`
- `backend/coach_api/test_booking_availability.py`
- `backend/coach_api/test_booking_availability_postgres.py`
- `backend/coach_api/test_booking_hours.py`
- `backend/coach_api/test_booking_reservations.py`
- `backend/coach_api/test_bound_actual_session_no_db.py`
- `backend/coach_api/test_cache_fail_open_no_db.py`
- `backend/coach_api/test_calendar_booking_only_no_db.py`
- `backend/coach_api/test_case_file_otjh_window_no_db.py`
- `backend/coach_api/test_caseload_boundaries_no_db.py`
- `backend/coach_api/test_check_session_publication.py`
- `backend/coach_api/test_check_session_resources.py`
- `backend/coach_api/test_cleanup_test_review_data_no_db.py`
- `backend/coach_api/test_coach_migration_graph_no_db.py`
- `backend/coach_api/test_coaching_transcript_backups.py`
- `backend/coach_api/test_coaching_transcript_backups_postgres.py`
- `backend/coach_api/test_completed_lms_review_reads.py`
- `backend/coach_api/test_completed_source_reopening.py`
- `backend/coach_api/test_completion_reminders.py`
- `backend/coach_api/test_dashboard_activity_plan_no_db.py`
- `backend/coach_api/test_dashboard_completed_dates_no_db.py`
- `backend/coach_api/test_dashboard_hidden_learners_no_db.py`
- `backend/coach_api/test_dashboard_loading_no_db.py`
- `backend/coach_api/test_dashboard_record_counts_no_db.py`
- `backend/coach_api/test_dashboard_sections_no_db.py`
- `backend/coach_api/test_dashboard_snapshot_scheduler_no_db.py`
- `backend/coach_api/test_dashboard_upcoming_no_db.py`
- `backend/coach_api/test_directory_calendar_no_db.py`
- `backend/coach_api/test_graph_request_errors.py`
- `backend/coach_api/test_graph_token_cache_no_db.py`
- `backend/coach_api/test_graph_transport.py`
- `backend/coach_api/test_imported_archive_interleavings.py`
- `backend/coach_api/test_imported_booking_state.py`
- `backend/coach_api/test_imported_meeting_ownership_no_db.py`
- `backend/coach_api/test_imported_recording_archive.py`
- `backend/coach_api/test_imported_recording_playback.py`
- `backend/coach_api/test_imported_review_list_forms.py`
- `backend/coach_api/test_imported_review_start.py`
- `backend/coach_api/test_imported_snapshot_persistence.py`
- `backend/coach_api/test_imported_start_models.py`
- `backend/coach_api/test_learner_display_dates_no_db.py`
- `backend/coach_api/test_learner_review_prepare_no_db.py`
- `backend/coach_api/test_live_session_outcomes_no_db.py`
- `backend/coach_api/test_lms_support_tickets_no_db.py`
- `backend/coach_api/test_marking_parts_no_db.py`
- `backend/coach_api/test_mcm_signature_waivers.py`
- `backend/coach_api/test_meeting_outcomes_no_db.py`
- `backend/coach_api/test_meeting_profile_identity.py`
