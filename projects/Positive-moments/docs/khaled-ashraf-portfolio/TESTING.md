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

- `automation/lecture_parts/test_graph_client.py`
- `backend/config/test_database.py`
- `backend/config/test_runner.py`
- `backend/operations/tests/test_api_docs.py`
- `backend/operations/tests/test_backfill_api.py`
- `backend/operations/tests/test_guarded_actions.py`
- `backend/operations/tests/test_lecture_register.py`
- `backend/operations/tests/test_lms_api.py`
- `backend/operations/tests/test_media_api.py`
- `backend/operations/tests/test_operations_api.py`
- `backend/operations/tests/test_publisher_alert_reviews.py`
- `backend/operations/tests/test_publisher_api.py`
- `backend/operations/tests/test_publisher_backfill_api.py`
- `backend/operations/tests/test_publishing_monitor_api.py`
- `backend/operations/tests/test_teams_transcript_retry_api.py`
- `backend/operations/tests/test_transcript_upload_api.py`
- `backend/positive_mentions/tests/test_api.py`
- `backend/positive_mentions/tests/test_evidence.py`
- `backend/positive_mentions/tests/test_evidence_api.py`
- `backend/positive_mentions/tests/test_social_api.py`
- `backend/positive_mentions/tests/test_social_clip_requests.py`
- `backend/positive_mentions/tests/test_social_operations_api.py`
- `backend/positive_mentions/tests/test_sso.py`
- `backend/positive_mentions/tests/test_utils.py`
- `frontend/tests/apiDocumentation.test.ts`
- `frontend/tests/clipRequest.test.ts`
- `frontend/tests/opportunityHeading.test.ts`
- `frontend/tests/positiveEvidence.test.ts`
- `frontend/tests/publishingAlerts.test.ts`
- `frontend/tests/publishingBackfill.test.ts`
- `frontend/tests/publishingDayNavigation.test.ts`
- `frontend/tests/publishingMonitor.test.ts`
- `frontend/tests/socialMedia.test.ts`
- `frontend/tests/socialOperations.test.ts`
- `frontend/tests/teamsTranscriptRetry.test.ts`
- `frontend/tests/transcriptRecovery.test.ts`
- `frontend/tests/transcriptUpload.test.ts`
- `frontend/vitest.config.ts`
- `tests/conftest.py`
- `tests/integration/test_attendance_optional_acceptance.py`
- `tests/integration/test_attendance_optional_qa_persistence.py`
- `tests/integration/test_attendance_recovery.py`
- `tests/integration/test_attendance_resolution_persistence.py`
- `tests/integration/test_automated_production_sync.py`
- `tests/integration/test_bunny_tracking_migration.py`
- `tests/integration/test_canonical_transcript_persistence.py`
- `tests/integration/test_coverage_review_legacy.py`
- `tests/integration/test_database_safety_gate.py`
- `tests/integration/test_delivery_reclassification_cycle.py`
- `tests/integration/test_duplicate_resolution_persistence.py`
- `tests/integration/test_engagement_persistence.py`
- `tests/integration/test_late_attendance_orchestrator.py`
- `tests/integration/test_lecture_processing_queue.py`
- `tests/integration/test_lecture_scoped_engagement.py`
- `tests/integration/test_legacy_writer_persistence.py`
- `tests/integration/test_lms_module_titles.py`
- `tests/integration/test_lms_register_foreign_transaction.py`
- `tests/integration/test_makeup_roster_drift.py`
- `tests/integration/test_manual_transcript_upload.py`
- `tests/integration/test_media_timeline_real_lectures.py`
- `tests/integration/test_orchestration_persistence.py`
- `tests/integration/test_perfect_lecture_persistence.py`
- `tests/integration/test_pipeline_contracts.py`
- `tests/integration/test_platform_invariants.py`
- `tests/integration/test_positive_moments_media_persistence.py`
- `tests/integration/test_provider_auth_budget_persistence.py`
- `tests/integration/test_provider_idle_limit_persistence.py`
- `tests/integration/test_publisher_auto_release.py`
- `tests/integration/test_publisher_backfill.py`
- `tests/integration/test_publisher_backfill_discovery.py`
- `tests/integration/test_publisher_backfill_qa.py`
- `tests/integration/test_publisher_delivery.py`
- `tests/integration/test_publisher_foundation_concurrency.py`
- `tests/integration/test_publisher_foundation_migrations.py`
- `tests/integration/test_publisher_library_cutover.py`
- `tests/integration/test_publisher_lms_openapi.py`
- `tests/integration/test_publisher_longest_recording.py`
- `tests/integration/test_publisher_recordings_persistence.py`
- `tests/integration/test_publisher_runtime.py`
- `tests/integration/test_publisher_transcripts_persistence.py`
