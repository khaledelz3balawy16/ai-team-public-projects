import { useState } from 'react';
import { api } from '../api/client';
import type { CareerGate, CareerItem, AssessmentData } from '../types/assessment';

const CAREER_LOGO_SRC = '/kbc-mark.svg';
const CAREER_CHARACTER_SRC = '/dashboard-character.png';

interface Props {
  gate: CareerGate;
  assessmentData: AssessmentData;
  onShown: () => void;
}

export function CareerPath({ gate, assessmentData, onShown }: Props) {
  const [loading, setLoading] = useState(false);
  const [careers, setCareers] = useState<CareerItem[]>(gate.data ?? []);
  const [skills, setSkills] = useState<string[]>(gate.skills ?? []);
  const [shown, setShown] = useState(!!gate.data);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);

    try {
      const raw = await api.careerPathGenerate(assessmentData) as Record<string, unknown>;

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

      const examsUsed = Object.entries(assessmentData)
        .filter(([, v]) => v && typeof v === 'object' && Object.keys(v as object).length > 0)
        .map(([k]) => k);

      void api.careerPathSave({
        career_recommendations: list,
        skills_to_develop: skillList,
        exams_used: examsUsed,
      });

      void api.careerPathShown();
      onShown();
    } catch (e) {
      setError('Failed to generate career path. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const alreadyGenerated = careers.length > 0;
  const btnDisabled = loading || alreadyGenerated || !gate.canShow;
  const remaining = Math.max(gate.minRequired - gate.completed, 0);
  const logo = <img src={CAREER_LOGO_SRC} alt="" />;
  const careerCharacter = <img src={CAREER_CHARACTER_SRC} alt="" />;

  return (
    <div className="dashboard-card career-path-panel">
      <div className="career-path-hero">
        <div className="career-path-title">
          <div className="career-path-icon career-path-character" aria-hidden="true">{careerCharacter}</div>
          <div>
            <span className="career-kicker">Career prediction</span>
            <h3>Career Path Recommendations</h3>
            <p>
              Predict the jobs that best suit the learner based on assessment results,
              strengths, learning style, and career interests.
            </p>
          </div>
        </div>

        <div className="career-path-actions">
          <div className="unlock-pill">
            {gate.completed}/{gate.minRequired} exams completed
          </div>
          <button
            className="btn-primary career-generate-btn"
            disabled={btnDisabled}
            onClick={handleGenerate}
          >
            {loading ? 'Generating...' : 'Show my career path'}
          </button>
        </div>
      </div>

      {error && <div className="career-error" role="alert">{error}</div>}

      {shown && !loading && (
        <div className="card-body career-path-body">
          <p className="career-path-copy">
            Based on the learner profile, these career paths currently align best with
            the completed assessment data.
          </p>
          <div className="career-grid">
            {careers.map((item, index) => (
              <div key={index} className="career-card">
                <div className="career-icon" aria-hidden="true">
                  {item.icon?.name
                    ? <i className={`fa-${item.icon.style ?? 'solid'} fa-${item.icon.name}`} />
                    : logo}
                </div>
                <h4>{item.title}</h4>
                <p>{item.description}</p>
              </div>
            ))}
          </div>
          {skills.length > 0 && (
            <div className="skills-panel">
              <h4>Skills to Develop</h4>
              <ul>
                {skills.map((skill, index) => (
                  <li key={index}>{skill}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!shown && !loading && (
        <div className="card-body career-path-body">
          <div className="career-unlock-panel">
            <div className="career-unlock-icon" aria-hidden="true">{logo}</div>
            <div>
              <h4>{remaining > 0 ? 'Career prediction is still locked' : 'Career prediction is ready'}</h4>
              <p>
                {remaining > 0
                  ? `Complete ${remaining} more core assessment${remaining === 1 ? '' : 's'} to unlock AI career recommendations.`
                  : 'The learner has enough assessment data. Generate personalised career recommendations now.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
