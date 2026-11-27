"""
Main API views for the psychological dashboard.

GET  /api/dashboard/          → fetch assessment data for logged-in user
POST /api/career-path/shown/  → record that career path was shown today
POST /api/career-path/save/   → save AI-generated career recommendations
POST /api/career-path/generate/ → proxy call to n8n webhook
"""
import requests as http_requests
from datetime import datetime, timezone, date
from types import SimpleNamespace

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AssessmentScore, SelfAssessmentQuestion, SelfAssessmentQuizResponse


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

DEFAULT_QUESTIONS_PER_LABEL = 5
QUESTIONS_PER_LABEL = {
    'wellbeing': 5,
    'psychological': 5,
    'personality': 5,
    'career': 5,
    'riasec': 5,
    'ei': 5,
    'work': 5,
    'cognitive': 5,
    'logical': 5,
    'knowledge': 5,
    'skills': 5,
    'behaviors': 5,
    'learning_style': 5,
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
        is_rawan=getattr(settings, 'PUBLIC_DASHBOARD_IS_RAWAN', True),
    )


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

    selected = []
    for group_key in LABEL_KEY_MAP.get(quiz_type, {}).values():
        group_questions = grouped.pop(group_key, [])
        selected.extend(group_questions[:limit])

    for group_key in sorted(grouped):
        selected.extend(grouped[group_key][:limit])

    return selected


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


def _dispatch_assessment_webhook(
    *,
    quiz_type: str,
    assessment_type: str,
    user,
    response_obj: SelfAssessmentQuizResponse,
    answer_rows: list,
    scores: dict,
    total_score,
    assessment_payload: dict,
):
    webhook_url = getattr(settings, 'N8N_ASSESSMENT_WEBHOOK_URLS', {}).get(quiz_type, '')
    if not webhook_url:
        return {'sent': False, 'status': 'not_configured'}

    payload = {
        'source': 'psycho_dashboard',
        'event': 'assessment_submitted',
        'quiz_type': quiz_type,
        'quiz_link': getattr(settings, 'ASSESSMENT_QUIZ_LINKS', {}).get(quiz_type, ''),
        'assessment_type': assessment_type,
        'response_id': response_obj.id,
        'submitted_at': response_obj.submitted_at.isoformat() if response_obj.submitted_at else None,
        'user': {
            'email': user.email,
            'name': user.name,
        },
        'student': {
            'email': user.email,
            'name': user.name,
        },
        'submitted_count': len(answer_rows),
        'answers': answer_rows,
        'question_answers': answer_rows,
        'scores': scores,
        'total_score': total_score,
        'assessment_data': assessment_payload,
    }

    try:
        resp = http_requests.post(
            webhook_url,
            json=payload,
            timeout=getattr(settings, 'N8N_ASSESSMENT_WEBHOOK_TIMEOUT', 30),
        )
        try:
            response_body = resp.json()
        except ValueError:
            response_body = resp.text[:500]

        return {
            'sent': True,
            'ok': resp.ok,
            'status_code': resp.status_code,
            'response': response_body,
        }
    except http_requests.Timeout:
        return {'sent': True, 'ok': False, 'error': 'timeout'}
    except Exception as exc:
        return {'sent': True, 'ok': False, 'error': str(exc)}


def _build_career_gate(row: AssessmentScore | None, is_rawan: bool):
    if row is None:
        completed = 0
    else:
        completed = row.count_completed()

    min_required = 6

    last_shown      = row.career_path_last_shown if row else None
    already_today   = last_shown and last_shown.date() == date.today() if last_shown else False

    if is_rawan:
        can_show        = True
        already_today   = False
        saved_data      = row.career_recommendations if row else None
        saved_skills    = row.skills_to_develop if row else None
    else:
        can_show     = (completed >= min_required) and not already_today
        saved_data   = row.career_recommendations if (row and already_today) else None
        saved_skills = row.skills_to_develop if (row and already_today) else None

    return {
        'completed':     completed,
        'minRequired':   min_required,
        'canShow':       can_show,
        'alreadyToday':  already_today,
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
    user  = _public_user()
    email = user.email

    row = _get_or_empty(email)

    assessment_data = row.to_assessment_data() if row else {
        'wellbeing': {}, 'psychological': {}, 'personality': {},
        'career': {}, 'riasec': {}, 'ei': {}, 'work': {},
        'cognitive': {}, 'logical': {}, 'knowledge': {},
        'skills': {}, 'behaviors': {}, 'learning_style': {},
    }

    career_gate = _build_career_gate(row, user.is_rawan)

    return Response({
        'user': {
            'email':    user.email,
            'name':     user.name,
            'is_rawan': user.is_rawan,
        },
        'assessment_data': assessment_data,
        'career_gate':     career_gate,
    })


@api_view(['POST'])
def career_path_shown(request):
    """Record that career path was shown (once per day for non-rawan users)."""
    user = _public_user()

    if user.is_rawan:
        return Response({'ok': True, 'skipped': True})

    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    row.career_path_last_shown = datetime.now(timezone.utc)
    row.save(update_fields=['career_path_last_shown'])

    return Response({'ok': True})


@api_view(['POST'])
def career_path_save(request):
    """Save AI-generated career recommendations to DB."""
    user = _public_user()
    data = request.data

    _ensure_assessment_scores_table()
    row, _ = AssessmentScore.objects.get_or_create(email=user.email)
    row.career_recommendations = data.get('career_recommendations')
    row.skills_to_develop      = data.get('skills_to_develop')
    row.save(update_fields=['career_recommendations', 'skills_to_develop'])

    return Response({'ok': True})


@api_view(['POST'])
def career_path_generate(request):
    """
    Proxy the n8n career webhook call from backend so the webhook URL
    is never exposed to the browser.
    """
    user = _public_user()

    payload = {
        'source': 'career_path',
        'user': {
            'email': user.email,
            'name':  user.name,
        },
        'assessment': request.data.get('assessment', {}),
    }

    try:
        resp = http_requests.post(
            settings.N8N_CAREER_WEBHOOK_URL,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return Response(resp.json())
    except http_requests.Timeout:
        return Response(
            {'error': 'Career generation timed out. Please try again.'},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as exc:
        return Response(
            {'error': str(exc)},
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
    user = _public_user()
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

    answer_rows, scores, total_score = _build_scores_from_answers(quiz_type, questions, answers)
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

    response_obj = SelfAssessmentQuizResponse.objects.create(
        learner_id=getattr(user, 'id', None),
        learner_name=user.name,
        learner_email=user.email,
        assessment_type=assessment_type,
        answers={
            'quiz_type': quiz_type,
            'assessment_type': assessment_type,
            'learner': {
                'id': getattr(user, 'id', None),
                'name': user.name,
                'email': user.email,
            },
            'submitted_count': len(answers),
            'answers': answer_rows,
        },
        scores=scores,
        total_score=total_score,
    )
    webhook_result = _dispatch_assessment_webhook(
        quiz_type=quiz_type,
        assessment_type=assessment_type,
        user=user,
        response_obj=response_obj,
        answer_rows=answer_rows,
        scores=scores,
        total_score=total_score,
        assessment_payload=payload,
    )

    return Response({
        'ok': True,
        'response_id': response_obj.id,
        'quiz_link': getattr(settings, 'ASSESSMENT_QUIZ_LINKS', {}).get(quiz_type, ''),
        'scores': scores,
        'assessment_data': row.to_assessment_data(),
        'webhook': webhook_result,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def assessment_save(request):
    user = _public_user()
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
