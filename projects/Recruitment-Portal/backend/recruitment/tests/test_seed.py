from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from recruitment.models import Applicant, Application, Event, Question, QuestionCondition, QuestionOption, Track
from .factories import applicant, application


class SeedTests(TestCase):
    def seed(self):
        call_command("seed_career_fair", stdout=StringIO())

    def test_seed_is_idempotent(self):
        self.seed()
        before = [model.objects.count() for model in (Event, Track, Question, QuestionOption, QuestionCondition)]
        self.seed()
        self.assertEqual(before, [model.objects.count() for model in (Event, Track, Question, QuestionOption, QuestionCondition)])
        self.assertEqual(before[0:3], [1, 4, 22])
        self.assertEqual(before[4], 2)
        self.assertEqual(Event.objects.get().status, Event.Status.DRAFT)
        self.assertEqual(Applicant.objects.count(), 0)

    def test_seed_preserves_customizations_and_candidates(self):
        self.seed()
        selected = Track.objects.first()
        selected.name = "Custom track title"
        selected.save()
        person = applicant()
        entry = application(selected.event, selected, person)
        self.seed()
        selected.refresh_from_db()
        self.assertEqual(selected.name, "Custom track title")
        self.assertTrue(Application.objects.filter(pk=entry.pk).exists())
        self.assertTrue(Applicant.objects.filter(pk=person.pk).exists())

    @override_settings(DJANGO_ENV="production", RECRUITMENT_ALLOW_SEED=True)
    def test_seed_forbidden_in_production_even_if_flag_set(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(Event.objects.exists())

    @override_settings(RECRUITMENT_ALLOW_SEED=False)
    def test_seed_requires_opt_in(self):
        with self.assertRaises(CommandError):
            self.seed()

    def test_seed_refuses_published_or_closed_example(self):
        Event.objects.create(title="Already closed", slug="career-fair-2026", status="CLOSED")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(Track.objects.exists())
