/**
 * Thin API client — all requests go to /api/* which Vite proxies to Django in dev,
 * and OpenLiteSpeed routes correctly in production.
 */

const BASE = '/api';
const LEARNER_EMAIL_PARAMS = ['email', 'aptem_email'];

export interface AssessmentOption {
  key: string;
  label: string;
  score: number;
  order: number;
}

export interface AssessmentQuestion {
  id: number;
  question_id: string;
  label: string;
  dimension_key: string;
  assessment_type: string;
  question_text: string;
  options: AssessmentOption[];
  is_reverse_scored: boolean;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${withLearnerEmail(path)}`, {
    credentials: 'include',          // send HttpOnly cookie
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  });

  if (res.status === 401) {
    // Token expired → redirect to login
    throw new Error('Unauthenticated');
  }

  if (!res.ok) {
    const text = await res.text();
    let message = '';
    try {
      const data = JSON.parse(text) as { detail?: string; error?: string };
      message = data.detail || data.error || '';
    } catch {
      message = '';
    }
    if (message) {
      throw new Error(message);
    }
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

function withLearnerEmail(path: string) {
  if (typeof window === 'undefined') return path;

  const currentParams = new URLSearchParams(window.location.search);
  const learnerEmail = LEARNER_EMAIL_PARAMS
    .map(key => currentParams.get(key)?.trim())
    .find(Boolean);

  if (!learnerEmail) return path;

  const [basePath, query = ''] = path.split('?');
  const nextParams = new URLSearchParams(query);
  if (!nextParams.has('email') && !nextParams.has('aptem_email')) {
    nextParams.set('email', learnerEmail);
  }

  const nextQuery = nextParams.toString();
  return nextQuery ? `${basePath}?${nextQuery}` : basePath;
}

export const api = {
  getDashboard: () =>
    apiFetch<import('../types/assessment').DashboardResponse>('/dashboard/'),

  assessmentQuestions: (quizType: string) =>
    apiFetch<{ quiz_type: string; quiz_link: string; assessment_type: string; questions: AssessmentQuestion[] }>(
      `/assessment/questions/?quiz_type=${encodeURIComponent(quizType)}`,
    ),

  assessmentSubmit: (payload: { quiz_type: string; answers: Record<string, number | string> }) =>
    apiFetch<{
      ok: boolean;
      response_id: number;
      quiz_link: string;
      scores: Record<string, { mean: number; level: string }>;
    }>(
      '/assessment/submit/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    ),

  assessmentSave: (payload: {
    quiz_type: string;
    scores?: Record<string, { mean: number; level: string }>;
    data?: Record<string, unknown>;
  }) =>
    apiFetch<{ ok: boolean }>('/assessment/save/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  careerPathShown: () =>
    apiFetch<{ ok: boolean }>('/career-path/shown/', { method: 'POST', body: '{}' }),

  careerPathSave: (payload: { career_recommendations: unknown; skills_to_develop: unknown; exams_used?: string[] }) =>
    apiFetch<{ ok: boolean }>('/career-path/save/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  startNewCycle: () =>
    apiFetch<{ ok: boolean; cycle_id: number }>('/new-cycle/', { method: 'POST', body: '{}' }),

  careerPathGenerate: (assessment: unknown) =>
    apiFetch<unknown>('/career-path/generate/', {
      method: 'POST',
      body: JSON.stringify({ assessment }),
    }),
};
