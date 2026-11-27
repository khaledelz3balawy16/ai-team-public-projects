import json
import os
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError, URLError
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from ..models import PMPAIReport
from ..scoring import calculate_result

SYSTEM_PROMPT = """You are an expert PMP assessment analyst, adult learning specialist, project management coach, and study-guide author. Analyse only the supplied data and do not invent facts or references. Missing information must be identified as not provided. Return valid JSON only, without markdown or code fences. Be professional, specific, practical, evidence-based, and use a direct coaching tone.

Return exactly these top-level keys: overall_summary, performance_summary, domain_breakdown, topic_breakdown, wrong_answer_analysis, work_impact_analysis, strengths, weak_areas, study_recommendations, personalised_study_plan, learning_chapters, exam_strategy_advice, final_advice.

For wrong_answer_analysis, return an object with common_themes and examples. Every example must directly illustrate one of the listed common themes and must be supported by an actual incorrect answer in the supplied assessment. Use this structure for each example: theme, scenario, learner_choice, better_approach, lesson. Use plain student-friendly language, explain why the better approach fits the theme, and never copy an unrelated question merely to fill the list. Provide one example for each major common theme when the assessment evidence allows it.

For learning_chapters, create 2 to 3 focused book-style remedial chapters that can later be inserted into a normal study book. These chapters must focus on the learner's weak areas and incorrect answers. Each chapter must be grounded in evidence from the supplied assessment, especially the learner_answer, correct_answer, domain, topic/task, and explanation fields. Do not copy full question banks into the chapter; summarise the scenario and focus on the learning gap.

Each learning_chapters item must use this exact structure: chapter_number, chapter_title, focus_area, why_this_chapter_matters, evidence_from_attempt, core_lesson, student_misconception, correct_thinking_pattern, pmp_concepts_to_review, worked_example, practice_drills, chapter_takeaways.

learning_chapters field requirements:
- evidence_from_attempt: list of 1 to 4 objects with scenario_summary, learner_answer, better_answer, learning_gap.
- core_lesson: concise book-ready teaching content, around 140 to 220 words, not a short bullet list.
- correct_thinking_pattern: a practical mental model the learner can reuse in future PMP questions.
- pmp_concepts_to_review: list of specific concepts/processes/behaviours to revise.
- worked_example: object with scenario, analysis, best_response, why_other_responses_fail.
- practice_drills: list of short drills or reflection tasks.
- chapter_takeaways: list of concise takeaways.

Keep the entire response concise enough for an interactive web app. Prioritise learning_chapters, but avoid excessive length. Do not exceed what is needed for a practical personalised study guide."""
REQUIRED_KEYS = {"overall_summary", "performance_summary", "domain_breakdown", "topic_breakdown", "wrong_answer_analysis", "work_impact_analysis", "strengths", "weak_areas", "study_recommendations", "personalised_study_plan", "learning_chapters", "exam_strategy_advice", "final_advice"}

class AIReportError(Exception): pass

def ensure_dict(value, fallback_key="detail"):
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {fallback_key: value}

def ensure_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]

def normalize_report(report, attempt):
    result = calculate_result(attempt)
    report = ensure_dict(report)
    report.setdefault("overall_summary", "AI analysis was generated for this submitted assessment.")
    report["performance_summary"] = ensure_dict(report.get("performance_summary"))
    report["performance_summary"].setdefault("performance_level", result.get("performance_level", ""))
    report["performance_summary"].setdefault("score_percentage", result.get("score_percentage", 0))
    for key in ("domain_breakdown", "topic_breakdown", "work_impact_analysis", "personalised_study_plan"):
        report[key] = ensure_dict(report.get(key))
    wrong = ensure_dict(report.get("wrong_answer_analysis"))
    wrong["common_themes"] = ensure_list(wrong.get("common_themes"))
    wrong["examples"] = ensure_list(wrong.get("examples"))
    report["wrong_answer_analysis"] = wrong
    for key in ("strengths", "weak_areas", "study_recommendations", "learning_chapters"):
        report[key] = ensure_list(report.get(key))
    report.setdefault("exam_strategy_advice", "Review the incorrect-answer themes and practise similar scenarios before the next attempt.")
    report.setdefault("final_advice", "Use the weak areas and learning chapters as your next study focus.")
    return report

def build_ai_input(attempt):
    result = calculate_result(attempt)
    learner = attempt.learner_profile
    answers = []
    qs = attempt.answers.select_related("question__domain", "question__topic", "selected_option").prefetch_related("question__options", "selected_options")
    for a in qs:
        q = a.question
        selected = list(a.selected_options.all())
        learner_answer = "; ".join(o.option_text for o in selected) if selected else (a.selected_option.option_text if a.selected_option else "Unanswered")
        correct_answers = [o.option_text for o in q.options.all() if o.is_correct]
        domain_name = q.performance_domain or (q.domain.name if q.domain_id else "Unmapped")
        if a.is_correct:
            continue
        answers.append({"question": q.question_text, "learner_answer": learner_answer,
            "correct_answer": "; ".join(correct_answers) if correct_answers else "Not configured", "is_correct": a.is_correct,
            "domain": domain_name, "performance_domain": q.performance_domain, "eco_domain": q.eco_domain, "eco_task": q.eco_task or q.task,
            "topic": q.topic.name if q.topic else None, "task": q.task, "methodology": q.methodology, "question_type": q.question_type,
            "correct_answer_explanation": q.correct_answer_explanation, "wrong_answer_explanation": q.wrong_answer_explanation,
            "pmp_reference": q.pmp_reference or None, "chapter_reference": q.chapter_reference or None})
    return {"learner_profile": {"name": learner.name, "job_title": learner.job_title or None, "company": learner.company_name or None,
        "industry": learner.industry or None, "role_description": learner.role_description or None, "experience_level": learner.experience_level or None},
        "exam_summary": result, "incorrect_answers": answers[:12], "incorrect_answer_count_included": len(answers)}

def local_report(attempt, reason="AI service unavailable"):
    result = calculate_result(attempt)
    score = result.get("score_percentage", 0)
    summary = (
        "This attempt was submitted without any correct answers, so there is not enough meaningful performance evidence to analyse just yet. "
        "Please complete another set with a few attempted answers, and your coaching report will have something worthwhile to work with."
        if score == 0
        else f"Your submitted attempt scored {score}%. This coaching report is based on your saved answers, domain performance, and review evidence."
    )
    weak_domains = sorted(result.get("domain_breakdown", []), key=lambda row: row.get("score_percentage", 0))[:3]
    strong_domains = sorted(result.get("domain_breakdown", []), key=lambda row: row.get("score_percentage", 0), reverse=True)[:3]
    weak_topics = sorted(result.get("topic_breakdown", []), key=lambda row: row.get("score_percentage", 0))[:5]
    incorrect = result.get("incorrect_answers_review", [])[:6]
    weak_names = [row.get("domain") for row in weak_domains if row.get("domain")]
    topic_names = [row.get("topic") for row in weak_topics if row.get("topic")]
    examples = [{
        "theme": item.get("domain") or "PMP reasoning",
        "scenario": item.get("question"),
        "learner_choice": item.get("selected_answer"),
        "better_approach": item.get("correct_answer"),
        "lesson": item.get("explanation") or "Review why the correct answer fits the PMP mindset before retrying similar questions.",
    } for item in incorrect[:3]]
    focus = weak_names[0] if weak_names else "PMP exam readiness"
    chapter_evidence = [{
        "scenario_summary": item.get("question"),
        "learner_answer": item.get("selected_answer"),
        "better_answer": item.get("correct_answer"),
        "learning_gap": item.get("domain") or item.get("topic") or "Exam reasoning",
    } for item in incorrect[:4]]
    if not chapter_evidence:
        chapter_evidence = [{"scenario_summary": "No incorrect answers were available for chapter evidence.", "learner_answer": "Not applicable", "better_answer": "Maintain the same reasoning pattern.", "learning_gap": "Sustain performance under timed conditions."}]
    return normalize_report({
        "overall_summary": summary,
        "performance_summary": {"performance_level": result.get("performance_level", ""), "score_percentage": score},
        "domain_breakdown": {row["domain"]: f"{row['score_percentage']}% ({row['correct_answers']}/{row['total_questions']})" for row in result.get("domain_breakdown", [])},
        "topic_breakdown": {row["topic"]: f"{row['score_percentage']}% in {row['domain']}" for row in result.get("topic_breakdown", [])},
        "wrong_answer_analysis": {
            "common_themes": topic_names[:3] or weak_names or ["Timed answer discipline"],
            "examples": examples,
        },
        "work_impact_analysis": {"focus": "The attempt shows which PMP decision patterns need practice before the next timed session."},
        "strengths": [f"{row['domain']}: {row['score_percentage']}%" for row in strong_domains if row.get("score_percentage", 0) >= 65] or ["Use the review mode to identify repeatable strengths after the next attempt."],
        "weak_areas": [f"{row['domain']}: {row['score_percentage']}%" for row in weak_domains if row.get("score_percentage", 0) < 65] or ["No major weak domain was detected from this attempt."],
        "study_recommendations": [
            "Review each incorrect answer and write down the decision rule that would have led to the correct choice.",
            "Practise the weakest topics first, then retake a shorter timed drill.",
            "For situational questions, identify the real problem before choosing an action.",
        ],
        "personalised_study_plan": {
            "next_session": f"Start with {focus} and review the lowest-scoring topics: {', '.join(topic_names[:3]) or 'not enough topic data'}.",
            "practice": "Use 20 to 40 question drills, then review all missed items before moving to a full attempt.",
            "checkpoint": "Retake a full bank practice after the weak-topic score is consistently above 65%.",
        },
        "learning_chapters": [{
            "chapter_number": 1,
            "chapter_title": f"Fixing the {focus} decision pattern",
            "focus_area": focus,
            "why_this_chapter_matters": "This area had the clearest evidence of missed PMP reasoning in the submitted attempt.",
            "evidence_from_attempt": chapter_evidence,
            "core_lesson": "PMP questions usually reward disciplined analysis before action. When the scenario includes conflict, change, risk, quality, schedule, or stakeholder pressure, slow down and identify the constraint, owner, and next responsible step. Avoid answers that jump straight to escalation, replacement, cancellation, or undocumented changes unless the question clearly says an approved process already supports that step.",
            "student_misconception": "Choosing the fastest visible action instead of the best governed project-management response.",
            "correct_thinking_pattern": "Understand the problem, consult the right artifact or stakeholder, evaluate impact, then act through the approved process.",
            "pmp_concepts_to_review": topic_names[:5] or weak_names or ["Stakeholder engagement", "Risk response", "Change control", "Servant leadership"],
            "worked_example": {
                "scenario": "A project issue appears under pressure and several responses seem possible.",
                "analysis": "The best PMP answer usually protects transparency, collaboration, and process discipline.",
                "best_response": "Choose the response that investigates impact and follows the appropriate plan or governance path.",
                "why_other_responses_fail": "Distractors often skip analysis, bypass stakeholders, or act without approval.",
            },
            "practice_drills": ["Review five missed questions and label the trap in each option.", "Redo a 20-question timed set in the weakest topic.", "Explain each correct answer in one sentence before checking the explanation."],
            "chapter_takeaways": ["Analyse before acting.", "Use the right project artifact.", "Escalate only when the scenario supports it."],
        }],
        "exam_strategy_advice": "For the next attempt, answer in passes: easy questions first, flag uncertain items, then return with a calm PMP mindset.",
        "final_advice": "The report is ready from local scoring data. Replace the AI key later to restore richer AI-written coaching.",
    }, attempt)

def save_report(attempt, report):
    saved, _ = PMPAIReport.objects.update_or_create(attempt=attempt, defaults={
        "report_json": report,
        "overall_summary": report["overall_summary"],
        "performance_level": report.get("performance_summary", {}).get("performance_level", ""),
        "generated_at": timezone.now(),
    })
    attempt.status = "report_generated"; attempt.save(update_fields=["status", "updated_at"])
    return saved

def generate_report(attempt, force=False):
    if attempt.status not in ("submitted", "report_generated"): raise AIReportError("The attempt must be submitted first.")
    existing = PMPAIReport.objects.filter(attempt=attempt).first()
    if existing and not force and existing.report_json.get("learning_chapters"):
        return existing
    key = os.getenv("AI_API_KEY")
    if not key: raise ImproperlyConfigured("AI_API_KEY is not configured.")
    base = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {"model": os.getenv("AI_MODEL", "gpt-4.1-mini"), "response_format": {"type": "json_object"}, "max_tokens": int(os.getenv("AI_REPORT_MAX_TOKENS", "4500")),
               "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(build_ai_input(attempt))}]}
    req = Request(f"{base}/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        # Some managed Windows environments inject a dead localhost proxy.
        # AI calls use a direct TLS connection unless explicitly opted back in.
        opener = build_opener(ProxyHandler({}) if os.getenv("AI_BYPASS_PROXY", "true").lower() == "true" else ProxyHandler())
        with opener.open(req, timeout=120) as response: raw = json.loads(response.read())
        report = json.loads(raw["choices"][0]["message"]["content"])
    except (HTTPError, URLError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return save_report(attempt, local_report(attempt, str(exc)))
    report = normalize_report(report, attempt)
    missing = REQUIRED_KEYS - report.keys()
    if missing: raise AIReportError(f"AI response is missing fields: {', '.join(sorted(missing))}")
    return save_report(attempt, report)
