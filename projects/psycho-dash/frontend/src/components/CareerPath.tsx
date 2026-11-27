import { useState } from 'react';
import { api } from '../api/client';
import type { CareerGate, CareerItem, AssessmentData } from '../types/assessment';

interface Props {
  gate:           CareerGate;
  assessmentData: AssessmentData;
  isRawan:        boolean;
  onShown:        () => void;
}

export function CareerPath({ gate, assessmentData, isRawan, onShown }: Props) {
  const [loading,   setLoading]   = useState(false);
  const [careers,   setCareers]   = useState<CareerItem[]>(gate.data ?? []);
  const [skills,    setSkills]    = useState<string[]>(gate.skills ?? []);
  const [shown,     setShown]     = useState(!!gate.data);
  const [error,     setError]     = useState<string | null>(null);
  const [btnLocked, setBtnLocked] = useState(!gate.canShow && !isRawan);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);

    try {
      const raw = await api.careerPathGenerate(assessmentData) as Record<string, unknown>;

      // Same flexible parsing as the original JS
      const list: CareerItem[] = Array.isArray(raw)
        ? raw as CareerItem[]
        : Array.isArray((raw as Record<string, unknown>)['Career recommendations'])
          ? (raw as Record<string, CareerItem[]>)['Career recommendations']
          : Array.isArray((raw as Record<string, unknown>)['career_recommendations'])
            ? (raw as Record<string, CareerItem[]>)['career_recommendations']
            : [];

      const skillList: string[] = Array.isArray((raw as Record<string, unknown>)['skills_to_develop'])
        ? (raw as Record<string, string[]>)['skills_to_develop']
        : [];

      setCareers(list);
      setSkills(skillList);
      setShown(true);

      // Save to DB
      void api.careerPathSave({ career_recommendations: list, skills_to_develop: skillList });

      // Record shown (once per day, non-rawan)
      if (!isRawan) {
        void api.careerPathShown();
        setBtnLocked(true);
        onShown();
      }
    } catch (e) {
      setError('Failed to generate career path. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const btnDisabled = btnLocked || loading || (!gate.canShow && !isRawan);

  return (
    <div className="dashboard-card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Career Path Recommendations</h3>
        <button
          className="btn-primary"
          disabled={btnDisabled}
          onClick={handleGenerate}
          style={{ opacity: btnDisabled ? 0.5 : 1 }}
        >
          {loading ? 'Generating…' : 'Show my career path'}
        </button>
      </div>

      {error && <p style={{ color: '#dc2626', padding: '0 1.25rem' }}>{error}</p>}

      {shown && !loading && (
        <div className="card-body">
          <p style={{ color: '#6b7280', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Based on your personality profile, learning style, and aptitude assessments,
            these career paths align well with your strengths:
          </p>
          <div className="career-grid">
            {careers.map((item, i) => (
              <div key={i} className="career-card">
                <div className="career-icon">💼</div>
                <h4>{item.title}</h4>
                <p>{item.description}</p>
              </div>
            ))}
          </div>
          {skills.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.5rem' }}>Skills to Develop:</h4>
              <ul style={{ paddingLeft: '1rem' }}>
                {skills.map((s, i) => (
                  <li key={i} style={{ fontSize: '0.9rem', color: '#374151', marginBottom: 4 }}>
                    → {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!shown && !loading && (
        <div className="card-body">
          <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            {gate.completed < gate.minRequired
              ? `Complete at least ${gate.minRequired} assessments to unlock your career path recommendations (${gate.completed}/${gate.minRequired} done).`
              : 'Click the button to generate your personalised career path recommendations.'}
          </p>
        </div>
      )}
    </div>
  );
}
