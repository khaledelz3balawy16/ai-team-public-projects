import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { AssessmentBlock } from '../types/assessment';

interface Props {
  block:       AssessmentBlock;
  onStartQuiz: (type: string) => void;
}

interface LearningStyles {
  auditory?:       { percentage: number };
  visual?:         { percentage: number };
  reading_writing?: { percentage: number };
  kinesthetic?:    { percentage: number };
}

export function LearningStyle({ block, onStartQuiz }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const ls = (block.learning_styles ?? {}) as LearningStyles;
  const dominant    = (block.dominant_style as string) ?? '';
  const summary     = (block.summary as string) ?? '';
  const tips        = (block.recommended_approaches as string[]) ?? [];

  const data = [
    Number(ls.auditory?.percentage ?? 0),
    Number(ls.visual?.percentage ?? 0),
    Number(ls.reading_writing?.percentage ?? 0),
    Number(ls.kinesthetic?.percentage ?? 0),
  ];
  const hasData = data.some(v => v > 0);

  useEffect(() => {
    if (!ref.current || !hasData) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      animation: false,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { top: 10, right: 30, bottom: 30, left: 110 },
      xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      yAxis: {
        type: 'category',
        data: ['Auditory', 'Visual', 'Reading/Writing', 'Kinesthetic'],
      },
      series: [{
        type: 'bar',
        data,
        itemStyle: {
          color: (params: { dataIndex: number }) =>
            ['#8dd3c7', '#57b5e7', '#fbbf72', '#fc8d62'][params.dataIndex],
          borderRadius: 4,
        },
        label: { show: true, position: 'right', formatter: '{c}%' },
      }],
    });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current!);
    return () => { chart.dispose(); ro.disconnect(); };
  }, [hasData, data]);

  return (
    <div id="learningStyleSection" className="dashboard-card">
      <div className="card-header">
        <h3>Learning Style Preferences</h3>
      </div>
      <div className="card-body">
        <div ref={ref} style={{ height: 220, width: '100%' }} />
        {hasData && dominant && (
          <div style={{ marginTop: '1rem' }}>
            <h4>
              Your Dominant Style:{' '}
              <span style={{ color: '#4f2d7f' }}>{dominant}</span>
            </h4>
            {summary && <p>{summary}</p>}
            {tips.length > 0 && (
              <>
                <h4 style={{ marginTop: '0.75rem' }}>Recommended Approaches:</h4>
                <ul style={{ paddingLeft: '1rem' }}>
                  {tips.map((t, i) => (
                    <li key={i} style={{ fontSize: '0.9rem', marginBottom: 4 }}>✓ {t}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
      <div className="card-footer">
        <button className="btn-primary btn-full" onClick={() => onStartQuiz('learning_style')}>
          Take Learning Style Assessment
        </button>
      </div>
    </div>
  );
}
