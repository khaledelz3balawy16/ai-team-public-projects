"""Add example configuration only; never touch candidates or overwrite existing rows."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recruitment.models import Event, Question, QuestionCondition, QuestionOption, Track

T = Question.Type
# Stable identifiers are explicit; labels may change independently in Admin.
TRACKS = [
    ("software-development", "Software Development", [
        ("languages", "Which programming languages are you familiar with?", T.MULTIPLE_CHOICE, True, [("python", "Python"), ("javascript", "JavaScript"), ("java", "Java"), ("csharp", "C#")]),
        ("development-area", "Which development area interests you most?", T.SINGLE_CHOICE, True, [("backend", "Backend"), ("frontend", "Frontend"), ("fullstack", "Full stack"), ("mobile", "Mobile")]),
        ("frameworks", "Which frameworks have you used?", T.MULTIPLE_CHOICE, True, [("django", "Django"), ("react", "React"), ("dotnet", ".NET"), ("none", "None yet")]),
        ("project", "Describe a programming project you worked on.", T.LONG_TEXT, True, []),
        ("portfolio", "GitHub or Portfolio URL", T.URL, False, []),
    ]),
    ("data-analysis", "Data Analysis", [
        ("tools", "Which data tools are you familiar with?", T.MULTIPLE_CHOICE, True, [("excel", "Excel"), ("sql", "SQL"), ("python", "Python"), ("power-bi", "Power BI")]),
        ("analysis-area", "Which data analysis area interests you?", T.MULTIPLE_CHOICE, True, [("business", "Business analytics"), ("visualisation", "Data visualisation"), ("statistics", "Statistics")]),
        ("sql-level", "How would you rate your SQL knowledge?", T.SINGLE_CHOICE, True, [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")]),
        ("project", "Describe a data analysis project you completed.", T.LONG_TEXT, True, []),
        ("portfolio", "Portfolio or Dashboard URL", T.URL, False, []),
    ]),
    ("digital-marketing", "Digital Marketing", [
        ("areas", "Which marketing areas interest you?", T.MULTIPLE_CHOICE, True, [("seo", "SEO"), ("social-media", "Social media"), ("content", "Content marketing"), ("paid-ads", "Paid advertising")]),
        ("tools", "Which marketing tools have you used?", T.MULTIPLE_CHOICE, True, [("analytics", "Google Analytics"), ("canva", "Canva"), ("ads-manager", "Ads Manager"), ("none", "None yet")]),
        ("campaign-experience", "Have you participated in a marketing campaign?", T.YES_NO, True, []),
        ("campaign-details", "Describe the campaign and your contribution.", T.LONG_TEXT, True, []),
        ("skill", "Which marketing skill would you like to develop?", T.LONG_TEXT, True, []),
        ("portfolio", "Portfolio URL", T.URL, False, []),
    ]),
    ("project-management", "Project Management", [
        ("areas", "Which project management areas are you familiar with?", T.MULTIPLE_CHOICE, True, [("planning", "Planning"), ("risk", "Risk management"), ("agile", "Agile"), ("coordination", "Coordination")]),
        ("tools", "Which project management tools have you used?", T.MULTIPLE_CHOICE, True, [("jira", "Jira"), ("trello", "Trello"), ("ms-project", "Microsoft Project"), ("none", "None yet")]),
        ("coordination-experience", "Have you coordinated a project before?", T.YES_NO, True, []),
        ("project-details", "Describe the project and your responsibilities.", T.LONG_TEXT, True, []),
        ("delay", "How would you respond to a project delay?", T.LONG_TEXT, True, []),
        ("training", "Relevant certifications or training", T.SHORT_TEXT, False, []),
    ]),
]


class Command(BaseCommand):
    help = "Non-destructive sample configuration; development/test only with explicit settings opt-in."

    def handle(self, *args, **options):
        if getattr(settings, "DJANGO_ENV", "production") not in ("development", "test") or not settings.RECRUITMENT_ALLOW_SEED:
            raise CommandError("Seeding requires development/test settings and RECRUITMENT_ALLOW_SEED=true.")
        self.seed_configuration()
        self.stdout.write(self.style.SUCCESS("Development example configuration is ready; existing rows were preserved."))

    @transaction.atomic
    def seed_configuration(self):
        event, _ = Event.objects.get_or_create(slug="career-fair-2026", defaults={"title": "Career Fair 2026", "status": Event.Status.DRAFT})
        if event.status != Event.Status.DRAFT:
            raise CommandError("The example event is no longer a draft; no configuration was changed.")
        for track_order, (code, name, questions) in enumerate(TRACKS, 1):
            track, _ = Track.objects.get_or_create(event=event, code=code, defaults={"name": name, "display_order": track_order * 10})
            question_map = {}
            for order, (key, title, kind, required, choices) in enumerate(questions, 1):
                question, _ = Question.objects.get_or_create(track=track, key=key, defaults={
                    "title": title, "question_type": kind, "is_required": required, "display_order": order * 10,
                })
                if question.question_type != kind:
                    raise CommandError("An existing example question has a different type; existing data was preserved.")
                question_map[key] = question
                for option_order, (value, label) in enumerate(choices, 1):
                    QuestionOption.objects.get_or_create(question=question, value=value, defaults={"label": label, "display_order": option_order * 10})
            for source, target in (("campaign-experience", "campaign-details"), ("coordination-experience", "project-details")):
                if source in question_map:
                    QuestionCondition.objects.get_or_create(
                        source_question=question_map[source], target_question=question_map[target],
                        operator=QuestionCondition.Operator.EQUALS, defaults={"expected_value": True},
                    )
