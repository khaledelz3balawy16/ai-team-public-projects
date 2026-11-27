import re
from collections import defaultdict
from functools import lru_cache

from django.db.models import Count

from .models import DOMAIN_EXAM_QUESTION_COUNT, PERFORMANCE_DOMAINS, PMPQuestion

QUESTION_BANK_TARGETS = {name: DOMAIN_EXAM_QUESTION_COUNT for name in PERFORMANCE_DOMAINS}
REQUIRED_TOTAL = DOMAIN_EXAM_QUESTION_COUNT * len(PERFORMANCE_DOMAINS)

OFFICIAL_ECO_DOMAINS = ["People", "Process", "Business Environment"]
OFFICIAL_ECO_WEIGHTS = {"People": 33, "Process": 41, "Business Environment": 26}
OFFICIAL_ECO_FALLBACK_MAP = {
    "Stakeholders": "People",
    "Resources": "People",
    "Scope": "Process",
    "Schedule": "Process",
    "Finance": "Process",
    "Risk": "Process",
    "Governance": "Business Environment",
}

DOMAIN_KEYWORDS = {
    "Governance": ["governance", "integration", "change control", "baseline", "business case", "benefit", "strategic"],
    "Scope": ["scope", "requirement", "acceptance criteria", "wbs", "deliverable"],
    "Schedule": ["schedule", "critical path", "milestone", "timeline", "sprint", "iteration"],
    "Finance": ["finance", "cost", "budget", "earned value", "reserve", "cpi", "spi", "contract", "procurement"],
    "Stakeholders": ["stakeholder", "communication", "engagement", "customer", "sponsor"],
    "Resources": ["resource", "team", "leadership", "conflict", "coaching", "functional manager"],
    "Risk": ["risk", "uncertainty", "threat", "opportunity", "mitigation", "compliance", "regulation"],
}
TOPIC_DOMAIN_MAP = {
    "Change Control": "Governance", "Integration Management": "Governance", "Benefits Management": "Governance", "Strategic Alignment": "Governance",
    "Scope Management": "Scope", "Quality Management": "Scope", "Schedule Management": "Schedule", "Agile Delivery": "Schedule",
    "Procurement": "Finance", "Risk Management": "Risk", "Compliance": "Risk", "Stakeholder Engagement": "Stakeholders", "Communication": "Stakeholders",
    "Conflict Management": "Resources", "Team Leadership": "Resources", "Coaching": "Resources", "Organizational Change": "Stakeholders",
}

def normalize_text(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())).strip()

def infer_performance_domain(*values):
    text = " ".join(str(x or "") for x in values)
    normalized = normalize_text(text)
    for topic, domain in TOPIC_DOMAIN_MAP.items():
        if normalize_text(topic) in normalized: return domain
    matches = [domain for domain, words in DOMAIN_KEYWORDS.items() if any(normalize_text(word) in normalized for word in words)]
    return matches[0] if len(matches) == 1 else ""

def question_signature(question):
    option_bits = tuple(normalize_text(option.option_text) for option in question.options.all())
    return (normalize_text(question.question_text), option_bits, normalize_text(question.source_item_id), normalize_text(question.source_sheet))

def canonical_signature(question):
    option_bits = tuple(normalize_text(option.option_text) for option in question.options.all())
    return (normalize_text(question.question_text), option_bits)

def is_valid_exam_question(question):
    if not question.is_active or question.duplicate_of_id or question.is_synthetic or question.performance_domain not in PERFORMANCE_DOMAINS:
        return False
    if "#value!" in (question.question_text or "").lower():
        return False
    if question.exhibit_blob_name and not list(question.exhibits.all()):
        return False
    options = list(question.options.all())
    if len(options) < 2: return False
    return sum(1 for option in options if option.is_correct) >= 1

def unique_exam_questions(queryset=None):
    qs = queryset if queryset is not None else PMPQuestion.objects.all()
    qs = qs.filter(is_active=True, performance_domain__in=PERFORMANCE_DOMAINS, duplicate_of__isnull=True, is_synthetic=False).prefetch_related("options", "exhibits")
    candidates = []
    for question in qs.order_by("id"):
        if is_valid_exam_question(question): candidates.append(question)
    candidates = sorted(candidates, key=lambda q: (q.source_year or 0, -q.id), reverse=True)
    seen, selected = set(), []
    for question in candidates:
        signature = canonical_signature(question)
        if signature in seen: continue
        seen.add(signature); selected.append(question)
    return selected

@lru_cache(maxsize=1)
def cached_unique_exam_questions():
    return unique_exam_questions()

@lru_cache(maxsize=32)
def cached_unique_exam_questions_for_source(source_file):
    return unique_exam_questions(PMPQuestion.objects.filter(source_file=source_file))

def questions_for_domain(domain_name):
    return unique_exam_questions(PMPQuestion.objects.filter(performance_domain=domain_name))


def valid_question_queryset(queryset=None):
    qs = queryset if queryset is not None else PMPQuestion.objects.all()
    return qs.filter(
        is_active=True,
        duplicate_of__isnull=True,
        is_synthetic=False,
        performance_domain__in=PERFORMANCE_DOMAINS,
        options__is_correct=True,
    ).exclude(question_text__icontains="#VALUE!").distinct()


def official_eco_domain(question):
    text = normalize_text(getattr(question, "eco_domain", ""))
    if "people" in text:
        return "People"
    if "process" in text:
        return "Process"
    if "business" in text or "environment" in text:
        return "Business Environment"
    return OFFICIAL_ECO_FALLBACK_MAP.get(getattr(question, "performance_domain", ""), "Process")


def official_eco_quotas(total):
    raw = {domain: total * weight / 100 for domain, weight in OFFICIAL_ECO_WEIGHTS.items()}
    quotas = {domain: int(value) for domain, value in raw.items()}
    remainder = total - sum(quotas.values())
    for domain, _ in sorted(raw.items(), key=lambda item: item[1] - int(item[1]), reverse=True)[:remainder]:
        quotas[domain] += 1
    return quotas


def official_eco_readiness_stats(queryset=None, total=180):
    quotas = official_eco_quotas(total)
    counts = defaultdict(int)
    rows = valid_question_queryset(queryset).values("performance_domain", "eco_domain").annotate(total=Count("id", distinct=True))
    for row in rows:
        eco_text = normalize_text(row.get("eco_domain", ""))
        if "people" in eco_text:
            name = "People"
        elif "business" in eco_text or "environment" in eco_text:
            name = "Business Environment"
        elif "process" in eco_text:
            name = "Process"
        else:
            name = OFFICIAL_ECO_FALLBACK_MAP.get(row.get("performance_domain", ""), "Process")
        counts[name] += row["total"]
    domains = []
    for name in OFFICIAL_ECO_DOMAINS:
        count = counts[name]
        required = quotas[name]
        domains.append({"name": name, "weight": OFFICIAL_ECO_WEIGHTS[name], "count": count, "required": required, "missing": max(0, required - count), "ready": count >= required})
    return {"question_count": total, "duration_minutes": 240, "ready": all(item["ready"] for item in domains), "domains": domains}

def _build_bank_readiness_stats(queryset=None):
    counts = {name: 0 for name in PERFORMANCE_DOMAINS}
    for row in valid_question_queryset(queryset).values("performance_domain").annotate(total=Count("id", distinct=True)):
        counts[row["performance_domain"]] = row["total"]
    base_qs = queryset if queryset is not None else PMPQuestion.objects.all()
    needs_qs = base_qs.filter(import_status="needs_domain_mapping") | base_qs.exclude(performance_domain__in=PERFORMANCE_DOMAINS)
    mapping_needed = [{"id": q.id, "question_id": q.question_id, "question_text": q.question_text[:180]} for q in needs_qs.order_by("id")[:100]]
    domains = []
    for name in PERFORMANCE_DOMAINS:
        count = counts[name]
        required = QUESTION_BANK_TARGETS[name]
        domains.append({"name": name, "count": count, "required": required, "missing": max(0, required - count), "ready": count >= required})
    total = sum(item["count"] for item in domains)
    return {"total": total, "required_total": REQUIRED_TOTAL, "ready": all(item["ready"] for item in domains), "domains": domains, "needs_domain_mapping": mapping_needed}

@lru_cache(maxsize=1)
def _cached_bank_readiness_stats():
    return _build_bank_readiness_stats()

def clear_bank_cache():
    _cached_bank_readiness_stats.cache_clear()
    cached_unique_exam_questions.cache_clear()
    cached_unique_exam_questions_for_source.cache_clear()

def bank_readiness_stats(queryset=None):
    if queryset is not None:
        return _build_bank_readiness_stats(queryset)
    return _cached_bank_readiness_stats()

def domain_exam_ready(domain_name):
    count = len(questions_for_domain(domain_name))
    return {"name": domain_name, "count": count, "required": DOMAIN_EXAM_QUESTION_COUNT, "ready": count >= DOMAIN_EXAM_QUESTION_COUNT, "missing": max(0, DOMAIN_EXAM_QUESTION_COUNT - count)}
