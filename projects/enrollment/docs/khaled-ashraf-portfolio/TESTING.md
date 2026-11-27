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

- `backend/coach_api/tests.py`
- `backend/coach_api/tests_calendar_race.py`
- `backend/coach_api/tests_errors.py`
- `backend/coach_api/tests_security.py`
- `backend/curriculum_api/test_cohort_identity_lookup.py`
- `backend/curriculum_api/test_cohort_status_patch.py`
- `backend/curriculum_api/tests.py`
- `backend/enrollment_service/settings_test.py`
- `backend/enrollment_service/test_lms_activity_readonly.py`
- `backend/enrollment_service/test_lms_readonly.py`
- `backend/enrollment_service/test_lms_reviews_readonly.py`
- `backend/enrollment_service/test_training_plan_sources.py`
- `backend/enrollment_service/test_uln_compatibility.py`
- `backend/enrollment_service/tests.py`
- `backend/enrolment_api/document_templates/test_binding_audit.py`
- `backend/enrolment_api/document_templates/test_blank_documents.py`
- `backend/enrolment_api/document_templates/test_design_theme.py`
- `backend/enrolment_api/document_templates/test_discard.py`
- `backend/enrolment_api/document_templates/test_dynamic_catalogue.py`
- `backend/enrolment_api/document_templates/test_ilr_2026_27_content.py`
- `backend/enrolment_api/document_templates/test_ilr_working_hours.py`
- `backend/enrolment_api/document_templates/test_initial_issue.py`
- `backend/enrolment_api/document_templates/test_initial_signing.py`
- `backend/enrolment_api/document_templates/test_issued_preview.py`
- `backend/enrolment_api/document_templates/test_learner_documents.py`
- `backend/enrolment_api/document_templates/test_legacy_snapshot.py`
- `backend/enrolment_api/document_templates/test_pending_signatures.py`
- `backend/enrolment_api/document_templates/test_question_fields.py`
- `backend/enrolment_api/document_templates/test_revisions.py`
- `backend/enrolment_api/document_templates/test_runner.py`
- `backend/enrolment_api/document_templates/test_settings.py`
- `backend/enrolment_api/document_templates/test_storage.py`
- `backend/enrolment_api/document_templates/test_template_documents.py`
- `backend/enrolment_api/document_templates/test_templates.py`
- `backend/enrolment_api/document_templates/test_training_plan_activities.py`
- `backend/enrolment_api/document_templates/test_z_branded_pdf.py`
- `backend/enrolment_api/plr_test_runner.py`
- `backend/enrolment_api/plr_test_settings.py`
- `backend/enrolment_api/plr_test_urls.py`
- `backend/enrolment_api/skills_radar/test_catalogue.py`
- `backend/enrolment_api/skills_radar/test_module_impact.py`
- `backend/enrolment_api/skills_radar/test_runner.py`
- `backend/enrolment_api/skills_radar/test_screening.py`
- `backend/enrolment_api/skills_radar/test_screening_migration.py`
- `backend/enrolment_api/skills_radar/test_settings.py`
- `backend/enrolment_api/test_plr_pdf.py`
- `backend/enrolment_api/test_plr_service.py`
- `backend/enrolment_api/test_url_resolution.py`
- `backend/enrolment_api/tests.py`
- `backend/enrolment_api/tests_bksb.py`
- `backend/enrolment_api/tests_cv_job_documents.py`
- `backend/enrolment_api/tests_document_schema.py`
- `backend/enrolment_api/tests_eligibility_addresses.py`
- `backend/enrolment_api/tests_eligibility_age.py`
- `backend/enrolment_api/tests_eligibility_applications.py`
- `backend/enrolment_api/tests_eligibility_exception.py`
- `backend/enrolment_api/tests_eligibility_form.py`
- `backend/enrolment_api/tests_eligibility_invitation.py`
- `backend/enrolment_api/tests_eligibility_layout.py`
- `backend/enrolment_api/tests_eligibility_prefill.py`
- `backend/enrolment_api/tests_eligibility_validation.py`
- `backend/enrolment_api/tests_eligibility_workplace.py`
- `backend/enrolment_api/tests_employer_document_signing.py`
- `backend/enrolment_api/tests_employment_status_history.py`
- `backend/enrolment_api/tests_ilr_eligibility_evidence.py`
- `backend/enrolment_api/tests_ilr_employer_details.py`
- `backend/enrolment_api/tests_ilr_finalisation.py`
- `backend/enrolment_api/tests_ilr_health.py`
- `backend/enrolment_api/tests_ilr_learner_details.py`
- `backend/enrolment_api/tests_organisation_matching.py`
- `backend/enrolment_api/tests_plr_evidence.py`
- `backend/enrolment_api/tests_plr_legacy_regression.py`
- `backend/enrolment_api/tests_plr_pdf_import.py`
- `backend/enrolment_api/tests_plr_pdf_preview.py`
- `backend/enrolment_api/tests_plr_record_changes.py`
- `backend/enrolment_api/tests_plr_uln.py`
- `backend/enrolment_api/tests_policy_documents.py`
- `backend/enrolment_api/tests_postcode_lookup.py`
- `backend/enrolment_api/tests_skills_radar_scale.py`
- `backend/enrolment_api/tests_wizard_entry.py`
