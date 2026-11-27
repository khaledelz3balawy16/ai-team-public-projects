import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { AssessmentBlock } from '../types/assessment';

interface Props {
  block: AssessmentBlock;
  titleTone?: 'navy' | 'gold' | 'blue';
  themeMode?: 'light' | 'dark';
  onStartQuiz: (type: string) => void;
}

interface LearningStyles {
  auditory?: { percentage: number };
  visual?: { percentage: number };
  reading_writing?: { percentage: number };
  kinesthetic?: { percentage: number };
}

const STYLE_ROWS = [
  { key: 'auditory',        label: 'Auditory',        color: '#172a55' },
  { key: 'visual',          label: 'Visual',          color: '#5a2ca0' },
  { key: 'reading_writing', label: 'Reading/Writing', color: '#f4a000' },
  { key: 'kinesthetic',     label: 'Kinesthetic',     color: '#ef4b67' },
] as const;

function formatLearningAxisLabel(name: string) {
  if (name === 'Reading/Writing') return 'Reading\nWriting';
  if (name === 'Kinesthetic') return 'Kinesth.';
  return name;
}

export function LearningStyle({ block, titleTone = 'blue', themeMode = 'light', onStartQuiz }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const ls = (block.learning_styles ?? {}) as LearningStyles;
  const dominant = (block.dominant_style as string) ?? '';
  const summary   = (block.summary as string) ?? '';

  const data    = STYLE_ROWS.map(row => Number(ls[row.key]?.percentage ?? 0));
  const hasData = data.some(v => v > 0);

  useEffect(() => {
    if (!ref.current || !hasData) return;

    const chart  = echarts.init(ref.current, undefined, {
      devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2),
    });
    const isDark = themeMode === 'dark';
    const textColor  = isDark ? '#f3f7ff' : '#24324a';
    const areaColor  = isDark ? 'rgba(90,44,160,0.25)' : 'rgba(90,44,160,0.15)';
    const lineColor  = '#5a2ca0';
    const splitColor = isDark ? 'rgba(148,163,184,0.18)' : 'rgba(90,44,160,0.12)';

    chart.setOption({
      animation: true,
      animationDuration: 900,
      animationEasing: 'cubicOut',
      tooltip: {
        trigger: 'item',
        appendToBody: true,
        confine: false,
        backgroundColor: 'rgba(23,42,85,0.95)',
        borderWidth: 0,
        borderRadius: 8,
        textStyle: { color: '#fff', fontWeight: 700 },
        extraCssText: 'z-index: 9999; pointer-events: none; box-shadow: 0 14px 32px rgba(15,23,42,0.24);',
        formatter: (params: { name: string; value: number[] }) => {
          return STYLE_ROWS.map((row, i) =>
            `<span style="color:${row.color}">●</span> ${row.label}: <b>${params.value[i]}%</b>`
          ).join('<br/>');
        },
      },
      radar: {
        indicator: STYLE_ROWS.map(row => ({ name: row.label, max: 100 })),
        center: ['50%', '50%'],
        radius: '41%',
        shape: 'polygon',
        splitNumber: 4,
        axisNameGap: 10,
        axisName: {
          color: textColor,
          fontSize: 12,
          fontWeight: 900,
          lineHeight: 15,
          padding: [2, 3],
          textBorderColor: isDark ? 'rgba(17,24,39,0.85)' : 'rgba(255,255,255,0.95)',
          textBorderWidth: 3,
          formatter: formatLearningAxisLabel,
        },
        splitLine:  { lineStyle: { color: splitColor } },
        splitArea:  { show: false },
        axisLine:   { lineStyle: { color: splitColor } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: data,
          name: 'Learning Style',
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: lineColor, width: 2 },
          areaStyle: { color: areaColor },
          itemStyle: {
            color: (params: { dataIndex: number }) => STYLE_ROWS[params.dataIndex]?.color ?? lineColor,
          },
        }],
      }],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);

    return () => {
      chart.dispose();
      ro.disconnect();
    };
  }, [hasData, data, themeMode]);

  return (
    <div id="learningStyleSection" className="dashboard-card learning-style-card">
      <div className="card-header">
        <h3 className={`exam-title-badge ${titleTone}`}>Learning Style Preferences</h3>
      </div>
      <div className="card-body">
        <div className="card-layout">
          <div className="interpretation">
            <h4>Interpretation</h4>
            <p>
              {hasData && dominant
                ? summary || `${dominant} is your strongest learning preference in this assessment.`
                : 'Complete this assessment to discover whether you learn best through sound, visuals, reading and writing, or hands-on practice.'}
            </p>
          </div>

          <div className="radar-wrap">
            {hasData ? (
              <div ref={ref} className="learning-chart" />
            ) : (
              <div className="learning-placeholder-chart" aria-label="Learning style preview">
                <div className="learning-preview-center">LS</div>
                {STYLE_ROWS.map((row, index) => (
                  <span key={row.key} className={`learning-preview-label label-${index}`}>
                    {row.label}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="scores-wrap">
            <h4>{hasData ? 'Styles' : 'Styles'}</h4>
            <div className="learning-score-list">
              {STYLE_ROWS.map((row, index) => {
                const value = data[index];
                return (
                  <div key={row.key} className="learning-score-row">
                    <div>
                      <span>{row.label}</span>
                      {hasData && <strong>{value}%</strong>}
                    </div>
                    <div className="learning-score-track">
                      {hasData ? (
                        <div style={{ width: `${value}%`, backgroundColor: row.color }} />
                      ) : (
                        <div style={{ width: '0%', backgroundColor: row.color }} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
      <div className="card-footer">
        <button className="btn-primary btn-full" onClick={() => onStartQuiz('learning_style')}>
          {hasData ? 'Retake Assessment' : 'Start Assessment'}
        </button>
      </div>
    </div>
  );
}
