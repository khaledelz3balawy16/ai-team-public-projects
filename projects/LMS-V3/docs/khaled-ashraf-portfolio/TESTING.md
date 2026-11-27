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
- `backend/coach_api/test_aptem_review_reconciliation_no_db.py`
- `backend/coach_api/test_attendance_last_four_no_db.py`
- `backend/coach_api/test_attendance_profiles_no_db.py`
- `backend/coach_api/test_audit_review_instance_consistency_no_db.py`
- `backend/coach_api/test_auto_review_reconciliation_no_db.py`
- `backend/coach_api/test_auto_review_reconciliation_postgres.py`
- `backend/coach_api/test_cache_fail_open_no_db.py`
- `backend/coach_api/test_case_file_otjh_window_no_db.py`
- `backend/coach_api/test_caseload_boundaries_no_db.py`
- `backend/coach_api/test_cleanup_test_review_data_no_db.py`
- `backend/coach_api/test_dashboard_hidden_learners_no_db.py`
- `backend/coach_api/test_dashboard_loading_no_db.py`
- `backend/coach_api/test_dashboard_sections_no_db.py`
- `backend/coach_api/test_dashboard_snapshot_scheduler_no_db.py`
- `backend/coach_api/test_dashboard_upcoming_no_db.py`
- `backend/coach_api/test_graph_token_cache_no_db.py`
- `backend/coach_api/test_learner_display_dates_no_db.py`
- `backend/coach_api/test_live_session_outcomes_no_db.py`
- `backend/coach_api/test_meeting_outcomes_no_db.py`
- `backend/coach_api/test_meeting_reminders_no_db.py`
- `backend/coach_api/test_migrated_pdf_download.py`
- `backend/coach_api/test_migrated_pdf_parity.py`
- `backend/coach_api/test_migrated_progress.py`
- `backend/coach_api/test_migrated_rescheduling.py`
- `backend/coach_api/test_migrated_reviews.py`
- `backend/coach_api/test_migrated_scheduled_flow_no_db.py`
- `backend/coach_api/test_migrated_summary_actions.py`
- `backend/coach_api/test_migrated_summary_binding.py`
- `backend/coach_api/test_migrated_template_sync.py`
- `backend/coach_api/test_migrated_templates.py`
- `backend/coach_api/test_native_review_boundary_no_db.py`
- `backend/coach_api/test_non_delivery_booking_no_db.py`
- `backend/coach_api/test_otjh_profile_parity_no_db.py`
- `backend/coach_api/test_personal_review_no_db.py`
- `backend/coach_api/test_reconciliation_command_process.py`
- `backend/coach_api/test_reconciliation_lock_order_no_db.py`
- `backend/coach_api/test_reconciliation_safety_no_db.py`
- `backend/coach_api/test_review_booking_status_no_db.py`
- `backend/coach_api/test_review_categories_no_db.py`
- `backend/coach_api/test_review_pdf_no_db.py`
- `backend/coach_api/test_review_reconciliation.py`
- `backend/coach_api/test_review_source_selection_no_db.py`
- `backend/coach_api/test_review_source_separation.py`
- `backend/coach_api/test_support_tickets_no_db.py`
- `backend/coach_api/test_template_statistics_no_db.py`
- `backend/coach_api/test_timetable_identity_isolation_no_db.py`
- `backend/coach_api/test_timetable_live_window_no_db.py`
- `backend/coach_api/tests.py`
- `backend/coach_api/tests_ai_marking.py`
- `backend/coach_api/tests_ai_reflection.py`
- `backend/coach_api/tests_attendance_context.py`
- `backend/coach_api/tests_attendance_detail.py`
- `backend/coach_api/tests_attendance_group.py`
- `backend/coach_api/tests_attendance_loading.py`
- `backend/coach_api/tests_attendance_placements.py`
- `backend/coach_api/tests_attendance_projection.py`
- `backend/coach_api/tests_attendance_selected.py`
- `backend/coach_api/tests_attendance_sessions.py`
- `backend/coach_api/tests_bulk_attendance.py`
- `backend/coach_api/tests_calendar_race.py`
- `backend/coach_api/tests_calendar_reschedule.py`
- `backend/coach_api/tests_calendar_sync_visibility.py`
- `backend/coach_api/tests_case_file_overview.py`
- `backend/coach_api/tests_case_file_profile.py`
- `backend/coach_api/tests_case_file_read_only.py`
- `backend/coach_api/tests_case_file_reviews.py`
- `backend/coach_api/tests_case_file_shell.py`
- `backend/coach_api/tests_case_file_transport.py`
- `backend/coach_api/tests_caseload_display_dates.py`
