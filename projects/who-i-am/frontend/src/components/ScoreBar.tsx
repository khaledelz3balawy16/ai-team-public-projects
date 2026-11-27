import type { ScoreItem } from '../types/assessment';
import type { CSSProperties } from 'react';

interface Props {
  label: string;
  item:  ScoreItem | undefined;
}

function levelColor(level: string): string {
  switch (level.toLowerCase()) {
    case 'very high': case 'high': case 'good': return '#138a36';
    case 'moderate':  case 'medium':            return '#f4a000';
    case 'low':       case 'poor':              return '#ef4b67';
    default:                                    return '#5a2ca0';
  }
}

function levelToPercent(level: string): number {
  switch (level.toLowerCase()) {
    case 'very high': return 95;
    case 'high': case 'good': return 80;
    case 'moderate': case 'medium': return 55;
    case 'low': case 'poor': return 25;
    case 'very low': return 10;
    default: return 0;
  }
}

export function ScoreBar({ label, item }: Props) {
  const lvl  = item?.level ?? '';
  const mean = item?.mean  ?? 0;
  const pct  = levelToPercent(lvl);
  const col  = levelColor(lvl);
  const style = { '--score-color': col, '--score-width': `${pct}%` } as CSSProperties;

  return (
    <div className="score-bar" style={style}>
      <div className="score-bar-row">
        <span>{label}</span>
        {lvl && (
          <span className="score-bar-level">
            {lvl} ({mean.toFixed(1)})
          </span>
        )}
      </div>
      <div className="score-bar-track">
        <div />
      </div>
    </div>
  );
}
