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

- `scripts/legacy-progress-audit.test.ts`
- `src/api/__tests__/auth.test.ts`
- `src/api/__tests__/cachedRequest.test.ts`
- `src/api/__tests__/curriculumLearnerAssignments.test.ts`
- `src/api/__tests__/enrolmentUserImport.test.ts`
- `src/api/__tests__/learnerCalendarFreshness.test.ts`
- `src/api/__tests__/learnerContentLoading.test.ts`
- `src/api/__tests__/learnerOverview.test.ts`
- `src/api/__tests__/learnerRead.test.ts`
- `src/api/__tests__/learningPlanPropagation.test.ts`
- `src/api/__tests__/progressReviews.test.ts`
- `src/api/__tests__/wizardCacheInvalidation.test.ts`
- `src/api/adminEvidence.test.ts`
- `src/api/reflectionSubmission.test.ts`
- `src/api/reviewPdf.test.ts`
- `src/components/feature/DatePickerField.test.tsx`
- `src/components/feature/Header.passwordReset.test.tsx`
- `src/components/feature/RealLearningJourneyView.test.ts`
- `src/components/feature/SelectField.test.tsx`
- `src/components/feature/__tests__/LearnerProfilePhoto.test.tsx`
- `src/components/feature/__tests__/LearnerProgrammeGate.test.tsx`
- `src/components/feature/__tests__/LearnerSidebarNavigation.test.tsx`
- `src/components/feature/__tests__/PageSkeleton.test.tsx`
- `src/components/feature/__tests__/ReflectionWindow.test.ts`
- `src/components/feature/__tests__/RequireAuth.test.tsx`
- `src/components/feature/__tests__/SidebarAdminPreview.test.tsx`
- `src/components/feature/__tests__/SlideDeckViewer.test.tsx`
- `src/components/feature/__tests__/VideoPlayerFallback.test.tsx`
- `src/components/feature/__tests__/WorkspaceSidebar.test.tsx`
- `src/components/feature/__tests__/WorkspaceSwitcher.test.tsx`
- `src/components/feature/__tests__/calendarPreviews.test.tsx`
- `src/components/feature/__tests__/ksbTemplateImport.test.ts`
- `src/components/feature/__tests__/monthlyActivity.test.ts`
- `src/components/feature/__tests__/otjhActivityLog.test.tsx`
- `src/components/feature/__tests__/videoUrl.test.ts`
- `src/components/feature/__tests__/wizardLateDetailHydration.test.tsx`
- `src/components/feature/__tests__/wizardModuleRequests.test.tsx`
- `src/components/feature/__tests__/wizardResetOnOpenOnly.test.tsx`
- `src/components/reviews/__tests__/ReviewPdfDownload.test.tsx`
- `src/components/reviews/__tests__/ReviewSignatures.test.tsx`
- `src/features/audit/AuditWorkspaceHoursTest.tsx`
- `src/features/audit/api.test.ts`
- `src/features/audit/learner-exclusions.test.ts`
- `src/features/audit/learner-log-pro-copy/lib/api.test.ts`
- `src/features/audit/learner-log-pro-copy/lib/journalDraft.test.ts`
- `src/features/audit/learner-log-pro-copy/lib/lastAuditRequests.test.ts`
- `src/features/audit/learner-log-pro-copy/lib/lectureOrdering.test.ts`
- `src/features/audit/learner-log-pro-copy/lib/readingHtml.test.ts`
- `src/features/audit/learner-log-pro-hours-test/lib/actualHours.test.ts`
- `src/features/audit/learner-log-pro-hours-test/lib/api.test.ts`
- `src/features/audit/learner-log-pro-hours-test/lib/journalHours.test.ts`
- `src/features/audit/learner-log-pro-hours-test/lib/lastAuditRequests.test.ts`
- `src/features/audit/learner-log-pro-hours-test/lib/readingHtml.test.ts`
- `src/features/audit/learner-log-pro-manual/lib/api.test.ts`
- `src/features/audit/learner-log-pro-manual/lib/lastAuditRequests.test.ts`
- `src/features/monthly-logs/api.test.ts`
- `src/features/monthly-logs/monthlyLogs.test.tsx`
- `src/features/old-otjh/ArchivePreview.test.tsx`
- `src/features/old-otjh/BulkSignDialog.test.tsx`
- `src/features/old-otjh/ContentPreview.test.tsx`
- `src/features/old-otjh/JournalDownloads.test.tsx`
- `src/features/old-otjh/LearnerEntryGate.test.tsx`
- `src/features/old-otjh/MonitoringDashboard.test.tsx`
- `src/features/old-otjh/PreviousRecordMenuItem.test.tsx`
- `src/features/old-otjh/SignatureCapture.test.tsx`
- `src/features/old-otjh/TransitionDialog.test.tsx`
- `src/features/old-otjh/downloadJournal.test.ts`
- `src/features/old-otjh/entry.test.ts`
- `src/features/old-otjh/journalPdf.test.ts`
- `src/features/old-otjh/oldOtjh.test.tsx`
- `src/features/old-otjh/previewUrl.test.ts`
- `src/features/old-otjh/report.test.ts`
- `src/hooks/__tests__/learnerNavigation.test.tsx`
- `src/hooks/__tests__/useAuth.test.tsx`
- `src/hooks/__tests__/useCurriculumData.strictmode.test.tsx`
- `src/hooks/__tests__/useCurriculumKsbSets.strictmode.test.tsx`
- `src/hooks/__tests__/useFreshUserRedirect.test.tsx`
- `src/hooks/__tests__/useLearnerDetailParam.test.tsx`
- `src/hooks/__tests__/useLearnerMetrics.test.tsx`
- `src/hooks/__tests__/useLearnerNavGate.test.tsx`
