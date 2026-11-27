import type { ScoreItem } from '../types/assessment';

interface Props {
  label: string;
  item:  ScoreItem | undefined;
}

function levelColor(level: string): string {
  switch (level.toLowerCase()) {
    case 'very high': case 'high': case 'good': return '#16a34a';
    case 'moderate':  case 'medium':            return '#f59e0b';
    case 'low':       case 'poor':              return '#dc2626';
    default:                                    return '#4f2d7f';
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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
        <span style={{ color: '#6b7280' }}>{label}</span>
        {lvl && (
          <span style={{ fontWeight: 600, color: col }}>
            {lvl} ({mean.toFixed(1)})
          </span>
        )}
      </div>
      <div style={{ background: '#e5e7eb', borderRadius: 9999, height: 8 }}>
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            borderRadius: 9999,
            backgroundColor: col || '#4f2d7f',
            transition: 'width 0.6s ease',
          }}
        />
      </div>
    </div>
  );
}
