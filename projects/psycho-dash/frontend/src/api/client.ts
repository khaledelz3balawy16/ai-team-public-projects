/**
 * Thin API client — all requests go to /api/* which Vite proxies to Django in dev,
 * and OpenLiteSpeed routes correctly in production.
 */

const BASE = '/api';

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
  const res = await fetch(`${BASE}${path}`, {
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
      webhook?: Record<string, unknown>;
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

  careerPathSave: (payload: { career_recommendations: unknown; skills_to_develop: unknown }) =>
    apiFetch<{ ok: boolean }>('/career-path/save/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  careerPathGenerate: (assessment: unknown) =>
    apiFetch<unknown>('/career-path/generate/', {
      method: 'POST',
      body: JSON.stringify({ assessment }),
    }),
};
