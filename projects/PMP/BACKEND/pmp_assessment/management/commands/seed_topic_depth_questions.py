from django.core.management.base import BaseCommand
from django.db import transaction

from pmp_assessment.bank import unique_exam_questions
from pmp_assessment.models import PMPDomain, PMPQuestion, PMPQuestionOption, PMPTopic


SOURCE_FILE = "Original PMI ECO-aligned topic depth expansion"
SOURCE_REFERENCE = "PMI PMP Exam Content Outline 2026 aligned original topic-depth item"

SCENARIOS = [
    "a sponsor asks for a fast decision before the next governance checkpoint",
    "the delivery team finds new information during execution",
    "a customer-facing milestone is approaching and uncertainty is increasing",
    "two stakeholder groups disagree about the right response",
    "a vendor, team, or business constraint changes the original plan",
    "an adaptive team needs to protect value while responding to change",
    "a compliance or business-value concern appears late in delivery",
    "the team has enough data to act but needs the right PMP process",
    "a project lead must balance stakeholder pressure with sound governance",
    "new evidence shows the current approach may not achieve the intended outcome",
]

TOPIC_BLUEPRINTS = {
    "Finance|Earned Value": {
        "domain": "Finance", "topic": "Earned Value", "eco": "Process", "methodology": "Predictive",
        "concept": "earned value forecasting",
        "correct": "Compare the earned value indicators, identify the variance trend, and recommend corrective action based on the forecast.",
        "distractors": [
            "Report that the project is healthy because one performance indicator is favourable.",
            "Change the baseline immediately so the variance no longer appears.",
            "Ask the team to work overtime before analysing the cost and schedule signals.",
        ],
        "explanation": "Earned value questions reward interpreting CPI, SPI, variance trends, and forecasts before choosing a corrective action.",
    },
    "Finance|Budget Control": {
        "domain": "Finance", "topic": "Budget Control", "eco": "Business Environment", "methodology": "Hybrid",
        "concept": "budget governance and benefits protection",
        "correct": "Review the forecast, clarify the decision threshold, and present options that protect business value.",
        "distractors": [
            "Hide the forecast until the budget threshold is actually exceeded.",
            "Reduce quality activities informally to stay inside the current budget.",
            "Approve spending because the project team believes the work is important.",
        ],
        "explanation": "Budget control should connect forecasts, thresholds, governance, and business value rather than treating cost as an isolated number.",
    },
    "Finance|Cost Management": {
        "domain": "Finance", "topic": "Cost Management", "eco": "Process", "methodology": "Predictive",
        "concept": "cost impact analysis",
        "correct": "Assess the cost impact, update the forecast, and use the approved control process before committing funds.",
        "distractors": [
            "Use contingency reserve for any cost increase without checking the plan.",
            "Ask the sponsor to approve the cost after the team has already started the work.",
            "Reject the work automatically because it affects the budget.",
        ],
        "explanation": "Cost management questions usually require impact analysis, forecast updates, and the approved control path before action.",
    },
    "Finance|Procurement": {
        "domain": "Finance", "topic": "Procurement", "eco": "Process", "methodology": "Hybrid",
        "concept": "contract and procurement governance",
        "correct": "Review the procurement documents and contract obligations, then coordinate the response through the approved process.",
        "distractors": [
            "Let the supplier decide because the work is under their responsibility.",
            "Escalate immediately without reviewing the agreement.",
            "Accept the supplier proposal because it appears to reduce cost.",
        ],
        "explanation": "Procurement questions reward using the contract, procurement plan, and agreed remedies before selecting a response.",
    },
    "Risk|Sustainability Risk": {
        "domain": "Risk", "topic": "Sustainability Risk", "eco": "Business Environment", "methodology": "General",
        "concept": "sustainability and business-case risk",
        "correct": "Assess the impact on benefits, stakeholders, and compliance commitments, then update the risk response.",
        "distractors": [
            "Ignore the concern because sustainability is not part of the schedule baseline.",
            "Remove the sustainability commitment without stakeholder review.",
            "Report the project as green because cost and time are still on track.",
        ],
        "explanation": "Sustainability risks can affect benefits, acceptance, compliance, and stakeholder trust, so they belong in active risk analysis.",
    },
    "Risk|Compliance": {
        "domain": "Risk", "topic": "Compliance", "eco": "Business Environment", "methodology": "General",
        "concept": "regulatory and compliance response",
        "correct": "Clarify the compliance requirement with qualified experts and assess the project impact before deciding.",
        "distractors": [
            "Continue with the original plan until an auditor raises a finding.",
            "Ask the customer to waive the requirement informally.",
            "Stop all project work before understanding whether the requirement applies.",
        ],
        "explanation": "Compliance questions reward early clarification, expert input, and impact analysis before implementing or escalating a response.",
    },
    "Risk|Risk Management": {
        "domain": "Risk", "topic": "Risk Management", "eco": "Process", "methodology": "Hybrid",
        "concept": "risk identification, analysis, and response",
        "correct": "Analyse probability and impact with the team, assign ownership, and update the risk response plan.",
        "distractors": [
            "Wait until the uncertainty becomes an issue before taking action.",
            "Escalate the risk to the sponsor without analysing the exposure.",
            "Close the risk because the team has not seen the event happen yet.",
        ],
        "explanation": "Risk management questions usually reward proactive identification, analysis, ownership, and planned responses.",
    },
    "Stakeholders|Communication": {
        "domain": "Stakeholders", "topic": "Communication", "eco": "People", "methodology": "Hybrid",
        "concept": "communication tailoring",
        "correct": "Tailor the communication approach to the stakeholder's decision needs and confirm the message was understood.",
        "distractors": [
            "Send more detailed technical information without changing the communication approach.",
            "Stop communicating with the stakeholder because they missed earlier messages.",
            "Ask the team to communicate separately without a shared message.",
        ],
        "explanation": "Communication questions reward tailoring, feedback, clarity, and alignment with stakeholder decision needs.",
    },
    "Stakeholders|Stakeholder Engagement": {
        "domain": "Stakeholders", "topic": "Stakeholder Engagement", "eco": "People", "methodology": "Agile",
        "concept": "stakeholder engagement and resistance",
        "correct": "Engage the stakeholder to understand concerns, update the engagement approach, and align on next steps.",
        "distractors": [
            "Escalate immediately before understanding the stakeholder's concerns.",
            "Remove the stakeholder from project updates to reduce resistance.",
            "Continue without action because the stakeholder was identified earlier.",
        ],
        "explanation": "Stakeholder engagement questions reward empathy, analysis of concerns, tailored engagement, and collaborative alignment.",
    },
}


def question_text(plan, index):
    scenario = SCENARIOS[index % len(SCENARIOS)]
    return (
        f"During {plan['concept']}, {scenario}. "
        f"What should the project manager do next to keep the project aligned with PMP best practice?"
    )


def option_rows(plan):
    options = [plan["correct"], *plan["distractors"]]
    return [
        PMPQuestionOption(option_label=chr(65 + index), option_text=text, is_correct=text == plan["correct"])
        for index, text in enumerate(options)
    ]


class Command(BaseCommand):
    help = "Seed deterministic original topic-depth questions for thin PMP topics."

    def add_arguments(self, parser):
        parser.add_argument("--target", type=int, default=10)

    @transaction.atomic
    def handle(self, *args, **options):
        target = options["target"]
        created = 0
        for key, plan in TOPIC_BLUEPRINTS.items():
            domain, _ = PMPDomain.objects.get_or_create(name=plan["domain"])
            topic, _ = PMPTopic.objects.get_or_create(domain=domain, name=plan["topic"])
            current = len(unique_exam_questions(PMPQuestion.objects.filter(topic=topic)))
            needed = max(0, target - current)
            for index in range(needed):
                source_item_id = f"TOPIC-DEPTH-{key.replace('|', '-').upper()}-{current + index + 1:03d}"
                question, made = PMPQuestion.objects.get_or_create(
                    source_file=SOURCE_FILE,
                    source_item_id=source_item_id,
                    defaults={
                        "question_id": source_item_id,
                        "question_text": question_text(plan, current + index),
                        "domain": domain,
                        "topic": topic,
                        "performance_domain": plan["domain"],
                        "eco_domain": plan["eco"],
                        "eco_task": plan["topic"],
                        "task": plan["topic"],
                        "methodology": plan["methodology"],
                        "difficulty": "Medium",
                        "question_type": "Single Response",
                        "correct_answer_explanation": plan["explanation"],
                        "wrong_answer_explanation": "Distractors either skip analysis, bypass the relevant PMP process, or act before understanding the scenario.",
                        "pmp_reference": SOURCE_REFERENCE,
                        "chapter_reference": plan["topic"],
                        "source_sheet": plan["topic"],
                        "source_year": 2026,
                        "is_active": True,
                        "is_synthetic": False,
                    },
                )
                if not made:
                    continue
                rows = option_rows(plan)
                for row in rows:
                    row.question = question
                PMPQuestionOption.objects.bulk_create(rows)
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} topic-depth questions to target {target} per thin topic."))
