from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pmp_assessment.bank import PERFORMANCE_DOMAINS, PERFORMANCE_DOMAIN_TARGET, bank_readiness_stats
from pmp_assessment.models import PMPDomain, PMPQuestion, PMPQuestionOption, PMPTopic

CONTEXTS = [
    "During a complex digital transformation", "While leading a distributed project team",
    "In a regulated organizational environment", "During a high-priority product initiative",
    "While managing a hybrid delivery programme", "In a project with multiple external stakeholders",
    "During execution of a time-sensitive project", "While coordinating several cross-functional teams",
]
REPLACEMENTS = [
    [("What should the project manager do first?", "What is the most appropriate first action for the project manager?"), ("What should the project manager do?", "Which response should the project manager choose?")],
    [("What is the best action?", "Which action provides the best response?"), ("What is the best next action?", "What should be done next?")],
    [("What should happen first?", "Which step should occur before the others?"), ("Which action is most appropriate?", "What is the most suitable course of action?")],
    [("the project manager", "the project lead"), ("the team", "the delivery team")],
]

class Command(BaseCommand):
    help = "Create clearly labelled temporary variants until each performance domain reaches 40 active unique questions."
    def add_arguments(self, parser): parser.add_argument("--per-domain", type=int, default=PERFORMANCE_DOMAIN_TARGET)
    @transaction.atomic
    def handle(self, *args, **options):
        target = options["per_domain"]
        created = 0
        for domain_name in PERFORMANCE_DOMAINS:
            domain, _ = PMPDomain.objects.get_or_create(name=domain_name)
            stats = next(x for x in bank_readiness_stats()["domains"] if x["name"] == domain_name)
            needed = target - stats["count"]
            if needed <= 0: continue
            sources = list(PMPQuestion.objects.filter(is_active=True, performance_domain=domain_name, duplicate_of__isnull=True).prefetch_related("options"))
            if not sources: raise CommandError(f"No source questions are available for {domain_name}.")
            topic, _ = PMPTopic.objects.get_or_create(domain=domain, name="Temporary Practice Variants")
            for index in range(needed):
                source = sources[index % len(sources)]
                body = source.question_text
                for old, new in REPLACEMENTS[index % len(REPLACEMENTS)]: body = body.replace(old, new)
                text = f"{CONTEXTS[index % len(CONTEXTS)]}, review this situation:\n\n{body}\n\n[Temporary {domain_name} practice variant {index + 1}]"
                question = PMPQuestion.objects.create(question_text=text, domain=domain, topic=topic, performance_domain=domain_name, eco_domain=source.eco_domain,
                    eco_task=source.eco_task, task=source.task, question_type=source.question_type, methodology=source.methodology, difficulty=source.difficulty,
                    correct_answer_explanation=source.correct_answer_explanation, wrong_answer_explanation=source.wrong_answer_explanation,
                    pmp_reference=f"TEMPORARY TEST VARIANT based on question {source.id}", chapter_reference=source.chapter_reference, is_active=True)
                PMPQuestionOption.objects.bulk_create([PMPQuestionOption(question=question, option_label=o.option_label, option_text=o.option_text, is_correct=o.is_correct) for o in source.options.all()])
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} temporary variants."))
