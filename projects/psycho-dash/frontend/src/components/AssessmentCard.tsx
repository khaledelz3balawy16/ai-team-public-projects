/**
 * Generic card used for every radar+scores section.
 * The PHP shortcode generated all these inline — now one reusable component.
 */
import { RadarChart } from './RadarChart';
import { ScoreBar }   from './ScoreBar';
import type { AssessmentBlock, ScoreItem } from '../types/assessment';

interface ScoreDef {
  key:   string;
  label: string;
}

interface Props {
  id?:         string;
  title:       string;
  chartId:     string;
  block:       AssessmentBlock;
  scoreDefs:   readonly ScoreDef[];
  overallKey?: string;
  quizType:    string;
  interpretation: string;
  onStartQuiz: (type: string) => void;
}

function getScores(block: AssessmentBlock): Record<string, ScoreItem> {
  if (block.scores && typeof block.scores === 'object') {
    return block.scores as Record<string, ScoreItem>;
  }
  // flat structure
  return block as unknown as Record<string, ScoreItem>;
}

export function AssessmentCard({
  id, title, chartId, block, scoreDefs, overallKey, quizType, interpretation, onStartQuiz,
}: Props) {
  const scores = getScores(block);
  const keys   = scoreDefs.map(s => s.key);
  const labels = scoreDefs.map(s => s.label);
  const overall = overallKey && block[overallKey] && typeof block[overallKey] === 'object'
    ? block[overallKey] as ScoreItem
    : null;

  return (
    <div id={id} className="dashboard-card">
      <div className="card-header">
        <h3>{title}</h3>
      </div>
      <div className="card-body">
        <div className="card-layout">
          {/* Interpretation */}
          <div className="interpretation">
            <h4>Interpretation</h4>
            <p>{interpretation}</p>
          </div>

          {/* Radar */}
          <div className="radar-wrap">
            <RadarChart id={chartId} keys={keys} labels={labels} scores={scores} overall={overall} />
          </div>

          {/* Score bars */}
          <div className="scores-wrap">
            <h4>Scores</h4>
            <div className="scores-list">
              {scoreDefs.map(({ key, label }) => (
                <ScoreBar key={key} label={label} item={scores[key]} />
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="card-footer">
        <button className="btn-primary" onClick={() => onStartQuiz(quizType)}>
          ↻ Start Assessment
        </button>
      </div>
    </div>
  );
}
