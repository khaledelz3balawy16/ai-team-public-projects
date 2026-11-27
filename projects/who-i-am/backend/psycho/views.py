"""
Main API views for the psychological dashboard.

GET  /api/dashboard/          → fetch assessment data for logged-in user
POST /api/career-path/shown/  → record that career path was shown today
POST /api/career-path/save/   → save AI-generated career recommendations
POST /api/career-path/generate/ → generate career recommendations via GPT
"""
import json
import random
import requests as http_requests
from datetime import datetime, timezone, date
from types import SimpleNamespace

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AssessmentScore, SelfAssessmentQuestion, SelfAssessmentQuizResponse
from .db_utils import get_aptem_learner_by_email, get_kbc_user_by_email, get_learner_from_aptem_db


ASSESSMENT_FIELDS = {
    'wellbeing': 'wellbeing_score',
    'psychological': 'psychological_score',
    'personality': 'personality_score',
    'career': 'career_score',
    'riasec': 'riasec_score',
    'ei': 'ei_score',
    'work': 'work_score',
    'cognitive': 'cognitive_score',
    'logical': 'logical_score',
    'knowledge': 'knowledge_score',
    'skills': 'skills_score',
    'behaviors': 'behaviors_score',
    'learning_style': 'learning_style_score',
}

ASSESSMENT_OVERALL_KEYS = {
    'wellbeing': 'overall_wellbeing',
    'psychological': 'overall_psychological',
    'personality': 'overall_personality',
    'career': 'overall_career',
    'riasec': 'overall_riasec',
    'ei': 'overall_ei',
    'work': 'overall_work',
    'cognitive': 'overall_cognitive',
    'logical': 'overall_logical',
    'knowledge': 'overall_knowledge',
    'skills': 'overall_skills',
    'behaviors': 'overall_behaviors',
}

QUIZ_ASSESSMENT_TYPES = {
    'wellbeing': 'wellbeing',
    'psychological': 'Psychological',
    'personality': 'Personality',
    'career': 'Career Adaptability',
    'riasec': 'Career Interests (RIASEC)',
    'ei': 'Emotional Intelligence (EI)',
    'work': 'Work Values',
    'cognitive': 'English',
    'logical': 'Mathematics',
    'knowledge': 'Knowledge Assessment',
    'skills': 'Skills Assessment',
    'behaviors': 'Behaviours Assessment',
    'learning_style': 'learning_style',
}

LABEL_KEY_MAP = {
    'wellbeing': {
        'depression': 'depression',
        'anxiety': 'anxiety',
        'stress': 'stress',
        'sleep_quality': 'sleep_quality',
    },
    'psychological': {
        'hope': 'hope',
        'efficacy': 'efficacy',
        'resilience': 'psych_resilience',
        'optimism': 'optimism',
        'gratitude': 'gratitude',
    },
    'personality': {
        'openness': 'openness',
        'conscientiousness': 'conscientiousness',
        'extraversion': 'extraversion',
        'agreeableness': 'agreeableness',
        'neuroticism': 'neuroticism',
    },
    'career': {
        'career autonomy': 'autonomy',
        'adaptability': 'adaptability',
        'personal resilience': 'career_resilience',
        'identity': 'identity',
    },
    'riasec': {
        'realistic': 'realistic',
        'investigative': 'investigative',
        'artistic': 'artistic',
        'social': 'social',
        'enterprising': 'enterprising',
        'conventional': 'conventional',
    },
    'ei': {
        'self-awareness': 'self_awareness',
        'self-management': 'self_management',
        'social awareness': 'social_awareness',
        'relationship management': 'relationship_management',
    },
    'work': {
        'achievement': 'achievement',
        'independence': 'independence',
        'recognition': 'recognition',
        'relationships': 'relationships',
        'support': 'support',
        'working conditions': 'working_conditions',
    },
    'cognitive': {
        'sentence correction': 'sentence_correction',
        'critical reasoning': 'critical_reasoning',
        'reading comprehension': 'reading_comprehension',
        'verbal intelligence': 'verbal_intelligence',
        'memory & cognitive speed': 'memory_cognitive_speed',
    },
    'logical': {
        'arithmetic': 'arithmetic',
        'algebra': 'algebra',
        'geometry': 'geometry',
        'data interpretation': 'data_interpretation',
        'numerical reasoning': 'numerical_reasoning',
    },
    'knowledge': {
        'marketing concepts': 'marketing_concepts',
        'business awareness': 'business_awareness',
        'market research': 'market_research',
        'products & channels': 'products_channels',
        'digital marketing': 'digital_marketing',
    },
    'skills': {
        'campaign planning': 'campaign_planning',
        'communication': 'communication',
        'project management': 'project_management',
        'data analysis': 'data_analysis',
        'marketing tools': 'marketing_tools',
    },
    'behaviors': {
        'agility & adaptability': 'agility_adaptability',
        'creativity & innovation': 'creativity_innovation',
        'collaboration & teamwork': 'collaboration_teamwork',
    },
    'learning_style': {
        'auditory': 'auditory',
        'visual': 'visual',
        'reading_writing': 'reading_writing',
        'kinesthetic': 'kinesthetic',
    },
}

DEFAULT_QUESTIONS_PER_LABEL = 3
QUESTIONS_PER_LABEL = {
    'wellbeing': 4,       # 4 dims × 4 = 16
    'psychological': 3,   # 5 dims × 3 = 15
    'personality': 3,     # 5 dims × 3 = 15
    'career': 4,          # 4 dims × 4 = 16
    'riasec': 3,          # 6 dims × 3 = 18
    'ei': 4,              # 4 dims × 4 = 16
    'work': 3,            # 6 dims × 3 = 18
    'cognitive': 3,       # 5 dims × 3 = 15
    'logical': 3,         # 5 dims × 3 = 15
    'knowledge': 3,       # 5 dims × 3 = 15
    'skills': 3,          # 5 dims × 3 = 15
    'behaviors': 5,       # 3 dims × 5 = 15
    'learning_style': 4,  # 4 dims × 4 = 16
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_empty(email: str) -> AssessmentScore | None:
    _ensure_assessment_scores_table()
    try:
        return AssessmentScore.objects.get(email__iexact=email)
    except AssessmentScore.DoesNotExist:
        return None


def _public_user():
    return SimpleNamespace(
        email=getattr(settings, 'PUBLIC_DASHBOARD_EMAIL', 'contact+d73bd059faea@example.com'),
        name=getattr(settings, 'PUBLIC_DASHBOARD_NAME', 'KBC Learner'),
        id=getattr(settings, 'PUBLIC_DASHBOARD_LEARNER_ID', None),
    )


def _display_name(user):
    name = getattr(user, 'name', '') or ''
    if name:
        return name

    first_name = getattr(user, 'first_name', '') or ''
    last_name = getattr(user, 'last_name', '') or ''
    full_name = ' '.join(part for part in (first_name, last_name) if part).strip()
    return full_name or getattr(user, 'username', '') or getattr(user, 'email', '') or 'KBC Learner'


def _request_user(request):
    user = getattr(request, 'user', None)
    email = (getattr(user, 'email', '') or '').strip() if user else ''
    query_email = (request.query_params.get('email') or request.query_params.get('aptem_email') or '').strip()
    if not email and query_email and getattr(settings, 'PUBLIC_DASHBOARD_ENABLED', False):
        email = query_email

    if user and getattr(user, 'is_authenticated', False) and email:
        learner = _resolve_aptem_learner(email)
        return SimpleNamespace(
            id=getattr(user, 'id', None),
            email=learner.email,
            name=learner.name or _display_name(user),
            aptem_email=learner.email,
            aptem_learner_id=learner.id,
            aptem_learner_name=learner.name,
        )

    if query_email and getattr(settings, 'PUBLIC_DASHBOARD_ENABLED', False):
        # The "Login to Student Dashboard" redirect carries the learner's email.
        # When KBC_REQUIRE_KNOWN_EMAIL is on, only let them in if that email is a
        # real learner in kbc_users_data — otherwise an arbitrary email in the URL
        # would grant access.
        if getattr(settings, 'KBC_REQUIRE_KNOWN_EMAIL', False):
            if not get_kbc_user_by_email(query_email):
                return None
        return _resolve_aptem_learner(query_email)

    # No JWT login and no ?email= in the request → no access. (The demo/public
    # learner fallback has been removed: the dashboard is reachable only via the
    # "Login to Student Dashboard" redirect that carries the learner's email.)
    return None


def _resolve_aptem_learner(email: str):
    public_user = _public_user()
    fallback = public_user if not email else SimpleNamespace(
        id=None,
        email=email,
        name=public_user.name if email.lower() == public_user.email.lower() else '',
    )
    # Priority: AiTeamKBC aptem_auto_extracting → KBC users DB → aptem cache
    learner = get_learner_from_aptem_db(email) or get_kbc_user_by_email(email) or get_aptem_learner_by_email(email)
    if not learner:
        fallback.aptem_email = fallback.email
        fallback.aptem_learner_id = getattr(fallback, 'id', None)
        fallback.aptem_learner_name = getattr(fallback, 'name', '')
        return fallback

    return SimpleNamespace(
        id=learner.aptem_id,
        email=learner.email,
        name=learner.full_name or learner.email,
        aptem_email=learner.email,
        aptem_learner_id=learner.aptem_id,
        aptem_learner_name=learner.full_name or learner.email,
    )


def _auth_required_response():
    return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)


def _ensure_assessment_scores_table():
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_scores (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(254) UNIQUE NOT NULL,
                wellbeing_score JSONB NULL,
                psychological_score JSONB NULL,
                personality_score JSONB NULL,
                career_score JSONB NULL,
                riasec_score JSONB NULL,
                ei_score JSONB NULL,
                work_score JSONB NULL,
                cognitive_score JSONB NULL,
                logical_score JSONB NULL,
                knowledge_score JSONB NULL,
                skills_score JSONB NULL,
                behaviors_score JSONB NULL,
                learning_style_score JSONB NULL,
                career_recommendations JSONB NULL,
                skills_to_develop JSONB NULL,
                career_path_last_shown TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS assessment_scores_email_idx
            ON assessment_scores (email)
        """)


def _base_label(label: str) -> str:
    value = (label or '').strip()
    if value.endswith('(R)'):
        value = value[:-3].strip()
    return value


def _normalise_label(label: str) -> str:
    return ' '.join(_base_label(label).lower().split())


def _is_reverse_label(label: str) -> bool:
    return (label or '').strip().endswith('(R)')


def _label_to_key(quiz_type: str, label: str) -> str:
    normalised = _normalise_label(label)
    return LABEL_KEY_MAP.get(quiz_type, {}).get(normalised, normalised.replace(' ', '_').replace('-', '_'))


def _mean_to_level(mean: float) -> str:
    if mean >= 4.2:
        return 'Very High'
    if mean >= 3.5:
        return 'High'
    if mean >= 2.5:
        return 'Moderate'
    if mean >= 1.5:
        return 'Low'
    return 'Very Low'


def _option_score(question: SelfAssessmentQuestion, raw_answer):
    selected_option = _selected_option(question, raw_answer)
    if not selected_option:
        return None

    try:
        score = int(selected_option.get('score'))
    except (TypeError, ValueError):
        return None

    if _is_reverse_label(question.label or ''):
        score = 6 - score

    return score


def _default_options():
    return [
        {'key': 'A', 'label': 'Strongly disagree', 'score': 1, 'order': 1},
        {'key': 'B', 'label': 'Disagree', 'score': 2, 'order': 2},
        {'key': 'C', 'label': 'Neutral', 'score': 3, 'order': 3},
        {'key': 'D', 'label': 'Agree', 'score': 4, 'order': 4},
        {'key': 'E', 'label': 'Strongly agree', 'score': 5, 'order': 5},
    ]


def _selected_option(question: SelfAssessmentQuestion, raw_answer):
    if raw_answer is None:
        return None

    raw = str(raw_answer).strip()
    if not raw:
        return None

    options = question.options or _default_options()
    for option in options:
        if not isinstance(option, dict):
            continue
        if raw.lower() in {
            str(option.get('key', '')).strip().lower(),
            str(option.get('label', '')).strip().lower(),
        }:
            return option

    try:
        raw_score = int(raw)
    except ValueError:
        raw_score = None

    if raw_score is not None:
        for option in options:
            if not isinstance(option, dict):
                continue
            try:
                option_score = int(option.get('score'))
            except (TypeError, ValueError):
                continue
            if option_score == raw_score:
                return option

        return {'key': raw, 'label': raw, 'score': raw_score, 'order': None}

    return None


def _serialize_assessment_question(quiz_type: str, question: SelfAssessmentQuestion):
    return {
        'id': question.id,
        'question_id': question.question_id,
        'label': _base_label(question.label or ''),
        'dimension_key': _label_to_key(quiz_type, question.label or ''),
        'assessment_type': question.assessment_type,
        'question_text': question.question_text,
        'options': question.options or _default_options(),
        'is_reverse_scored': _is_reverse_label(question.label or ''),
    }


def _select_questions_for_quiz(quiz_type: str, questions):
    limit = QUESTIONS_PER_LABEL.get(quiz_type, DEFAULT_QUESTIONS_PER_LABEL)
    grouped = {}

    for question in questions:
        group_key = _label_to_key(quiz_type, question.label or '')
        grouped.setdefault(group_key, []).append(question)

    # Shuffle within each group so questions differ every session
    for group_key in grouped:
        random.shuffle(grouped[group_key])

    selected = []
    for group_key in LABEL_KEY_MAP.get(quiz_type, {}).values():
        group_questions = grouped.pop(group_key, [])
        selected.extend(group_questions[:limit])

    for group_key in sorted(grouped):
        selected.extend(grouped[group_key][:limit])

    num_dimensions = len(LABEL_KEY_MAP.get(quiz_type, {}))
    total_cap = limit * num_dimensions if num_dimensions else 15
    return selected[:total_cap]


def _build_scores_from_answers(quiz_type: str, questions, answers: dict):
    grouped = {}
    answer_rows = []

    for question in questions:
        raw_answer = answers.get(str(question.id))
        if raw_answer is None:
            raw_answer = answers.get(str(question.question_id))

        if raw_answer is None:
            continue

        selected_option = _selected_option(question, raw_answer)
        score = _option_score(question, raw_answer)
        dimension_key = _label_to_key(quiz_type, question.label or '')
        original_score = None
        if selected_option:
            try:
                original_score = int(selected_option.get('score'))
            except (TypeError, ValueError):
                original_score = selected_option.get('score')

        answer_rows.append({
            'id': question.id,
            'question_id': question.question_id,
            'label': _base_label(question.label or ''),
            'dimension_key': dimension_key,
            'question_text': question.question_text,
            'selected_answer': {
                'raw': raw_answer,
                'key': selected_option.get('key') if selected_option else None,
                'label': selected_option.get('label') if selected_option else str(raw_answer),
                'score': original_score,
                'order': selected_option.get('order') if selected_option else None,
            },
            'answer': selected_option.get('label') if selected_option else raw_answer,
            'raw_answer': raw_answer,
            'score': score,
            'scored_answer': score,
            'is_reverse_scored': _is_reverse_label(question.label or ''),
        })

        if score is not None:
            grouped.setdefault(dimension_key, []).append(score)

    scores = {}
    for key, values in grouped.items():
        if not values:
            continue
        mean = round(sum(values) / len(values), 2)
        scores[key] = {'mean': mean, 'level': _mean_to_level(mean)}

    all_scores = [row['score'] for row in answer_rows if row['score'] is not None]
    total_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    return answer_rows, scores, total_score


def _overall_from_scores(scores: dict):
    values = []
    for item in scores.values():
        if not isinstance(item, dict):
            continue
        try:
            value = float(item.get('mean'))
        except (TypeError, ValueError):
            continue
        values.append(value)

    if not values:
        return None

    mean = round(sum(values) / len(values), 2)
    return {'mean': mean, 'level': _mean_to_level(mean)}


def _build_learning_style_data(scores: dict):
    total = sum(item.get('mean', 0) for item in scores.values()) or 1
    learning_styles = {
        key: {'percentage': round((item.get('mean', 0) / total) * 100)}
        for key, item in scores.items()
    }
    dominant_key = max(scores, key=lambda key: scores[key].get('mean', 0), default='')
    display = {
        'auditory': 'Auditory',
        'visual': 'Visual',
        'reading_writing': 'Reading/Writing',
        'kinesthetic': 'Kinesthetic',
    }
    dominant = display.get(dominant_key, dominant_key)
    return {
        'learning_styles': learning_styles,
        'dominant_style': dominant,
        'summary': f'{dominant} is your strongest learning preference in this assessment.' if dominant else '',
        'recommended_approaches': [
            f'Use more {dominant.lower()} study activities when learning new topics.' if dominant else 'Use varied study activities.',
            'Mix your dominant style with one supporting style for stronger recall.',
            'Review your results after completing more assessments.',
        ],
    }


def _build_career_gate(row: AssessmentScore | None):
    if row is None:
        completed = 0
    else:
        completed = row.count_completed()

    min_required = 6
    can_show = completed >= min_required

    # Always return saved career data if it exists — prevents regeneration
    saved_data   = row.career_recommendations if row else None
    saved_skills = row.skills_to_develop if row else None

    # Unwrap nested structure if saved in new format
    if isinstance(saved_data, dict) and 'recommendations' in saved_data:
        saved_skills = saved_data.get('skills_to_develop', saved_skills)
        saved_data   = saved_data.get('recommendations')

    return {
        'completed':     completed,
        'minRequired':   min_required,
        'canShow':       can_show,
        'alreadyToday':  False,
        'data':          saved_data,
        'skills':        saved_skills,
    }


# ── views ─────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def dashboard(request):
    """
    Returns all assessment data + career gate for the current user.
    This replaces the PHP shortcode that injected window.ASSESSMENT_DATA.
    """
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    email = user.email

    row = _get_or_empty(email)

    assessment_data = row.to_assessment_data() if row else {
        'wellbeing': {}, 'psychological': {}, 'personality': {},
        'career': {}, 'riasec': {}, 'ei': {}, 'work': {},
        'cognitive': {}, 'logical': {}, 'knowledge': {},
        'skills': {}, 'behaviors': {}, 'learning_style': {},
    }

    career_gate = _build_career_gate(row)

    # Show "Start New Cycle" only when ALL 13 assessments are completed
    all_exam_fields = [
        'wellbeing_score', 'psychological_score', 'personality_score',
        'career_score', 'riasec_score', 'ei_score', 'work_score',
        'cognitive_score', 'logical_score', 'knowledge_score',
        'skills_score', 'behaviors_score', 'learning_style_score',
    ]
    all_done = row is not None and all(getattr(row, f, None) for f in all_exam_fields)
    can_start_new_cycle = all_done

    return Response({
        'user': {
            'email':    user.email,
            'name':     user.name,
            'aptem_learner_id': getattr(user, 'aptem_learner_id', getattr(user, 'id', None)),
            'aptem_email': getattr(user, 'aptem_email', user.email),
            'aptem_learner_name': getattr(user, 'aptem_learner_name', user.name),
        },
        'assessment_data':    assessment_data,
        'career_gate':        career_gate,
        'can_start_new_cycle': can_start_new_cycle,
    })


@api_view(['POST'])
def new_assessment_cycle(request):
    """Create a fresh assessment row and clear current scores — starts a new cycle."""
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    learner_email = (getattr(user, 'aptem_email', user.email) or user.email).strip().lower()
    learner_id    = getattr(user, 'aptem_learner_id', getattr(user, 'id', None))
    learner_name  = getattr(user, 'aptem_learner_name', user.name) or user.name

    # Clear the AssessmentScore row so the dashboard shows blank for the new cycle
    _ensure_assessment_scores_table()
    score_fields_to_clear = [
        'wellbeing_score', 'psychological_score', 'personality_score',
        'career_score', 'riasec_score', 'ei_score', 'work_score',
        'cognitive_score', 'logical_score', 'knowledge_score',
        'skills_score', 'behaviors_score', 'learning_style_score',
        'career_recommendations', 'skills_to_develop', 'career_path_last_shown',
    ]
    score_row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    for f in score_fields_to_clear:
        setattr(score_row, f, None)
    score_row.save(update_fields=score_fields_to_clear)

    new_row = SelfAssessmentQuizResponse.objects.create(
        learner_email=learner_email,
        learner_id=learner_id,
        learner_name=learner_name,
    )
    return Response({'ok': True, 'cycle_id': new_row.id})


@api_view(['POST'])
def career_path_shown(request):
    """Record that career path was shown."""
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    row.career_path_last_shown = datetime.now(timezone.utc)
    row.save(update_fields=['career_path_last_shown'])

    return Response({'ok': True})


@api_view(['POST'])
def career_path_save(request):
    """Save AI-generated career recommendations to DB."""
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    data = request.data
    career_recs  = data.get('career_recommendations')
    skills_list  = data.get('skills_to_develop')
    exams_used   = data.get('exams_used', [])
    model_used   = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    career_payload = {
        'recommendations': career_recs,
        'skills_to_develop': skills_list,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'exams_used': exams_used,
        'model': model_used,
    }

    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    row.career_recommendations = career_payload
    row.skills_to_develop      = skills_list
    row.save(update_fields=['career_recommendations', 'skills_to_develop'])

    # Also save to quiz response row — including all current exam scores
    learner_email = (getattr(user, 'aptem_email', user.email) or user.email).strip().lower()
    try:
        resp_obj = SelfAssessmentQuizResponse.objects.filter(
            learner_email=learner_email
        ).order_by('-created_at').first()
        if resp_obj is None:
            resp_obj = SelfAssessmentQuizResponse.objects.create(
                learner_email=learner_email,
                learner_id=getattr(user, 'aptem_learner_id', getattr(user, 'id', None)),
                learner_name=getattr(user, 'aptem_learner_name', user.name) or user.name,
            )
        resp_obj.career_recommendations = career_payload
        resp_obj.skills_to_develop      = skills_list

        # Snapshot all exam results from assessment_scores into the quiz response row
        _ensure_assessment_scores_table()
        score_row, _ = AssessmentScore.objects.get_or_create(email=user.email)
        exam_column_map = {
            'wellbeing':      score_row.wellbeing_score,
            'psychological':  score_row.psychological_score,
            'personality':    score_row.personality_score,
            'career':         score_row.career_score,
            'riasec':         score_row.riasec_score,
            'ei':             score_row.ei_score,
            'work':           score_row.work_score,
            'cognitive':      score_row.cognitive_score,
            'logical':        score_row.logical_score,
            'knowledge':      score_row.knowledge_score,
            'skills':         score_row.skills_score,
            'behaviors':      score_row.behaviors_score,
            'learning_style': score_row.learning_style_score,
        }
        update_fields = ['career_recommendations', 'skills_to_develop', 'updated_at']
        for col, val in exam_column_map.items():
            if val:
                setattr(resp_obj, col, val)
                update_fields.append(col)

        resp_obj.save(update_fields=update_fields)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error('Failed to save career path for %s: %s', learner_email, exc)

    return Response({'ok': True})


def _format_assessment_for_prompt(assessment: dict) -> str:
    """Convert assessment data dict into a structured text block for the GPT prompt."""
    label_names = {
        'wellbeing':      'Wellbeing',
        'psychological':  'Psychological Capital',
        'personality':    'Personality (Big Five)',
        'career':         'Career Adaptability',
        'riasec':         'Career Interests (RIASEC)',
        'ei':             'Emotional Intelligence',
        'work':           'Work Values',
        'cognitive':      'Cognitive Skills (English)',
        'logical':        'Logical Skills (Maths)',
        'knowledge':      'Marketing Knowledge',
        'skills':         'Marketing Skills',
        'behaviors':      'Professional Behaviours',
        'learning_style': 'Learning Style',
    }
    lines = []
    for key, title in label_names.items():
        block = assessment.get(key) or {}
        scores = block.get('scores') or {}
        if not scores and key == 'learning_style':
            scores = block.get('learning_styles') or {}
        if not scores:
            continue
        lines.append(f'\n[{title}]')
        for dim, val in scores.items():
            if isinstance(val, dict):
                mean  = val.get('mean', '')
                level = val.get('level', '')
                pct   = val.get('percentage', '')
                label = dim.replace('_', ' ').title()
                if pct:
                    lines.append(f'  • {label}: {pct}% ({level})')
                else:
                    lines.append(f'  • {label}: {mean}/5 ({level})')
            else:
                lines.append(f'  • {dim.replace("_", " ").title()}: {val}')
    return '\n'.join(lines) if lines else 'No assessment data available.'


@api_view(['POST'])
def career_path_generate(request):
    """Generate career recommendations using OpenAI GPT based on assessment data."""
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return Response(
            {'error': 'OpenAI API key is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    assessment = request.data.get('assessment', {})
    assessment_text = _format_assessment_for_prompt(assessment)

    system_prompt = """\
You are an AI career advisor integrated with Font Awesome icon search.

Your task is to generate personalised career role recommendations based on a learner's \
psychometric and skills assessment results from a UK marketing higher-education programme.

ASSESSMENT SCORE GUIDE:
- All dimension scores are on a 1–5 mean scale.
- Levels: Very Low (1.0–1.8) | Low (1.8–2.6) | Moderate (2.6–3.4) | High (3.4–4.2) | Very High (4.2–5.0)
- Treat High and Very High dimensions as the learner's core strengths.
- Treat Low and Very Low dimensions as development areas — do not penalise, but factor into role fit.
- For RIASEC, the two highest-scoring types determine the learner's primary career interest code.
- For Learning Style, the dominant style informs preferred working environment.

CAREER ROLE RULES:
- Generate EXACTLY 4 career roles. Never exceed or go below four.
- Roles must be realistic, entry-to-mid-level, employable outcomes aligned with:
  marketing, strategy, digital media, communications, and project coordination.
- Roles must be appropriate for UK higher education and professional training pathways.
- Do NOT invent seniority (e.g. no "Head of", "Director of" unless scores strongly justify it).
- Each description: 2–3 sentences explaining why this role fits THIS learner's specific results.

ICON SELECTION:
- For each role, choose ONE official Font Awesome icon that best represents the career title.
- Use the kebab-case identifier exactly as listed on fontawesome.com (e.g. "bullhorn", "chart-line").
- Prefer solid style. Do NOT invent icon names.

OUTPUT CONSTRAINTS (MANDATORY):
- Output MUST be valid JSON ONLY — no markdown, no code fences, no extra text.
- Return ONLY this exact structure:
{
  "career_recommendations": [
    {
      "title": "string",
      "description": "string",
      "icon": { "name": "string", "style": "solid" }
    }
  ],
  "skills_to_develop": ["string", "string"]
}
- career_recommendations: exactly 4 items.
- skills_to_develop: 5 to 8 items, specific and actionable."""

    user_prompt = (
        f'Learner name: {user.name}\n\n'
        f'Assessment results:\n{assessment_text}\n\n'
        'Using the assessment results above, generate exactly 4 career role recommendations '
        'and 5–8 skills to develop. Follow all rules in the system message exactly.'
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': user_prompt},
            ],
            response_format={'type': 'json_object'},
            temperature=0.7,
            max_tokens=2000,
        )

        raw = completion.choices[0].message.content or '{}'
        result = json.loads(raw)
        return Response(result)

    except Exception as exc:
        return Response(
            {'error': f'Career generation failed: {str(exc)}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(['GET'])
def assessment_questions(request):
    quiz_type = (request.query_params.get('quiz_type') or '').strip()
    assessment_type = QUIZ_ASSESSMENT_TYPES.get(quiz_type)
    if not assessment_type:
        return Response({'error': 'Unknown assessment type.'}, status=status.HTTP_400_BAD_REQUEST)

    questions = list(
        SelfAssessmentQuestion.objects
        .filter(is_active=True, assessment_type__iexact=assessment_type)
        .order_by('label', 'question_id', 'id')
    )
    if not questions:
        return Response({'error': 'No questions found for this assessment.'}, status=status.HTTP_404_NOT_FOUND)

    selected_questions = _select_questions_for_quiz(quiz_type, questions)

    return Response({
        'quiz_type': quiz_type,
        'quiz_link': getattr(settings, 'ASSESSMENT_QUIZ_LINKS', {}).get(quiz_type, ''),
        'assessment_type': questions[0].assessment_type,
        'question_count': len(selected_questions),
        'questions': [_serialize_assessment_question(quiz_type, question) for question in selected_questions],
    })


@api_view(['POST'])
def assessment_submit(request):
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    quiz_type = request.data.get('quiz_type')
    answers = request.data.get('answers')
    assessment_type = QUIZ_ASSESSMENT_TYPES.get(quiz_type)
    field_name = ASSESSMENT_FIELDS.get(quiz_type)

    if not assessment_type or not field_name:
        return Response({'error': 'Unknown assessment type.'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(answers, dict) or not answers:
        return Response({'error': 'Answers must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

    questions = list(
        SelfAssessmentQuestion.objects
        .filter(is_active=True, assessment_type__iexact=assessment_type)
        .order_by('label', 'question_id', 'id')
    )
    if not questions:
        return Response({'error': 'No questions found for this assessment.'}, status=status.HTTP_404_NOT_FOUND)

    _, scores, total_score = _build_scores_from_answers(quiz_type, questions, answers)
    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)

    if quiz_type == 'learning_style':
        payload = _build_learning_style_data(scores)
    else:
        payload = {'scores': scores}
        overall_key = ASSESSMENT_OVERALL_KEYS.get(quiz_type)
        overall = _overall_from_scores(scores)
        if overall_key and overall:
            payload[overall_key] = overall
    payload['completed_at'] = datetime.now(timezone.utc).isoformat()

    setattr(row, field_name, payload)
    row.save(update_fields=[field_name, 'updated_at'])

    learner_email = (getattr(user, 'aptem_email', user.email) or user.email).strip().lower()
    learner_id = getattr(user, 'aptem_learner_id', getattr(user, 'id', None))
    learner_name = getattr(user, 'aptem_learner_name', user.name) or user.name

    try:
        # Always use the latest row for this learner (supports multiple cycles)
        response_obj = SelfAssessmentQuizResponse.objects.filter(
            learner_email=learner_email
        ).order_by('-created_at').first()
        if response_obj is None:
            response_obj = SelfAssessmentQuizResponse.objects.create(
                learner_email=learner_email,
                learner_id=learner_id,
                learner_name=learner_name,
            )
        response_obj.learner_id = learner_id
        response_obj.learner_name = learner_name

        # Save full exam data: scores + raw answers + question details
        # answers keys are str(q.id) — the integer PK sent by the frontend
        question_records = [
            {
                'question_id':   q.question_id,
                'label':         q.label,
                'dimension_key': _label_to_key(quiz_type, q.label or ''),
                'question_text': q.question_text,
                'options':       q.options or [],
                'answer_key':    answers.get(str(q.id)),
                'answer_label':  next(
                    (opt.get('label') for opt in (q.options or []) if opt.get('key') == answers.get(str(q.id))),
                    None,
                ),
            }
            for q in questions
            if str(q.id) in answers
        ]
        setattr(response_obj, quiz_type, {
            'scores':       scores,
            'total_score':  total_score,
            'answers':      answers,
            'questions':    question_records,
            'submitted_at': datetime.now(timezone.utc).isoformat(),
        })
        response_obj.save(update_fields=['learner_id', 'learner_name', quiz_type, 'updated_at'])
        response_id = response_obj.id
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error('Failed to save quiz response for %s: %s', learner_email, exc)
        response_id = None

    return Response({
        'ok': True,
        'response_id': response_id,
        'quiz_link': getattr(settings, 'ASSESSMENT_QUIZ_LINKS', {}).get(quiz_type, ''),
        'scores': scores,
        'assessment_data': row.to_assessment_data(),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def assessment_save(request):
    user = _request_user(request)
    if user is None:
        return _auth_required_response()

    quiz_type = request.data.get('quiz_type')
    scores = request.data.get('scores')
    data = request.data.get('data')

    field_name = ASSESSMENT_FIELDS.get(quiz_type)
    if not field_name:
        return Response({'error': 'Unknown assessment type.'}, status=status.HTTP_400_BAD_REQUEST)

    if data is not None and not isinstance(data, dict):
        return Response({'error': 'Assessment data must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

    if data is None and not isinstance(scores, dict):
        return Response({'error': 'Scores must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    payload = data if data is not None else {'scores': scores}
    payload['completed_at'] = datetime.now(timezone.utc).isoformat()
    setattr(row, field_name, payload)
    row.save(update_fields=[field_name, 'updated_at'])

    return Response({'ok': True, 'assessment_data': row.to_assessment_data()})
