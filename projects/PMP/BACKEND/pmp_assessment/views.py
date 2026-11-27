import random
from functools import lru_cache
from html import escape
from io import BytesIO
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.db.models import Avg, Count, Max, Sum
from django.http import HttpResponse, Http404
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .bank import DOMAIN_EXAM_QUESTION_COUNT, PERFORMANCE_DOMAINS, bank_readiness_stats, cached_unique_exam_questions, cached_unique_exam_questions_for_source, canonical_signature, clear_bank_cache, infer_performance_domain, official_eco_domain, official_eco_quotas, official_eco_readiness_stats, question_signature, questions_for_domain, unique_exam_questions, valid_question_queryset
from .identity.standalone_auth import consume_token, create_profile_for_user, issue_token, send_account_token, touch_profile
from .models import *
from .scoring import calculate_result
from .serializers import *
from .explanations import question_explanation
from .services.ai_report_service import AIReportError, generate_report
from .services.exhibit_storage import fetch_azure_exhibit_asset, fetch_exhibit_blob, fetch_local_exhibit_asset, normalize_blob_name

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def question_exhibit(request, blob_name):
    name = normalize_blob_name(blob_name)
    if not PMPQuestion.objects.filter(exhibit_blob_name=name).exists():
        raise Http404("Question exhibit not found.")
    try:
        blob = fetch_exhibit_blob(name)
    except FileNotFoundError as exc:
        raise Http404(str(exc)) from exc
    response = HttpResponse(blob.content, content_type=blob.content_type or "image/png")
    response["Cache-Control"] = f"private, max-age={settings.AZURE_PMP_EXHIBIT_PROXY_CACHE_SECONDS}"
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exhibit_asset(request, exhibit_id):
    exhibit = PMPExhibit.objects.filter(pk=exhibit_id).first()
    if not exhibit:
        raise Http404("Exhibit not found.")
    try:
        if exhibit.storage_backend == "local":
            asset = fetch_local_exhibit_asset(exhibit.storage_path)
        elif exhibit.storage_backend == "azure":
            asset = fetch_azure_exhibit_asset(exhibit.storage_path)
        else:
            raise FileNotFoundError("Exhibit asset not found.")
    except FileNotFoundError as exc:
        raise Http404(str(exc)) from exc
    response = HttpResponse(asset.content, content_type=asset.content_type)
    response["Cache-Control"] = f"private, max-age={settings.AZURE_PMP_EXHIBIT_PROXY_CACHE_SECONDS}"
    return response
def profile_for(request):
    return request.user.pmp_profile

def serialize_profile(profile):
    data = LearnerProfileSerializer(profile).data
    data["is_admin"] = bool(profile.user and profile.user.is_staff)
    if profile.kbc_registry_id:
        data["kbc_registry"] = KBCRegistrySerializer(profile.kbc_registry).data
    return data


def profile_context_payload(profile):
    return {
        "name": profile.name,
        "job_title": profile.job_title or "",
        "company": profile.company_name or "",
        "industry": profile.industry or "",
        "experience_level": profile.experience_level or "",
        "years_project_experience": str(profile.years_project_experience) if profile.years_project_experience is not None else "",
        "country": profile.country or "",
        "role_description": profile.role_description or "",
        "linkedin_url": profile.linkedin_url or "",
    }


def report_payload(report):
    data = dict(report.report_json or {})
    profile = report.attempt.learner_profile
    data["profile_context"] = profile_context_payload(profile)
    data["profile_updated_at"] = profile.updated_at.isoformat()
    data["report_generated_at"] = report.generated_at.isoformat()
    data["profile_report_stale"] = bool(profile.updated_at and report.generated_at and profile.updated_at > report.generated_at)
    return data


def attempt_deadline(attempt):
    if not attempt.started_at or not attempt.duration_minutes:
        return None
    return attempt.started_at + timezone.timedelta(minutes=attempt.duration_minutes)


def attempt_is_expired(attempt, now=None):
    deadline = attempt_deadline(attempt)
    return bool(deadline and (now or timezone.now()) >= deadline)


def expire_attempt(attempt, now=None):
    now = now or timezone.now()
    attempt.status = "expired"
    attempt.last_activity_at = now
    if attempt.started_at:
        attempt.time_spent_seconds = min(attempt.duration_minutes * 60, max(0, int((now - attempt.started_at).total_seconds())))
    attempt.save(update_fields=["status", "last_activity_at", "time_spent_seconds", "updated_at"])
    return attempt


def expire_stale_attempts(profile, now=None):
    now = now or timezone.now()
    for attempt in profile.attempts.filter(status="in_progress", started_at__isnull=False):
        if attempt_is_expired(attempt, now):
            expire_attempt(attempt, now)

def distribution_quotas(total):
    return official_eco_quotas(total)


def sample_with_visual_priority(pool, count, rng=random):
    pool = list(pool)
    visual = [q for q in pool if list(q.exhibits.all())]
    if not visual:
        return rng.sample(pool, count)
    non_visual = [q for q in pool if not list(q.exhibits.all())]
    visual_count = min(len(visual), count)
    chosen = rng.sample(visual, visual_count)
    if count > visual_count:
        chosen.extend(rng.sample(non_visual, count - visual_count))
    rng.shuffle(chosen)
    return chosen

def evenly_distributed_sample(questions, total, rng=random):
    quotas = distribution_quotas(total)
    chosen = []
    for domain, needed in quotas.items():
        bucket = [q for q in questions if official_eco_domain(q) == domain]
        if len(bucket) < needed:
            return None, f"{domain} contains only {len(bucket)} active questions. {needed} are required for the official PMP simulator blueprint."
        chosen.extend(sample_with_visual_priority(bucket, needed, rng))
    rng.shuffle(chosen)
    return chosen, ""


def practice_set_sample(questions, mode, total):
    if len(questions) < total:
        return None, f"The question bank contains only {len(questions)} active questions. {total} are required for {mode.replace('_', ' ').title()}."
    return sample_with_visual_priority(questions, total, random.Random(mode)), ""


def _build_practice_mock_question_ids(source_file, mode, total=180, all_questions=None):
    exam_number = max(1, int("".join(ch for ch in mode if ch.isdigit()) or "1"))
    source_questions = cached_unique_exam_questions_for_source(source_file)
    if not source_questions:
        return None, f"{mode.replace('_', ' ').title()} has no imported questions yet.", 0
    all_mock_signatures = set()
    for number in range(1, 6):
        for question in cached_unique_exam_questions_for_source(f"exam{number:02d}.xlsx"):
            all_mock_signatures.add(canonical_signature(question))
    own_questions = list(source_questions)
    if len(own_questions) > total:
        chosen, error = evenly_distributed_sample(own_questions, total, random.Random(mode))
        return [q.id for q in chosen] if chosen else None, error, len(source_questions)
    all_questions = all_questions if all_questions is not None else cached_unique_exam_questions()
    chosen = list(own_questions)
    chosen_ids = {q.id for q in chosen}
    chosen_signatures = {canonical_signature(q) for q in chosen}
    current = {name: 0 for name in distribution_quotas(total)}
    for question in chosen:
        current[official_eco_domain(question)] = current.get(official_eco_domain(question), 0) + 1
    legacy_pool = [
        q for q in all_questions
        if not str(q.source_file or "").lower().startswith("exam")
        and q.id not in chosen_ids
        and canonical_signature(q) not in chosen_signatures
        and canonical_signature(q) not in all_mock_signatures
    ]
    additions = []
    for domain, required in distribution_quotas(total).items():
        needed = max(0, required - current.get(domain, 0))
        if not needed:
            continue
        bucket = [q for q in legacy_pool if official_eco_domain(q) == domain]
        bucket.sort(key=lambda q: (0 if list(q.exhibits.all()) else 1, q.id))
        partition = [q for idx, q in enumerate(bucket) if idx % 5 == exam_number - 1]
        picked = partition[:needed]
        if len(picked) < needed:
            return None, f"{domain} has only {len(picked)} non-overlapping legacy questions available for {mode.replace('_', ' ').title()}. {needed} are required to complete it to 180 questions.", len(source_questions)
        additions.extend(picked)
        chosen_ids.update(q.id for q in picked)
        chosen_signatures.update(canonical_signature(q) for q in picked)
    if len(chosen) + len(additions) < total:
        remaining_needed = total - len(chosen) - len(additions)
        remaining = [q for q in legacy_pool if q.id not in chosen_ids and canonical_signature(q) not in chosen_signatures]
        remaining.sort(key=lambda q: (0 if list(q.exhibits.all()) else 1, q.id))
        additions.extend(remaining[:remaining_needed])
    chosen.extend(additions)
    if len(chosen) < total:
        return None, f"{mode.replace('_', ' ').title()} can only be built with {len(chosen)} unique questions. {total} are required.", len(source_questions)
    return [q.id for q in chosen[:total]], "", len(source_questions)


@lru_cache(maxsize=16)
def cached_practice_mock_question_ids(source_file, mode, total=180):
    return _build_practice_mock_question_ids(source_file, mode, total)


def practice_mock_questions(source_file, mode, total=180, all_questions=None):
    if all_questions is None:
        question_ids, error, imported_count = cached_practice_mock_question_ids(source_file, mode, total)
    else:
        question_ids, error, imported_count = _build_practice_mock_question_ids(source_file, mode, total, all_questions)
    if error or not question_ids:
        return None, error, imported_count
    questions_by_id = {
        question.id: question
        for question in PMPQuestion.objects.filter(id__in=question_ids).prefetch_related("options", "exhibits")
    }
    questions = [questions_by_id[question_id] for question_id in question_ids if question_id in questions_by_id]
    if len(questions) < total:
        cached_practice_mock_question_ids.cache_clear()
        return None, f"{mode.replace('_', ' ').title()} can only load {len(questions)} of its fixed questions. Refresh the question bank cache, then try again.", imported_count
    return questions, "", imported_count


def clear_question_selection_caches():
    clear_bank_cache()
    cached_practice_mock_question_ids.cache_clear()


def duration_for_attempt(mode, count):
    if mode == "exam_simulator":
        return 240
    if count >= 180:
        return 240
    if count >= 120:
        return 160
    if count >= 100:
        return 135
    if count >= 40:
        return 60
    return 30


def sample_from_pool(pool, count, label, mode):
    if len(pool) < count:
        return None, f"{label} contains only {len(pool)} active questions. {count} are required for {mode.replace('_', ' ')}."
    return sample_with_visual_priority(pool, count), ""


def user_stats(profile):
    attempts = profile.attempts.all()
    completed = attempts.filter(status__in=["submitted", "report_generated"])
    summary = completed.aggregate(average=Avg("score_percentage"), best=Max("score_percentage"), time_spent=Sum("time_spent_seconds"))
    return {
        "total_attempts": attempts.count(), "completed_attempts": completed.count(),
        "average_score": round(summary["average"] or 0, 2),
        "best_score": summary["best"],
        "latest_score": completed.order_by("-submitted_at", "-updated_at").values_list("score_percentage", flat=True).first(),
        "time_spent_seconds": summary["time_spent"] or 0,
    }

@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request):
    return Response({"csrfToken": get_token(request)})

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    data = serializer.validated_data; email = data["email"]
    existing_user = User.objects.filter(email__iexact=email).first()
    if existing_user:
        authenticated = authenticate(username=existing_user.username, password=data["password"])
        if not authenticated:
            return Response({"detail": "This email already has an account. Please sign in with the correct password."}, status=400)
        login(request, authenticated)
        profile = authenticated.pmp_profile
        touch_profile(profile)
        return Response({"profile": serialize_profile(profile), "existing_account": True})
    registry = KBCPmpLearnerRegistry.objects.filter(normalized_email=email, is_active=True).first()
    full_name = registry.full_name if registry else data.get("full_name", "").strip()
    if not registry and not full_name:
        return Response({"full_name": "Full name is required for external candidates."}, status=400)
    with transaction.atomic():
        username = email
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1; username = f"{email}-{suffix}"
        user = User.objects.create(username=username, email=email, first_name=full_name[:150], is_active=True)
        user.set_password(data["password"]); user.save(update_fields=["password"])
        profile = create_profile_for_user(user, full_name=full_name)
        token = issue_token(user, "email_verification", hours=48)
        send_account_token(user, "email_verification", token)
        login(request, user)
        touch_profile(profile)
    return Response({"profile": serialize_profile(profile), "kbc_recognized": bool(registry), "email_verification_required": True}, status=201)

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    login(request, user)
    profile = user.pmp_profile
    touch_profile(profile)
    return Response({"profile": serialize_profile(profile)})

@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"ok": True})

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.data.get("token")
    user = consume_token(token, "email_verification") if token else None
    if not user: return Response({"detail": "Invalid or expired verification token."}, status=400)
    profile = user.pmp_profile
    profile.email_verified = True; profile.save(update_fields=["email_verified", "updated_at"])
    return Response({"profile": serialize_profile(profile)})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
    if user:
        token = issue_token(user, "password_reset", hours=2)
        send_account_token(user, "password_reset", token)
    return Response({"ok": True})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    user = consume_token(serializer.validated_data["token"], "password_reset")
    if not user: return Response({"detail": "Invalid or expired reset token."}, status=400)
    user.set_password(serializer.validated_data["password"]); user.save(update_fields=["password"])
    return Response({"ok": True})

@api_view(["GET", "PATCH"])
def me(request):
    profile = profile_for(request)
    if request.method == "PATCH":
        previous_marketing_consent = profile.marketing_consent
        serializer = LearnerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True); profile = serializer.save()
        now = timezone.now()
        required = [profile.name, profile.job_title, profile.company_name, profile.industry, profile.country]
        profile.profile_completed = all(bool(str(value or "").strip()) for value in required)
        if profile.marketing_consent and not previous_marketing_consent:
            profile.marketing_consent_at = now
            profile.marketing_opted_out_at = None
        if previous_marketing_consent and not profile.marketing_consent:
            profile.marketing_opted_out_at = now
        profile.save(update_fields=["profile_completed", "marketing_consent_at", "marketing_opted_out_at", "updated_at"])
    return Response({"profile": serialize_profile(profile), "stats": user_stats(profile), "bank": bank_readiness_stats()})

class LearnerCreateView(generics.CreateAPIView):
    queryset = LearnerProfile.objects.all(); serializer_class = LearnerProfileSerializer
    permission_classes = [IsAdminUser]

class DomainListView(generics.ListAPIView):
    serializer_class = DomainSerializer
    permission_classes = [AllowAny]
    def get_queryset(self): return PMPDomain.objects.filter(name__in=PERFORMANCE_DOMAINS).order_by("id")

class TopicListView(generics.ListAPIView):
    serializer_class = TopicSerializer
    def get_queryset(self):
        qs = PMPTopic.objects.select_related("domain").order_by("domain__name", "name")
        return qs.filter(domain_id=self.request.query_params["domain_id"]) if self.request.query_params.get("domain_id") else qs

@api_view(["GET"])
def dashboard(request):
    profile = profile_for(request)
    expire_stale_attempts(profile)
    readiness = {item["name"]: item for item in bank_readiness_stats()["domains"]}
    domains = list(PMPDomain.objects.filter(name__in=PERFORMANCE_DOMAINS).order_by("id"))
    attempt_rows = list(profile.attempts.filter(selected_domain__in=domains).values("selected_domain_id", "status", "score_percentage", "submitted_at", "updated_at"))
    attempts_by_domain = {domain.id: [] for domain in domains}
    for row in attempt_rows:
        attempts_by_domain.setdefault(row["selected_domain_id"], []).append(row)
    domain_cards = []
    for domain in domains:
        rows = attempts_by_domain.get(domain.id, [])
        completed_rows = [row for row in rows if row["status"] in ("submitted", "report_generated")]
        latest = sorted(completed_rows, key=lambda row: (row["submitted_at"] or row["updated_at"], row["updated_at"]), reverse=True)[:1]
        ready = readiness.get(domain.name, {"count": 0, "ready": False, "missing": DOMAIN_EXAM_QUESTION_COUNT})
        domain_cards.append({"id": domain.id, "name": domain.name, "available_questions": ready["count"],
            "exam_ready": ready["ready"], "missing": ready["missing"],
            "attempts": len(rows), "latest_score": latest[0]["score_percentage"] if latest else None,
            "best_score": max([row["score_percentage"] for row in completed_rows if row["score_percentage"] is not None], default=None)})
    official_blueprint = official_eco_readiness_stats()
    simulator_missing = [item for item in official_blueprint["domains"] if not item["ready"]]
    simulator = {"ready": official_blueprint["ready"], "question_count": 180, "duration_minutes": 240, "missing": simulator_missing, "blueprint": official_blueprint["domains"]}
    source_counts = dict(
        valid_question_queryset()
        .filter(source_file__in=[f"exam{number:02d}.xlsx" for number in range(1, 6)])
        .values_list("source_file")
        .annotate(total=Count("id", distinct=True))
    )
    practice_sets = [
        {
            "mode": f"practice_{number}",
            "name": f"Mock Exam {number}",
            "source_file": f"exam{number:02d}.xlsx",
            "imported_questions": source_counts.get(f"exam{number:02d}.xlsx", 0),
            "available_questions": source_counts.get(f"exam{number:02d}.xlsx", 0),
            "question_count": 180,
            "duration_minutes": 240,
            "ready": source_counts.get(f"exam{number:02d}.xlsx", 0) > 0,
            "detail": "Starts a full-length mock exam.",
        }
        for number in range(1, 6)
    ]
    attempts_qs = profile.attempts.select_related("selected_domain", "selected_topic").order_by("-updated_at")
    recent = AttemptSummarySerializer(attempts_qs[:10], many=True).data
    active = attempts_qs.filter(status="in_progress").first()
    active_data = AttemptSummarySerializer(active).data if active else None
    if active_data:
        active_data["answered_count"] = active.answers.exclude(selected_option__isnull=True).count()
    return Response({"profile": serialize_profile(profile), "stats": user_stats(profile), "domains": domain_cards, "simulator": simulator, "practice_sets": practice_sets, "active_attempt": active_data, "recent_attempts": recent})

@api_view(["GET", "POST"])
def attempts(request):
    profile = profile_for(request)
    expire_stale_attempts(profile)
    if request.method == "GET":
        return Response(AttemptSummarySerializer(profile.attempts.select_related("selected_domain", "selected_topic").order_by("-updated_at"), many=True).data)
    active = profile.attempts.filter(status="in_progress").order_by("-updated_at").first()
    if active:
        return Response({"detail": "You already have an in-progress assessment.", "attempt": AttemptSummarySerializer(active).data}, status=409)
    serializer = AttemptCreateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    mode = serializer.validated_data["exam_mode"]
    domain = serializer.validated_data.get("selected_domain")
    topic = serializer.validated_data.get("selected_topic")
    methodology = serializer.validated_data.get("selected_methodology", "")
    difficulty = serializer.validated_data.get("selected_difficulty", "")
    count = serializer.validated_data["question_count"]
    duration = duration_for_attempt(mode, count)
    if mode == "domain":
        ready = questions_for_domain(domain.name)
        if not ready:
            return Response({"detail": f"{domain.name} has no active questions available yet."}, status=400)
        count = min(count, len(ready))
        duration = duration_for_attempt(mode, count)
        chosen = sample_with_visual_priority(ready, count)
    elif mode == "exam_simulator":
        chosen, error = evenly_distributed_sample(unique_exam_questions(), 180)
        if error: return Response({"detail": error}, status=400)
    elif mode == "topic":
        pool = unique_exam_questions(PMPQuestion.objects.filter(topic=topic))
        if not pool:
            return Response({"detail": f"{topic.name} has no active questions available yet."}, status=400)
        count = min(count, len(pool))
        duration = duration_for_attempt(mode, count)
        chosen = sample_with_visual_priority(pool, count)
    elif mode == "methodology":
        pool = unique_exam_questions(PMPQuestion.objects.filter(methodology=methodology))
        chosen, error = sample_from_pool(pool, count, methodology, mode)
        if error: return Response({"detail": error}, status=400)
    elif mode == "difficulty":
        pool = unique_exam_questions(PMPQuestion.objects.filter(difficulty=difficulty))
        chosen, error = sample_from_pool(pool, count, difficulty, mode)
        if error: return Response({"detail": error}, status=400)
    elif mode == "full_practice":
        pool = unique_exam_questions()
        count = min(count, len(pool))
        if not count:
            return Response({"detail": "The question bank has no active questions available for full practice."}, status=400)
        chosen = sample_with_visual_priority(pool, count)
        duration = duration_for_attempt(mode, count)
    elif mode.startswith("practice_"):
        exam_number = "".join(ch for ch in mode if ch.isdigit()).zfill(2)
        chosen, error, imported_count = practice_mock_questions(f"exam{exam_number}.xlsx", mode, 180)
        if error:
            return Response({"detail": error}, status=400)
        count = 180
        duration = duration_for_attempt(mode, count)
    else:
        pool = questions_for_domain(domain.name) if domain else unique_exam_questions()
        label = domain.name if domain else "All Domains"
        chosen, error = sample_from_pool(pool, count, label, mode)
        if error: return Response({"detail": error}, status=400)
    now = timezone.now()
    with transaction.atomic():
        attempt = PMPExamAttempt.objects.create(learner_profile=profile, exam_mode=mode, selected_domain=domain, selected_topic=topic,
            selected_methodology=methodology, selected_difficulty=difficulty, question_count=count,
            duration_minutes=duration, status="in_progress", started_at=now, last_activity_at=now)
        PMPExamAttemptQuestion.objects.bulk_create([PMPExamAttemptQuestion(attempt=attempt, question_id=q.id, order_number=i+1) for i, q in enumerate(chosen)])
    return Response(AttemptSummarySerializer(attempt).data, status=201)

def owned_attempt(request, pk):
    try: return profile_for(request).attempts.get(pk=pk)
    except PMPExamAttempt.DoesNotExist: return None

@api_view(["GET", "DELETE"])
def attempt_detail(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if request.method == "DELETE":
        attempt.delete()
        return Response(status=204)
    return Response(AttemptSummarySerializer(attempt).data)

@api_view(["GET"])
def attempt_questions(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if attempt.status == "in_progress" and attempt_is_expired(attempt):
        expire_attempt(attempt)
        return Response({"detail": "This assessment has expired. Start a new practice session from the dashboard."}, status=409)
    links = list(attempt.attempt_questions.select_related("question__domain", "question__topic").prefetch_related("question__options", "question__exhibits"))
    answer_rows = list(attempt.answers.prefetch_related("selected_options"))
    answers = {a.question_id: [o.id for o in a.selected_options.all()] or ([a.selected_option_id] if a.selected_option_id else []) for a in answer_rows}
    flagged_question_ids = [a.question_id for a in answer_rows if a.is_flagged]
    questions = PublicQuestionSerializer([x.question for x in links], many=True, context={"request": request}).data
    if attempt.status in ("submitted", "report_generated"):
        answer_map = {a.question_id: a for a in answer_rows}
        for item, link in zip(questions, links):
            question = link.question
            correct_ids = [option.id for option in question.options.all() if option.is_correct]
            item["correct_option_ids"] = correct_ids
            item["explanation"] = question_explanation(question)
            item["is_correct"] = bool(answer_map.get(question.id) and answer_map[question.id].is_correct)
    return Response({"attempt": AttemptSummarySerializer(attempt).data, "attempt_id": attempt.id, "exam_mode": attempt.exam_mode, "duration_minutes": attempt.duration_minutes, "started_at": attempt.started_at,
        "last_activity_at": attempt.last_activity_at, "current_question_index": attempt.current_question_index, "status": attempt.status,
        "answers": answers, "flagged_question_ids": flagged_question_ids, "questions": questions})

@api_view(["PUT", "PATCH"])
def save_answer(request, pk, question_id):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if attempt.status != "in_progress": return Response({"detail": "This attempt is not editable."}, status=409)
    serializer = AnswerSaveSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    try: link = attempt.attempt_questions.select_related("question").prefetch_related("question__options").get(question_id=question_id)
    except PMPExamAttemptQuestion.DoesNotExist: return Response({"detail": "Question is not in this attempt."}, status=400)
    raw_ids = serializer.validated_data.get("selected_option_ids", serializer.validated_data.get("selected_option_id"))
    has_selection = "selected_option_ids" in serializer.validated_data or "selected_option_id" in serializer.validated_data
    flag_value = serializer.validated_data.get("is_flagged")
    if has_selection:
        option_ids = raw_ids if isinstance(raw_ids, list) else [raw_ids]
        options_by_id = {o.id: o for o in link.question.options.all()}
        if any(oid not in options_by_id for oid in option_ids): return Response({"detail": "Selected option does not belong to this question."}, status=400)
        selected = [options_by_id[oid] for oid in option_ids]
        correct_ids = {o.id for o in link.question.options.all() if o.is_correct}
        selected_ids = {o.id for o in selected}
        existing = PMPExamAnswer.objects.filter(attempt=attempt, question=link.question).first()
        answer, _ = PMPExamAnswer.objects.update_or_create(attempt=attempt, question=link.question,
            defaults={"attempt_question": link, "selected_option": selected[0] if selected else None, "is_correct": bool(selected_ids) and selected_ids == correct_ids, "answered_at": timezone.now(), "is_flagged": flag_value if flag_value is not None else bool(existing and existing.is_flagged)})
        answer.selected_options.set(selected)
    else:
        answer, _ = PMPExamAnswer.objects.get_or_create(attempt=attempt, question=link.question, defaults={"attempt_question": link, "selected_option": None, "is_correct": False, "answered_at": None})
        if flag_value is not None:
            answer.is_flagged = flag_value
            answer.attempt_question = link
            answer.save(update_fields=["is_flagged", "attempt_question", "updated_at"])
    if "current_question_index" in serializer.validated_data: attempt.current_question_index = serializer.validated_data["current_question_index"]
    attempt.last_activity_at = timezone.now(); attempt.save(update_fields=["current_question_index", "last_activity_at", "updated_at"])
    return Response({"ok": True})

@api_view(["GET"])
def review_attempt_question(request, pk, question_id):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    try:
        link = attempt.attempt_questions.select_related("question").prefetch_related("question__options").get(question_id=question_id)
    except PMPExamAttemptQuestion.DoesNotExist:
        return Response({"detail": "Question is not in this attempt."}, status=400)
    question = link.question
    correct_options = [option for option in question.options.all() if option.is_correct]
    return Response({
        "question_id": question.id,
        "correct_option_ids": [option.id for option in correct_options],
        "correct_answer": "; ".join(option.option_text for option in correct_options),
        "explanation": question_explanation(question),
    })

@api_view(["POST"])
def submit_attempt(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if attempt.status == "in_progress" and attempt_is_expired(attempt):
        expire_attempt(attempt)
        return Response({"detail": "This assessment has expired. Start a new practice session from the dashboard."}, status=409)
    if attempt.status != "in_progress": return Response({"detail": "This attempt has already been submitted."}, status=409)
    now = timezone.now()
    with transaction.atomic():
        attempt = PMPExamAttempt.objects.select_for_update().get(pk=attempt.pk)
        links = list(attempt.attempt_questions.select_related("question"))
        existing = {a.question_id: a for a in attempt.answers.all()}
        for link in links:
            if link.question_id not in existing:
                PMPExamAnswer.objects.create(attempt=attempt, attempt_question=link, question=link.question, selected_option=None, is_correct=False, answered_at=None)
        result = calculate_result(attempt)
        attempt.correct_count = result["correct_count"]; attempt.incorrect_count = result["incorrect_count"]
        attempt.score_percentage = result["score_percentage"]; attempt.status = "submitted"; attempt.submitted_at = now; attempt.last_activity_at = now
        if attempt.started_at: attempt.time_spent_seconds = max(0, int((now-attempt.started_at).total_seconds()))
        attempt.save()
    return Response(result)

@api_view(["POST"])
def abandon_attempt(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if attempt.status != "in_progress": return Response({"detail": "This attempt is already closed."}, status=409)
    attempt.delete()
    return Response({"ok": True, "status": "discarded"})

@api_view(["GET"])
def attempt_result(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    if attempt.status not in ("submitted", "report_generated"): return Response({"detail": "Attempt has not been submitted."}, status=409)
    return Response(calculate_result(attempt))

@api_view(["POST"])
def generate_attempt_report(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    force = bool(request.data.get("force")) if isinstance(request.data, dict) else False
    try: report = generate_report(attempt, force=force)
    except Exception as exc:
        if isinstance(exc, AIReportError):
            code = status.HTTP_409_CONFLICT if "submitted first" in str(exc) else status.HTTP_502_BAD_GATEWAY
            return Response({"detail": str(exc)}, status=code)
        from django.core.exceptions import ImproperlyConfigured
        if isinstance(exc, ImproperlyConfigured): return Response({"detail": str(exc)}, status=503)
        raise
    return Response(report_payload(report))

@api_view(["GET"])
def attempt_report(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    try: report = PMPAIReport.objects.get(attempt=attempt)
    except PMPAIReport.DoesNotExist: return Response({"detail": "Report not generated."}, status=404)
    return Response(report_payload(report))

@api_view(["GET"])
def latest_report(request):
    report = PMPAIReport.objects.filter(attempt__learner_profile=profile_for(request)).order_by("-generated_at").first()
    if not report: return Response({"detail": "No generated reports are available yet."}, status=404)
    return Response(report_payload(report))

@api_view(["GET"])
def latest_report_pdf(request):
    report = PMPAIReport.objects.filter(attempt__learner_profile=profile_for(request)).order_by("-generated_at").only("attempt_id").first()
    if not report: return Response({"detail": "No generated reports are available yet."}, status=404)
    return redirect(f"/api/pmp/attempts/{report.attempt_id}/report/pdf/")

@api_view(["GET"])
def attempt_report_pdf(request, pk):
    attempt = owned_attempt(request, pk)
    if not attempt: return Response({"detail": "Attempt not found."}, status=404)
    try: saved = PMPAIReport.objects.select_related("attempt__learner_profile").get(attempt=attempt)
    except PMPAIReport.DoesNotExist: return Response({"detail": "Report not generated."}, status=404)
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    data = saved.report_json
    learner = saved.attempt.learner_profile
    result = calculate_result(saved.attempt)
    buffer = BytesIO()
    dashboard_page = (14.2*inch, 8.0*inch)
    page_width, _ = dashboard_page
    doc = SimpleDocTemplate(buffer, pagesize=dashboard_page, rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm, title=f"PMP AI Report - {learner.name}", author="PMP Assessment")
    styles = getSampleStyleSheet()
    ink = colors.HexColor("#211633")
    muted = colors.HexColor("#756D83")
    purple = colors.HexColor("#7C3FD1")
    deep = colors.HexColor("#160D21")
    amber = colors.HexColor("#F5A400")
    line = colors.HexColor("#E5E1EE")
    soft = colors.HexColor("#FBF8FF")

    styles.add(ParagraphStyle(name="EyebrowPdf", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#CDA7FF"), uppercase=True, spaceAfter=7))
    styles.add(ParagraphStyle(name="HeroTitlePdf", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=32, leading=37, textColor=colors.white, alignment=TA_LEFT, spaceAfter=8))
    styles.add(ParagraphStyle(name="HeroBodyPdf", parent=styles["Normal"], fontSize=11, leading=16, textColor=colors.HexColor("#E5D9ED")))
    styles.add(ParagraphStyle(name="SectionPdf", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=ink, spaceBefore=15, spaceAfter=9))
    styles.add(ParagraphStyle(name="CardTitlePdf", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=ink, spaceAfter=6))
    styles.add(ParagraphStyle(name="LabelPdf", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=purple, spaceAfter=3))
    styles.add(ParagraphStyle(name="BodyPdf", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=colors.HexColor("#514859"), spaceAfter=5))
    styles.add(ParagraphStyle(name="MutedPdf", parent=styles["Normal"], fontSize=8, leading=11, textColor=muted))
    styles.add(ParagraphStyle(name="KpiValuePdf", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=ink, spaceBefore=2, spaceAfter=0))
    styles.add(ParagraphStyle(name="ScorePdf", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="ScoreSubPdf", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#EADCF8"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="ChapterTitlePdf", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=18, leading=24, textColor=ink, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="ChapterLabelPdf", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=purple, spaceBefore=6, spaceAfter=4))
    styles.add(ParagraphStyle(name="ChapterBodyPdf", parent=styles["BodyText"], fontSize=10.5, leading=17, textColor=colors.HexColor("#514859"), spaceAfter=8))
    styles.add(ParagraphStyle(name="ChapterBulletPdf", parent=styles["BodyText"], fontSize=10, leading=16, leftIndent=12, firstLineIndent=-7, textColor=colors.HexColor("#514859"), spaceAfter=5))

    usable_width = page_width - doc.leftMargin - doc.rightMargin

    def text(value):
        if value is None: return ""
        if isinstance(value, (list, tuple)): return "; ".join(text(x) for x in value if text(x))
        if isinstance(value, dict): return "; ".join(f"{str(k).replace('_', ' ').title()}: {text(v)}" for k, v in value.items() if text(v))
        return str(value)
    def clean(value): return escape(text(value))
    def items(value):
        if not value: return []
        if isinstance(value, list): return value
        if isinstance(value, dict): return [{"title": k, **(v if isinstance(v, dict) else {"detail": v})} for k, v in value.items()]
        return [value]
    def title_for(obj, fallback):
        if not isinstance(obj, dict): return fallback
        for key in ("chapter_title", "title", "area", "topic", "domain", "theme", "day", "focus_area", "priority"):
            if obj.get(key): return text(obj.get(key))
        return fallback
    def stat_card(label, value):
        return [Paragraph(escape(str(label)), styles["MutedPdf"]), Spacer(1, 1.2*mm), Paragraph(escape(str(value)), styles["KpiValuePdf"])]
    def card(raw, fallback, width=None):
        obj = raw if isinstance(raw, dict) else {"detail": raw}
        parts = [Paragraph(clean(title_for(obj, fallback)), styles["CardTitlePdf"])]
        for key, val in obj.items():
            if key in ("chapter_title", "title", "area", "topic", "domain", "theme", "day", "focus_area", "priority") or val in (None, "", []): continue
            parts.append(Paragraph(escape(str(key).replace("_", " ").title()), styles["LabelPdf"]))
            parts.append(Paragraph(clean(val), styles["BodyPdf"]))
        table = Table([[parts]], colWidths=[width or usable_width])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.white),("BOX",(0,0),(-1,-1),0.75,line),("LINEABOVE",(0,0),(-1,0),2,purple),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
        return table
    def append_long_value(bits, key, val, depth=0):
        if val in (None, "", []): return
        label = escape(str(key).replace("_", " ").title())
        if depth == 0:
            bits.append(Paragraph(label, styles["ChapterLabelPdf"]))
        if isinstance(val, dict):
            for subkey, subval in val.items():
                if subval in (None, "", []): continue
                bits.append(Paragraph(f"<b>{escape(str(subkey).replace('_', ' ').title())}</b>", styles["ChapterBulletPdf"]))
                append_long_value(bits, subkey, subval, depth+1)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    line = clean(item)
                else:
                    line = clean(item)
                if line:
                    bits.append(Paragraph(f"- {line}", styles["ChapterBulletPdf"]))
        else:
            bits.append(Paragraph(clean(val), styles["ChapterBodyPdf"]))
    def long_card(raw, fallback):
        obj = raw if isinstance(raw, dict) else {"detail": raw}
        heading = title_for(obj, fallback)
        if obj.get("chapter_number") and obj.get("chapter_title"):
            heading = f"Chapter {obj.get('chapter_number')}: {obj.get('chapter_title')}"
        bits = [Spacer(1, 3*mm), Paragraph(clean(heading), styles["ChapterTitlePdf"])]
        for key, val in obj.items():
            if key in ("chapter_number", "chapter_title", "title", "area", "topic", "domain", "theme", "day", "priority") or val in (None, "", []): continue
            append_long_value(bits, key, val)
        bits.append(Spacer(1, 5*mm))
        return bits
    def section(title, value, columns=2):
        raw_items = items(value)
        if not raw_items: return []
        story_bits = [Paragraph(title, styles["SectionPdf"])]
        if columns <= 1:
            for index, raw in enumerate(raw_items, 1):
                story_bits.extend(long_card(raw, f"{title} {index}"))
            return story_bits
        rows = []
        col_width = (usable_width - (columns-1)*6*mm) / columns
        built = []
        for index, raw in enumerate(raw_items, 1):
            built.append(card(raw, f"{title} {index}", col_width - 2*mm))
        for start in range(0, len(built), columns):
            row = built[start:start+columns]
            while len(row) < columns: row.append("")
            rows.append(row)
        grid = Table(rows, colWidths=[col_width]*columns, hAlign="LEFT")
        grid.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
        return [KeepTogether([Paragraph(title, styles["SectionPdf"]), grid])]
    def chapter_section(title, value):
        raw_items = items(value)
        if not raw_items: return []
        story_bits = [PageBreak(), Paragraph(title, styles["SectionPdf"])]
        for index, raw in enumerate(raw_items, 1):
            if index > 1: story_bits.append(PageBreak())
            story_bits.extend(long_card(raw, f"Chapter {index}"))
        return story_bits
    summary = data.get("performance_summary", {})
    score = summary.get("score_percentage", result.get("score_percentage", 0))
    correct = summary.get("correct_answers", result.get("correct_count", 0))
    incorrect = summary.get("incorrect_answers", result.get("incorrect_count", 0))
    total = result.get("total_questions", (correct or 0) + (incorrect or 0))
    readiness = summary.get("performance_level") or data.get("performance_level") or result.get("performance_level", "PMP readiness")
    story = []

    hero_left = [Paragraph("PMP AI REPORT", styles["EyebrowPdf"]), Paragraph(clean(readiness), styles["HeroTitlePdf"]), Paragraph("Your result is ready. AI analysis has turned this score into a focused study plan.", styles["HeroBodyPdf"])]
    hero_score = [Paragraph(f"{round(float(score or 0))}%", styles["ScorePdf"]), Paragraph("overall score", styles["ScoreSubPdf"])]
    hero = Table([[hero_left, hero_score]], colWidths=[usable_width*0.74, usable_width*0.26])
    hero.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),deep),("BACKGROUND",(1,0),(1,0),colors.HexColor("#2B123D")),("LINEBEFORE",(1,0),(1,0),3,amber),("LINEBELOW",(0,0),(-1,0),2,colors.HexColor("#8B45DC")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,0),18),("RIGHTPADDING",(0,0),(0,0),18),("TOPPADDING",(0,0),(-1,-1),18),("BOTTOMPADDING",(0,0),(-1,-1),18),("LEFTPADDING",(1,0),(1,0),14),("RIGHTPADDING",(1,0),(1,0),14)]))
    story.extend([hero, Spacer(1, 9*mm)])

    stats = Table([[stat_card("Correct", correct), stat_card("Incorrect", incorrect), stat_card("Questions", total)]], colWidths=[usable_width/3-3*mm]*3)
    stats.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.white),("BOX",(0,0),(-1,-1),0.75,line),("INNERGRID",(0,0),(-1,-1),6,colors.white),("LEFTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    story.extend([stats, Spacer(1, 7*mm)])

    ai_head = Table([[Paragraph("AI ANALYSIS", styles["EyebrowPdf"]), Paragraph("Personal result coach", styles["SectionPdf"])]], colWidths=[28*mm, usable_width-28*mm])
    ai_head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.white),("BOX",(0,0),(-1,-1),0.75,line),("LEFTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
    story.append(ai_head)
    readiness_cards = Table([[stat_card("AI readiness", readiness), stat_card("Score evidence", f"{round(float(score or 0), 1)}%")]], colWidths=[usable_width/2-3*mm]*2)
    readiness_cards.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),soft),("BOX",(0,0),(-1,-1),0.75,line),("INNERGRID",(0,0),(-1,-1),6,colors.white),("LEFTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    story.extend([Spacer(1, 5*mm), readiness_cards, Spacer(1, 5*mm)])
    overview = Table([["", Paragraph(clean(data.get("overall_summary", "")), styles["BodyPdf"])]], colWidths=[2*mm, usable_width-2*mm])
    overview.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),purple),("BACKGROUND",(1,0),(1,0),soft),("LEFTPADDING",(1,0),(1,0),10),("RIGHTPADDING",(1,0),(1,0),10),("TOPPADDING",(1,0),(1,0),10),("BOTTOMPADDING",(1,0),(1,0),10)]))
    story.extend([overview, Spacer(1, 4*mm)])

    story.extend(section("Strengths", data.get("strengths"), 3))
    story.extend(section("Weak areas", data.get("weak_areas"), 3))
    themes = data.get("wrong_answer_analysis", {})
    story.extend(section("Wrong answer themes", themes.get("common_themes") if isinstance(themes, dict) else themes, 1))
    story.extend(section("Coaching examples", themes.get("examples") if isinstance(themes, dict) else None, 1))
    story.append(PageBreak())
    story.extend(section("Study recommendations", data.get("study_recommendations"), 1))
    story.extend(chapter_section("Learning chapters", data.get("learning_chapters")))
    story.extend(section("Personalised study plan", data.get("personalised_study_plan"), 1))
    story.extend(section("Exam strategy", data.get("exam_strategy_advice"), 1))
    if data.get("final_advice"):
        final = Table([[Paragraph("FINAL ADVICE", styles["EyebrowPdf"]), Paragraph(clean(data.get("final_advice")), styles["HeroBodyPdf"])]], colWidths=[32*mm, usable_width-32*mm])
        final.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),deep),("LINEBEFORE",(0,0),(0,0),4,amber),("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.extend([Spacer(1, 5*mm), final])

    doc.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pmp-ai-report-attempt-{pk}.pdf"'
    return response
class AdminQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = AdminQuestionSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    def perform_create(self, serializer):
        serializer.save()
        clear_question_selection_caches()
    def perform_update(self, serializer):
        serializer.save()
        clear_question_selection_caches()
    def perform_destroy(self, instance):
        instance.delete()
        clear_question_selection_caches()
    def get_queryset(self):
        qs = PMPQuestion.objects.select_related("domain", "topic", "duplicate_of").prefetch_related("options").order_by("-created_at")
        p = self.request.query_params
        if p.get("performance_domain"): qs = qs.filter(performance_domain=p["performance_domain"])
        if p.get("eco_domain"): qs = qs.filter(eco_domain__icontains=p["eco_domain"])
        if p.get("eco_task"): qs = qs.filter(eco_task__icontains=p["eco_task"])
        if p.get("methodology"): qs = qs.filter(methodology=p["methodology"])
        if p.get("question_type"): qs = qs.filter(question_type=p["question_type"])
        if p.get("source"): qs = qs.filter(source_file__icontains=p["source"])
        if p.get("active") in ("true", "false"): qs = qs.filter(is_active=p["active"] == "true")
        if p.get("needs_mapping") == "true": qs = qs.exclude(performance_domain__in=PERFORMANCE_DOMAINS)
        if p.get("search"): qs = qs.filter(question_text__icontains=p["search"])
        return qs
    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request): return Response(bank_readiness_stats())

def apprenticeship_lead_score(profile):
    completed = profile.attempts.filter(status__in=["submitted", "report_generated"])
    best = completed.aggregate(best=Max("score_percentage"))["best"] or 0
    score = 0
    if profile.profile_completed: score += 20
    if profile.marketing_consent: score += 25
    if profile.apprenticeship_interest: score += 25
    if completed.exists(): score += 20
    if best and best < 65: score += 10
    elif best and best < 80: score += 15
    elif best: score += 5
    return min(score, 100)


def recommended_apprenticeship_offer(best_score):
    if not best_score: return "Intro call + diagnostic PMP pathway"
    if best_score < 65: return "Foundation apprenticeship readiness track"
    if best_score < 80: return "Coached apprenticeship accelerator"
    return "Advanced apprenticeship interview prep"


class AdminProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LearnerProfileSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    queryset = LearnerProfile.objects.select_related("user", "kbc_registry").order_by("-updated_at")

    @action(detail=False, methods=["get"], url_path="sales-leads")
    def sales_leads(self, request):
        rows = []
        profiles = self.get_queryset().filter(marketing_consent=True, apprenticeship_interest=True)
        for profile in profiles:
            completed = profile.attempts.filter(status__in=["submitted", "report_generated"])
            summary = completed.aggregate(best=Max("score_percentage"), average=Avg("score_percentage"))
            latest = completed.order_by("-submitted_at", "-updated_at").first()
            best = summary["best"] or 0
            rows.append({
                "id": profile.id,
                "name": profile.name,
                "email": profile.email,
                "job_title": profile.job_title,
                "company": profile.company_name,
                "industry": profile.industry,
                "country": profile.country,
                "preferred_contact": profile.preferred_contact or "email",
                "marketing_consent_at": profile.marketing_consent_at,
                "completed_attempts": completed.count(),
                "latest_score": latest.score_percentage if latest else None,
                "best_score": best or None,
                "average_score": round(summary["average"] or 0, 2),
                "lead_score": apprenticeship_lead_score(profile),
                "recommended_offer": recommended_apprenticeship_offer(best),
            })
        rows.sort(key=lambda item: item["lead_score"], reverse=True)
        return Response(rows)
class KBCRegistryViewSet(viewsets.ModelViewSet):
    serializer_class = KBCRegistrySerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    queryset = KBCPmpLearnerRegistry.objects.all().order_by("full_name")

@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAdminUser])
def import_questions(request):
    payload = request.data
    if not isinstance(payload, list): return Response({"detail": "Expected a JSON array."}, status=400)
    created, duplicates, mapping_needed, errors = 0, 0, 0, []
    existing = {question_signature(q): q for q in unique_exam_questions(PMPQuestion.objects.all())}
    for index, item in enumerate(payload):
        try:
            data = item.copy(); question_text = data.get("question_text") or data.get("question") or data.get("Question")
            performance_domain = data.get("performance_domain") or data.get("Performance Domain") or ""
            if performance_domain not in PERFORMANCE_DOMAINS: performance_domain = infer_performance_domain(data.get("topic"), data.get("chapter_reference"), data.get("eco_task"), question_text)
            needs_mapping = performance_domain not in PERFORMANCE_DOMAINS
            domain, _ = PMPDomain.objects.get_or_create(name=performance_domain if not needs_mapping else "Unmapped")
            topic_name = data.get("topic") or data.get("source_sheet") or data.get("Source Sheet") or "Imported"; topic, _ = PMPTopic.objects.get_or_create(domain=domain, name=topic_name)
            options_payload = data.get("options") or [{"label": label, "text": data.get(f"option_{label.lower()}") or data.get(f"Option {label}"), "is_correct": label in str(data.get("correct_answer", "")).upper().split(",")} for label in "ABCDE" if data.get(f"option_{label.lower()}") or data.get(f"Option {label}")]
            serializer_data = {"question_id": data.get("question_id") or data.get("Original Question ID") or data.get("id") or "", "performance_domain": performance_domain if not needs_mapping else "Governance", "eco_domain": data.get("eco_domain") or data.get("ECO") or "", "eco_task": data.get("eco_task") or data.get("ECO Task") or data.get("task") or "", "question_type": data.get("question_type") or data.get("Question Type") or "Single Response", "question_text": question_text, "domain": domain.name, "topic": topic.name, "task": data.get("task") or data.get("ECO Task") or "", "methodology": data.get("methodology") or data.get("Methodology") or "General", "difficulty": data.get("difficulty") or "Medium", "correct_answer_explanation": data.get("rationale") or data.get("Rationale") or data.get("correct_answer_explanation") or "", "wrong_answer_explanation": data.get("rationale") or data.get("Rationale") or data.get("wrong_answer_explanation") or "", "source_file": data.get("source_file") or data.get("Source File") or "", "source_sheet": data.get("source_sheet") or data.get("Source Sheet") or "", "source_year": data.get("source_year") or data.get("Source Year"), "source_item_id": data.get("source_item_id") or data.get("Source Item ID") or "", "case_group_id": data.get("case_group_id") or "", "case_text": data.get("case_text") or "", "is_active": not needs_mapping and "#VALUE!" not in str(question_text), "options": options_payload}
            serializer = AdminQuestionSerializer(data=serializer_data); serializer.is_valid(raise_exception=True); question = serializer.save()
            if needs_mapping:
                question.performance_domain = ""; question.import_status = "needs_domain_mapping"; question.is_active = False; question.save(update_fields=["performance_domain", "import_status", "is_active", "updated_at"]); mapping_needed += 1
            signature = question_signature(question); canonical = existing.get(signature)
            if canonical:
                question.duplicate_of = canonical; question.is_active = False; question.save(update_fields=["duplicate_of", "is_active", "updated_at"]); duplicates += 1
            else:
                existing[signature] = question; created += 1
        except Exception as exc: errors.append({"index": index, "error": str(exc)})
    clear_question_selection_caches()
    return Response({"created": created, "duplicates": duplicates, "needs_domain_mapping": mapping_needed, "errors": errors}, status=201 if not errors else 207)
