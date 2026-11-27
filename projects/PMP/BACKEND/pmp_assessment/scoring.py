from .bank import official_eco_domain
from collections import defaultdict
from .explanations import correct_answer_text, question_explanation

def performance_level(score):
    return "Strong readiness" if score >= 80 else "Partial readiness" if score >= 65 else "High risk"

def risk_level(score):
    return "Low" if score >= 80 else "Medium" if score >= 65 else "High"

def selected_answer_text(answer):
    selected = list(answer.selected_options.all())
    if selected:
        return "; ".join(option.option_text for option in selected)
    return answer.selected_option.option_text if answer.selected_option else "Unanswered"

def question_domain(question):
    return question.performance_domain or (question.domain.name if question.domain_id else "Unmapped")

def calculate_result(attempt):
    rows = list(attempt.answers.select_related("question__domain", "question__topic", "selected_option").prefetch_related("question__options", "selected_options"))
    total = attempt.question_count
    correct = sum(a.is_correct for a in rows)
    score = round(correct * 100 / total, 2) if total else 0
    domains, official_domains, topics, incorrect = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0, ""]), []
    for answer in rows:
        q = answer.question
        domain_name = question_domain(q)
        eco_name = official_eco_domain(q)
        domains[domain_name][0] += 1
        domains[domain_name][1] += int(answer.is_correct)
        official_domains[eco_name][0] += 1
        official_domains[eco_name][1] += int(answer.is_correct)
        topic_name = q.topic.name if q.topic else "Uncategorised"
        topics[topic_name][0] += 1
        topics[topic_name][1] += int(answer.is_correct)
        topics[topic_name][2] = domain_name
        if not answer.is_correct:
            incorrect.append({"question_id": q.id, "question": q.question_text,
                "selected_answer": selected_answer_text(answer), "correct_answer": correct_answer_text(q),
                "domain": domain_name, "performance_domain": domain_name, "official_eco_domain": eco_name, "eco_domain": q.eco_domain, "eco_task": q.eco_task or q.task,
                "topic": topic_name, "is_flagged": answer.is_flagged, "explanation": question_explanation(q)})
    domain_data = [{"domain": name, "performance_domain": name, "total_questions": v[0], "correct_answers": v[1], "incorrect_answers": v[0]-v[1],
                    "score_percentage": round(v[1]*100/v[0], 2), "risk_level": risk_level(v[1]*100/v[0])} for name, v in domains.items()]
    official_domain_data = [{"domain": name, "total_questions": v[0], "correct_answers": v[1], "incorrect_answers": v[0]-v[1],
                             "score_percentage": round(v[1]*100/v[0], 2), "risk_level": risk_level(v[1]*100/v[0])} for name, v in official_domains.items()]
    topic_data = [{"topic": name, "domain": v[2], "total_questions": v[0], "correct_answers": v[1], "incorrect_answers": v[0]-v[1],
                   "score_percentage": round(v[1]*100/v[0], 2)} for name, v in topics.items()]
    weak = [{"area": x["domain"], "score_percentage": x["score_percentage"]} for x in domain_data if x["score_percentage"] < 65]
    strong = [{"area": x["domain"], "score_percentage": x["score_percentage"]} for x in domain_data if x["score_percentage"] >= 80]
    return {"attempt_id": attempt.id, "total_questions": total, "correct_count": correct, "incorrect_count": total-correct,
            "score_percentage": score, "performance_level": performance_level(score), "official_domain_breakdown": official_domain_data, "domain_breakdown": domain_data,
            "topic_breakdown": topic_data, "weak_areas": weak, "strengths": strong, "flagged_question_ids": [a.question_id for a in rows if a.is_flagged], "incorrect_answers_review": incorrect}
