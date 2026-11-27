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

- `backend/config/schema_test_runner.py`
- `backend/config/test_settings.py`
- `backend/email_execution_test_child.py`
- `backend/library/gmail_test_safety.py`
- `backend/library/management/commands/send_test_email.py`
- `backend/library/test_availability_requeue.py`
- `backend/library/test_availability_sources.py`
- `backend/library/test_copy_status_integrity.py`
- `backend/library/test_duplicate_borrow_requests.py`
- `backend/library/test_email_activation.py`
- `backend/library/test_email_execution_postgres.py`
- `backend/library/test_email_readiness.py`
- `backend/library/test_email_receiver.py`
- `backend/library/test_email_recipient_policy.py`
- `backend/library/test_email_system.py`
- `backend/library/test_email_timezone_fallback.py`
- `backend/library/test_final_loan_cutover.py`
- `backend/library/test_gmail_client.py`
- `backend/library/test_gmail_oauth.py`
- `backend/library/test_gmail_oauth_browser.py`
- `backend/library/test_gmail_oauth_config.py`
- `backend/library/test_gmail_single_send.py`
- `backend/library/test_gmail_test_profile.py`
- `backend/library/test_graph_mailbox_setup.py`
- `backend/library/test_legacy_cairo_readiness.py`
- `backend/library/test_lms_sso.py`
- `backend/library/test_loan_database_integrity.py`
- `backend/library/test_n8n_email_compatibility.py`
- `backend/library/test_notify_conversion.py`
- `backend/library/test_phase2.py`
- `backend/library/test_stale_loan_emails.py`
- `backend/library/test_student_directory.py`
- `backend/library/test_timezones.py`
- `backend/library/test_user_timezones.py`
- `backend/library/tests.py`
- `backend/run_isolated_tests.py`
- `backend/run_local_postgres_tests.py`
- `backend/send_first_gmail_test.py`
