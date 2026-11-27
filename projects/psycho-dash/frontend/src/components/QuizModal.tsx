import { useEffect, useState } from 'react';
import { api, type AssessmentQuestion } from '../api/client';

interface Props {
  quizType: string | null;
  onClose: () => void;
  onSaved?: () => void;
}

interface QuizMeta {
  title: string;
  intro: string;
}

const QUIZ_META: Record<string, QuizMeta> = {
  wellbeing: {
    title: 'Wellbeing Assessment',
    intro: 'Answer the wellbeing questions below. Scores are grouped by the question label.',
  },
  psychological: {
    title: 'Psychological Capital',
    intro: 'Answer the psychological capital questions below.',
  },
  personality: {
    title: 'Personality Traits',
    intro: 'Choose the answer that best describes your usual behaviour.',
  },
  career: {
    title: 'Career Adaptability',
    intro: 'Think about how ready you feel to plan and manage your career.',
  },
  riasec: {
    title: 'Career Interests (RIASEC)',
    intro: 'Rate how naturally each type of work activity appeals to you.',
  },
  ei: {
    title: 'Emotional Intelligence (EI)',
    intro: 'Rate how you understand and manage emotions.',
  },
  work: {
    title: 'Work Values',
    intro: 'Choose what matters most to you in learning and work settings.',
  },
  cognitive: {
    title: 'English & Cognitive Skills',
    intro: 'Answer the English and cognitive skills questions below.',
  },
  logical: {
    title: 'Mathematics & Logical Skills',
    intro: 'Answer the mathematics and logical skills questions below.',
  },
  knowledge: {
    title: 'Knowledge Assessment',
    intro: 'Answer the marketing and business knowledge questions below.',
  },
  skills: {
    title: 'Skills Assessment',
    intro: 'Rate how strongly you can use each practical skill.',
  },
  behaviors: {
    title: 'Behaviors Assessment',
    intro: 'Rate the behaviours you show in learning and teamwork.',
  },
  learning_style: {
    title: 'Learning Style Preferences',
    intro: 'Choose how you prefer to take in and practise new information.',
  },
};

export function QuizModal({ quizType, onClose, onSaved }: Props) {
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number | string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!quizType) return;

    setQuestions([]);
    setIndex(0);
    setAnswers({});
    setError(null);
    setLoading(true);

    api.assessmentQuestions(quizType)
      .then((response) => setQuestions(response.questions))
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load assessment questions.'))
      .finally(() => setLoading(false));
  }, [quizType]);

  if (!quizType) return null;

  const meta = QUIZ_META[quizType] ?? { title: 'Assessment', intro: 'Answer the questions below.' };
  const current = questions[index];
  const selected = current ? answers[String(current.id)] : undefined;
  const answeredCount = Object.keys(answers).length;
  const isLast = questions.length > 0 && index === questions.length - 1;
  const progress = questions.length ? Math.round((answeredCount / questions.length) * 100) : 0;

  const handleSelect = (questionId: number, value: number | string) => {
    setAnswers((currentAnswers) => ({ ...currentAnswers, [String(questionId)]: value }));
    setError(null);
  };

  const handleNext = () => {
    if (!current || selected === undefined) {
      setError('Choose an answer to continue.');
      return;
    }
    setIndex((currentIndex) => Math.min(currentIndex + 1, questions.length - 1));
  };

  const handleBack = () => {
    setIndex((currentIndex) => Math.max(currentIndex - 1, 0));
    setError(null);
  };

  const handleSubmit = async () => {
    if (!current || selected === undefined) {
      setError('Choose an answer to finish.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await api.assessmentSubmit({ quiz_type: quizType, answers });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save assessment.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box quiz-box" onClick={(event) => event.stopPropagation()}>
        <div className="quiz-topline">
          <span>{meta.title}</span>
          <button className="quiz-close" type="button" onClick={onClose} aria-label="Close assessment">
            x
          </button>
        </div>

        {loading ? (
          <div className="quiz-loading">
            <div className="spinner" />
            <p>Loading questions...</p>
          </div>
        ) : current ? (
          <>
            <h3>{current.label || meta.title}</h3>
            <p>{meta.intro}</p>

            <div className="quiz-progress" aria-label={`${progress}% complete`}>
              <div style={{ width: `${progress}%` }} />
            </div>

            <div className="quiz-question">
              <span>
                Question {index + 1} of {questions.length}
                {current.is_reverse_scored ? ' · reverse scored' : ''}
              </span>
              <strong>{current.question_text}</strong>
            </div>

            <div className="quiz-options">
              {current.options.map((option) => (
                <button
                  key={`${current.id}-${option.key}`}
                  type="button"
                  className={selected === option.key ? 'selected' : ''}
                  onClick={() => handleSelect(current.id, option.key)}
                >
                  <span>{option.score}</span>
                  {option.label}
                </button>
              ))}
            </div>

            {error && <div className="quiz-error" role="alert">{error}</div>}

            <div className="quiz-actions">
              <button className="btn-secondary" type="button" onClick={handleBack} disabled={index === 0 || saving}>
                Back
              </button>
              {isLast ? (
                <button className="btn-primary" type="button" onClick={handleSubmit} disabled={saving}>
                  {saving ? 'Saving...' : 'Save Assessment'}
                </button>
              ) : (
                <button className="btn-primary" type="button" onClick={handleNext} disabled={saving}>
                  Next
                </button>
              )}
            </div>
          </>
        ) : (
          <>
            <h3>No Questions Found</h3>
            <p>This assessment does not have imported questions yet.</p>
            {error && <div className="quiz-error" role="alert">{error}</div>}
            <div className="quiz-actions">
              <button className="btn-primary" type="button" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
