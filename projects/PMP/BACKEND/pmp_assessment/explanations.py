def correct_answer_text(question):
    correct = [option.option_text for option in question.options.all() if option.is_correct]
    return "; ".join(correct) if correct else "the configured correct answer"


DOMAIN_RATIONALES = {
    "Governance": "Governance questions usually reward following the agreed decision path, using evidence, and keeping accountability clear.",
    "Scope": "Scope questions usually reward validating requirements against agreed acceptance criteria before adding, guessing, or changing scope.",
    "Schedule": "Schedule questions usually reward impact analysis before compressing, committing to, or changing the plan.",
    "Risk": "Risk questions usually reward proactive identification, analysis, ownership, and planned responses.",
}


def question_explanation(question):
    existing = question.correct_answer_explanation or question.wrong_answer_explanation
    if existing:
        return existing
    answer = correct_answer_text(question).rstrip(".")
    domain = question.performance_domain or (question.domain.name if question.domain_id else "")
    rationale = DOMAIN_RATIONALES.get(domain, "PMP questions usually reward analysis, collaboration, and using the appropriate process before taking action.")
    return f"The correct answer is: {answer}. {rationale}"
