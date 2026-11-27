from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from recruitment.models import (
    Applicant, Application, ApplicationAnswer, ApplicationStatusHistory, CVDocument,
    Event, Question, QuestionCondition, QuestionOption, Track,
)
from .factories import applicant, application, event, question, track


class DomainTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = event()
        cls.track = track(cls.event)
        cls.other_track = track(cls.event, "data")
        cls.applicant = applicant()
        cls.application = application(cls.event, cls.track, cls.applicant)
        cls.question = question(cls.track)

    def test_event_has_many_tracks(self):
        self.assertEqual(self.event.tracks.count(), 2)

    def test_same_code_allowed_across_events(self):
        second = event("second")
        self.assertEqual(track(second).code, self.track.code)

    def test_question_and_option_ownership(self):
        choice = question(self.track, "languages", Question.Type.MULTIPLE_CHOICE)
        option = QuestionOption.objects.create(question=choice, value="python", label="Python")
        self.assertEqual(choice.track, self.track)
        self.assertEqual(option.question, choice)

    def test_option_on_text_question_rejected(self):
        with self.assertRaises(ValidationError):
            QuestionOption.objects.create(question=self.question, value="x", label="X")

    def test_option_label_edit_preserves_stable_value(self):
        choice = question(self.track, "languages", Question.Type.MULTIPLE_CHOICE)
        option = QuestionOption.objects.create(question=choice, value="python", label="Python")
        option.label = "Python 3"
        option.save()
        option.value = "new-value"
        with self.assertRaises(ValidationError):
            option.save()

    def test_email_normalized_before_validation(self):
        person = applicant("  Another@Example.test  ")
        self.assertEqual(person.email, "another@example.test")

    def test_duplicate_email_model_validation(self):
        with self.assertRaises(ValidationError):
            applicant("STUDENT@EXAMPLE.TEST")

    def test_one_applicant_can_apply_to_different_events(self):
        second = event("second")
        application(second, track(second), self.applicant)
        self.assertEqual(self.applicant.applications.count(), 2)

    def test_wrong_event_track_rejected(self):
        second = event("second")
        with self.assertRaises(ValidationError):
            application(second, self.track, self.applicant)

    def test_answer_from_other_track_rejected(self):
        other = question(self.other_track)
        with self.assertRaises(ValidationError):
            ApplicationAnswer.objects.create(application=self.application, question=other, response="Test")

    def test_invalid_option_values_rejected(self):
        choice = question(self.track, "languages", Question.Type.MULTIPLE_CHOICE)
        QuestionOption.objects.create(question=choice, value="python", label="Python")
        for response in (["invalid"], "python", ["python", "python"], [], [True]):
            with self.subTest(response=response), self.assertRaises(ValidationError):
                ApplicationAnswer.objects.create(application=self.application, question=choice, response=response)

    def test_valid_multiple_choice_answer(self):
        choice = question(self.track, "languages", Question.Type.MULTIPLE_CHOICE)
        QuestionOption.objects.create(question=choice, value="python", label="Python")
        answer = ApplicationAnswer.objects.create(application=self.application, question=choice, response=["python"])
        self.assertEqual(answer.response, ["python"])

    def test_typed_json_answers(self):
        examples = [
            (Question.Type.YES_NO, False, "false"),
            (Question.Type.NUMBER, 1.5, True),
            (Question.Type.SHORT_TEXT, "A project", "   "),
            (Question.Type.URL, "https://example.com/project", "javascript:alert(1)"),
        ]
        for index, (kind, valid, invalid) in enumerate(examples):
            q = question(self.track, f"typed-{index}", kind)
            ApplicationAnswer.objects.create(application=self.application, question=q, response=valid)
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                ApplicationAnswer(application=self.application, question=q, response=invalid).clean()

    def test_numeric_nonfinite_values_rejected(self):
        q = question(self.track, "number", Question.Type.NUMBER)
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValidationError):
                ApplicationAnswer(application=self.application, question=q, response=value).clean()

    def test_large_integer_does_not_overflow_validation(self):
        q = question(self.track, "large-number", Question.Type.NUMBER)
        ApplicationAnswer(application=self.application, question=q, response=10 ** 400).clean()

    def test_empty_optional_answer_rejected(self):
        self.question.is_required = False
        self.question.save()
        with self.assertRaises(ValidationError):
            ApplicationAnswer.objects.create(application=self.application, question=self.question, response="")

    def test_answered_question_cannot_be_deleted_or_retyped(self):
        ApplicationAnswer.objects.create(application=self.application, question=self.question, response="Test")
        with self.assertRaises(ProtectedError):
            self.question.delete()
        self.question.question_type = Question.Type.YES_NO
        with self.assertRaises(ValidationError):
            self.question.save()

    def test_track_with_application_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.track.delete()

    def test_track_cannot_move_event_with_applications(self):
        self.track.event = event("second")
        with self.assertRaises(ValidationError):
            self.track.save()

    def test_draft_track_change_cannot_orphan_answers(self):
        ApplicationAnswer.objects.create(application=self.application, question=self.question, response="Test")
        self.application.track = self.other_track
        with self.assertRaises(ValidationError):
            self.application.save()

    def test_submission_requires_privacy_and_timestamp(self):
        self.application.status = Application.Status.SUBMITTED
        with self.assertRaises(ValidationError):
            self.application.save()
        self.application.submitted_at = timezone.now()
        with self.assertRaises(ValidationError):
            self.application.save()

    def test_submitted_track_and_acknowledgement_immutable(self):
        instant = timezone.now()
        self.application.status = Application.Status.SUBMITTED
        self.application.submitted_at = instant
        self.application.privacy_acknowledged_at = instant
        self.application.privacy_notice_version = "v1"
        self.application.save()
        self.application.track = self.other_track
        with self.assertRaises(ValidationError):
            self.application.save()
        self.application.refresh_from_db()
        self.application.privacy_notice_version = "v2"
        with self.assertRaises(ValidationError):
            self.application.save()

    def test_drafts_not_counted_as_submitted_and_opt_in_false(self):
        self.assertEqual(Application.objects.filter(submitted_at__isnull=False).count(), 0)
        self.assertFalse(self.application.future_opportunities_opt_in)
        self.assertIsNone(self.application.external_cv_sharing_authorized_at)

    def test_event_date_and_publication_validation(self):
        self.event.starts_at = timezone.now()
        self.event.ends_at = self.event.starts_at - timezone.timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.event.save()
        self.event.ends_at = None
        self.event.status = Event.Status.PUBLISHED
        with self.assertRaises(ValidationError):
            self.event.save()
        self.event.privacy_notice_version = "v1"
        self.event.privacy_notice_url = "https://example.com/privacy"
        self.event.save()

    def test_closing_event_preserves_applications(self):
        self.event.status = Event.Status.CLOSED
        self.event.save()
        self.assertTrue(Application.objects.filter(pk=self.application.pk).exists())

    def test_invalid_status_choices_rejected(self):
        self.application.status = "INVALID"
        with self.assertRaises(ValidationError):
            self.application.save()

    def test_status_history_attribution_and_system_transition(self):
        user = get_user_model().objects.create_user(username="reviewer", password='CHANGE_ME', is_staff=True)
        entry = ApplicationStatusHistory.objects.create(application=self.application, previous_status="SUBMITTED", new_status="IN_REVIEW", changed_by=user)
        self.assertEqual(entry.changed_by, user)
        system_entry = ApplicationStatusHistory.objects.create(application=self.application, previous_status=None, new_status="DRAFT")
        self.assertIsNone(system_entry.changed_by)
        user.delete()
        entry.refresh_from_db()
        self.assertIsNone(entry.changed_by)
        entry.note = "change"
        with self.assertRaises(ValidationError):
            entry.save()

    def test_private_cv_metadata_and_generated_key(self):
        cv = self.make_cv()
        self.assertRegex(cv.storage_key, r"^cvs/[0-9a-f-]{36}$")
        self.assertNotIn(cv.original_filename, cv.storage_key)
        self.assertEqual(cv.security_scan_status, CVDocument.ScanStatus.PENDING)

    def make_cv(self, **overrides):
        data = dict(application=self.application, original_filename="resume.pdf", file_extension="pdf", content_type="application/pdf", size_bytes=1024)
        data.update(overrides)
        return CVDocument.objects.create(**data)

    def test_cv_size_extension_and_mime_restrictions(self):
        for overrides in (
            {"size_bytes": 0}, {"size_bytes": 10 * 1024 * 1024 + 1},
            {"file_extension": "exe"}, {"content_type": "text/html"},
            {"original_filename": "../resume.pdf"}, {"sha256_checksum": "invalid"},
            {"storage_key": "public/resume.pdf"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.make_cv(**overrides)

    @override_settings(CV_MAX_SIZE_BYTES=512)
    def test_cv_configured_size_limit(self):
        with self.assertRaises(ValidationError):
            self.make_cv()

    def test_cv_maximum_boundary_accepted(self):
        self.make_cv(size_bytes=10 * 1024 * 1024)


class ConditionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = event()
        cls.track = track(cls.event)
        cls.source = question(cls.track, "experience", Question.Type.YES_NO, 10)
        cls.target = question(cls.track, "details", order=20)

    def condition(self, **overrides):
        data = dict(source_question=self.source, target_question=self.target, operator="EQUALS", expected_value=True)
        data.update(overrides)
        return QuestionCondition.objects.create(**data)

    def test_valid_boolean_condition(self):
        self.assertIs(self.condition().expected_value, True)

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValidationError):
            self.condition(target_question=self.source)

    def test_cross_track_dependency_rejected(self):
        other = question(track(self.event, "data"), order=30)
        with self.assertRaises(ValidationError):
            self.condition(target_question=other)

    def test_reverse_order_rejected(self):
        with self.assertRaises(ValidationError):
            self.condition(source_question=self.target, target_question=self.source, expected_value="test")

    def test_cycle_rejected_even_with_preexisting_invalid_bulk_edge(self):
        self.condition()
        third = question(self.track, "third", order=30)
        QuestionCondition.objects.bulk_create([QuestionCondition(source_question=third, target_question=self.source, operator="EQUALS", expected_value="yes")])
        with self.assertRaisesRegex(ValidationError, "Circular"):
            self.condition(source_question=self.target, target_question=third, expected_value="test")

    def test_reordering_question_cannot_break_conditions(self):
        self.condition()
        self.source.display_order = 30
        with self.assertRaises(ValidationError):
            self.source.save()

    def test_operator_and_value_type_validation(self):
        for changes in ({"expected_value": "true"}, {"operator": "CONTAINS"}, {"expected_value": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.condition(**changes)

    def test_multiple_choice_contains_contract(self):
        source = question(self.track, "tools", Question.Type.MULTIPLE_CHOICE, 1)
        QuestionOption.objects.create(question=source, value="python", label="Python")
        self.condition(source_question=source, operator="CONTAINS", expected_value="python")
        with self.assertRaises(ValidationError):
            self.condition(source_question=source, operator="CONTAINS", expected_value=["python"])

    def test_question_settings_are_structured_metadata(self):
        self.target.settings = {"expression": "eval(unsafe)"}
        with self.assertRaises(ValidationError):
            self.target.save()
        self.target.settings = {"min_length": 5, "max_length": 3}
        with self.assertRaises(ValidationError):
            self.target.save()
        self.target.settings = {"max_length": 200}
        self.target.save()
