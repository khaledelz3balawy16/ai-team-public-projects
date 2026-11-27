from django.core.management.base import BaseCommand
from django.db import transaction
from pmp_assessment.bank import TOPIC_DOMAIN_MAP
from pmp_assessment.models import PMPDomain, PMPTopic, PMPQuestion, PMPQuestionOption

QUESTIONS = [
 ("Resources", "Conflict Management", "Two team members disagree about ownership of a critical deliverable. What should the project manager do first?", "General", "Meet with both team members to understand the source of the conflict", ["Escalate to their functional managers", "Meet with both team members to understand the source of the conflict", "Reassign the deliverable", "Document the conflict as a risk"]),
 ("Resources", "Team Leadership", "A high-performing team member has recently become disengaged. What is the best next action?", "Agile", "Have a private conversation to understand their needs and concerns", ["Replace the team member", "Reduce their workload without discussion", "Have a private conversation to understand their needs and concerns", "Report the behavior to the sponsor"]),
 ("Risk", "Risk Management", "A newly identified risk may delay a key milestone. What should the project manager do next?", "Predictive", "Assess probability and impact with the team", ["Immediately use management reserve", "Assess probability and impact with the team", "Change the baseline", "Ignore it until it occurs"]),
 ("Governance", "Change Control", "A stakeholder requests a scope change during execution. What should the project manager do?", "Predictive", "Assess the impact and submit a formal change request", ["Implement it to maintain satisfaction", "Reject it because the baseline is approved", "Assess the impact and submit a formal change request", "Ask the team to absorb the work"]),
 ("Risk", "Compliance", "A new regulation affects a product requirement. What should the project manager do first?", "General", "Assess the impact with relevant experts and stakeholders", ["Continue under the original plan", "Assess the impact with relevant experts and stakeholders", "Cancel the project", "Ask the customer to accept noncompliance"]),
 ("Schedule", "Agile Delivery", "During a sprint, the product owner proposes urgent new work. What should the agile team do?", "Agile", "Discuss priority and trade-offs while protecting the sprint goal", ["Add it immediately without discussion", "Have the project manager assign it", "Discuss priority and trade-offs while protecting the sprint goal", "Extend the sprint"]),
]

class Command(BaseCommand):
    help = "Create default PMP performance domains and development questions (idempotent)."
    @transaction.atomic
    def handle(self, *args, **kwargs):
        for name in ["Governance", "Scope", "Schedule", "Finance", "Stakeholders", "Resources", "Risk"]: PMPDomain.objects.get_or_create(name=name)
        created = 0
        for domain_name, topic_name, text, methodology, correct, options in QUESTIONS:
            domain = PMPDomain.objects.get(name=domain_name); topic, _ = PMPTopic.objects.get_or_create(domain=domain, name=topic_name)
            question, made = PMPQuestion.objects.get_or_create(question_text=text, defaults={"domain": domain, "topic": topic, "performance_domain": domain_name,
                "eco_domain": "Development Fixture", "eco_task": topic_name, "methodology": methodology,
                "difficulty": "Medium", "correct_answer_explanation": f"The best response is: {correct}.", "wrong_answer_explanation": "The alternatives skip analysis, collaboration, or the appropriate PMP process."})
            if not question.performance_domain:
                question.performance_domain = TOPIC_DOMAIN_MAP.get(topic_name, domain_name); question.save(update_fields=["performance_domain", "updated_at"])
            if made:
                PMPQuestionOption.objects.bulk_create([PMPQuestionOption(question=question, option_label=chr(65+i), option_text=option, is_correct=option == correct) for i, option in enumerate(options)])
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seed complete: {created} questions created."))
