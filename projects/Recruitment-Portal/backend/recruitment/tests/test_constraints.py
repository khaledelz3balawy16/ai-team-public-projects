"""bulk_create bypasses model.save: these tests prove actual DB constraints."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from recruitment.models import Applicant, Application, ApplicationAnswer, CVDocument, Question, QuestionCondition, QuestionOption, Track
from .factories import applicant, application, event, question, track


class DatabaseConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = event()
        cls.track = track(cls.event)
        cls.applicant = applicant()
        cls.application = application(cls.event, cls.track, cls.applicant)
        cls.question = question(cls.track)

    def assert_db_rejects(self, instance):
        with self.assertRaises(IntegrityError), transaction.atomic():
            type(instance).objects.bulk_create([instance])

    def test_unique_event_track_code(self):
        self.assert_db_rejects(Track(event=self.event, name="Other", code=self.track.code))

    def test_case_insensitive_trimmed_email_uniqueness(self):
        self.assert_db_rejects(Applicant(email="  STUDENT@EXAMPLE.TEST  ", full_name="Duplicate", education_status="STUDENT"))

    def test_unique_event_applicant(self):
        self.assert_db_rejects(Application(event=self.event, track=self.track, applicant=self.applicant, opportunity_type="INTERNSHIP", experience_level="NO_EXPERIENCE", preferred_work_arrangement="FLEXIBLE", availability="IMMEDIATELY"))

    def test_unique_question_key(self):
        self.assert_db_rejects(Question(track=self.track, key=self.question.key, title="Other", question_type="LONG_TEXT"))

    def test_unique_option_value(self):
        choice = question(self.track, "languages", Question.Type.MULTIPLE_CHOICE)
        QuestionOption.objects.create(question=choice, value="python", label="Python")
        self.assert_db_rejects(QuestionOption(question=choice, value="python", label="Duplicate"))

    def test_unique_answer(self):
        ApplicationAnswer.objects.create(application=self.application, question=self.question, response="Test")
        self.assert_db_rejects(ApplicationAnswer(application=self.application, question=self.question, response="Other"))

    def test_unique_cv(self):
        data = dict(application=self.application, original_filename="cv.pdf", file_extension="pdf", content_type="application/pdf", size_bytes=100)
        CVDocument.objects.create(**data)
        self.assert_db_rejects(CVDocument(**data))

    def test_cv_size_database_check(self):
        self.assert_db_rejects(CVDocument(application=self.application, original_filename="cv.pdf", file_extension="pdf", content_type="application/pdf", size_bytes=10 * 1024 * 1024 + 1))

    def test_invalid_status_database_check(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.filter(pk=self.application.pk).update(status="INVALID")

    def test_condition_self_database_check(self):
        self.assert_db_rejects(QuestionCondition(source_question=self.question, target_question=self.question, operator="EQUALS", expected_value="test"))
