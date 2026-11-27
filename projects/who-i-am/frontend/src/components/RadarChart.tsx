import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { ScoreItem } from '../types/assessment';

interface Props {
  id:     string;
  keys:   string[];
  labels: string[];
  scores: Record<string, ScoreItem>;
  overall?: ScoreItem | null;
  themeMode?: 'light' | 'dark';
}

function formatMean(m: number) { return m.toFixed(1); }

function levelClass(level: string) {
  return `level-${level.toLowerCase().replace(/\s+/g, '-')}`;
}

function meanToLevel(m: number): string {
  if (m >= 4.2) return 'Very High';
  if (m >= 3.5) return 'High';
  if (m >= 2.5) return 'Moderate';
  if (m >= 1.5) return 'Low';
  return 'Very Low';
}

function computeOverall(scores: Record<string, ScoreItem>, keys: string[]) {
  const vals = keys.map(k => Number(scores[k]?.mean)).filter(v => Number.isFinite(v));
  if (!vals.length) return null;
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  return { mean, level: meanToLevel(mean) };
}

const CHART_LABEL_OVERRIDES: Record<string, string> = {
  'Career Autonomy': 'Career\nAutonomy',
  'Personal Resilience': 'Personal\nResilience',
  'Sentence Correction': 'Sentence\nCorrection',
  'Critical Reasoning': 'Critical\nReasoning',
  'Reading Comprehension': 'Reading\nCompreh.',
  'Verbal Intelligence': 'Verbal\nIntel.',
  'Memory & Cognitive Speed': 'Memory &\nCog. Speed',
  'Numerical Reasoning': 'Numerical\nReasoning',
  'Data Interpretation': 'Data\nInterp.',
  'Marketing Concepts': 'Marketing\nConcepts',
  'Business Awareness': 'Business\nAwareness',
  'Market Research': 'Market\nResearch',
  'Products & Channels': 'Products &\nChannels',
  'Digital Marketing': 'Digital\nMarketing',
  'Campaign Planning': 'Campaign\nPlanning',
  'Communication': 'Comms',
  'Project Management': 'Project\nManagement',
  'Marketing Tools': 'Marketing\nTools',
  'Agility & Adaptability': 'Agility &\nAdapt.',
  'Creativity & Innovation': 'Creativity\n& Innovation',
  'Collaboration & Teamwork': 'Collab.\n& Teamwork',
  'Self-Awareness': 'Self\nAwareness',
  'Self-Management': 'Self\nMgmt',
  'Social Awareness': 'Social\nAwareness',
  'Relationship Management': 'Relationship\nMgmt',
  'Reading/Writing': 'Reading\nWriting',
};

function formatAxisLabel(name: string) {
  if (CHART_LABEL_OVERRIDES[name]) return CHART_LABEL_OVERRIDES[name];
  if (name.length <= 14) return name;

  const words = name.split(/\s+/);
  const lines: string[] = [];
  let current = '';

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= 14) {
      current = next;
      continue;
    }
    if (current) lines.push(current);
    current = word;
  }

  if (current) lines.push(current);
  return lines.slice(0, 2).join('\n');
}

export function RadarChart({ id, keys, labels, scores, overall: storedOverall, themeMode = 'light' }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const overall = storedOverall ?? computeOverall(scores, keys);

  useEffect(() => {
    if (!ref.current) return;

    const el = ref.current;
    if (el.clientHeight === 0) el.style.height = '315px';

    const chart = echarts.init(el, undefined, {
      devicePixelRatio: Math.max(window.devicePixelRatio || 1, 2),
    });
    const values = keys.map(k => Number(scores[k]?.mean ?? 0));
    const isDark = themeMode === 'dark';
    const chartText = isDark ? '#f3f7ff' : '#33415f';
    const gridLine = isDark ? 'rgba(148,163,184,0.22)' : 'rgba(90,44,160,0.13)';
    const splitFill = isDark
      ? ['rgba(31,41,63,0.88)', 'rgba(17,24,39,0.84)']
      : ['rgba(255,255,255,0.92)', 'rgba(247,249,252,0.88)'];
    const lineColor = isDark ? '#8fb4ff' : '#172a55';
    const pointColor = isDark ? '#f4c24f' : '#5a2ca0';

    chart.setOption({
      animation: true,
      animationDuration: 950,
      animationDurationUpdate: 650,
      animationEasing: 'cubicOut',
      animationEasingUpdate: 'cubicOut',
      tooltip: {
        trigger: 'item',
        appendToBody: true,
        confine: false,
        backgroundColor: 'rgba(23,42,85,0.95)',
        borderWidth: 0,
        borderRadius: 8,
        padding: [10, 12],
        textStyle: { color: '#fff', fontSize: 12, fontWeight: 600 },
        extraCssText: 'z-index: 9999; pointer-events: none; box-shadow: 0 14px 32px rgba(15,23,42,0.24);',
        formatter: () =>
          keys.map((k, i) => {
            const s = scores[k];
            return `${labels[i]}: <b>${formatMean(s?.mean ?? 0)}</b>${s?.level ? ` (${s.level})` : ''}`;
          }).join('<br/>'),
      },
      radar: {
        center: ['50%', '50%'],
        indicator: labels.map(name => ({ name, max: 5 })),
        radius: '41%',
        splitNumber: 5,
        axisNameGap: 10,
        axisName: {
          color: chartText,
          fontSize: 12,
          fontWeight: 900,
          lineHeight: 15,
          padding: [2, 4],
          textBorderColor: isDark ? 'rgba(17,24,39,0.85)' : 'rgba(255,255,255,0.95)',
          textBorderWidth: 3,
          formatter: formatAxisLabel,
        },
        axisLine: {
          lineStyle: { color: gridLine },
        },
        splitLine: {
          lineStyle: { color: gridLine, width: 1 },
        },
        splitArea: {
          areaStyle: {
            color: splitFill,
          },
        },
      },
      series: [{
        type: 'radar',
        symbol: 'circle',
        symbolSize: 7,
        selectedMode: false,
        data: [{
          name: 'Current',
          value: values,
          lineStyle: {
            color: lineColor,
            width: 3,
            shadowBlur: 10,
            shadowColor: isDark ? 'rgba(143,180,255,0.24)' : 'rgba(23,42,85,0.22)',
          },
          itemStyle: {
            color: pointColor,
            borderColor: isDark ? '#111827' : '#ffffff',
            borderWidth: 2,
            shadowBlur: 8,
            shadowColor: 'rgba(90,44,160,0.28)',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: isDark ? 'rgba(143,180,255,0.24)' : 'rgba(23,42,85,0.24)' },
              { offset: 1, color: isDark ? 'rgba(244,194,79,0.16)' : 'rgba(90,44,160,0.14)' },
            ]),
          },
        }],
        emphasis: {
          lineStyle: { width: 4 },
          areaStyle: { opacity: 0.55 },
        },
      }],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);

    return () => { chart.dispose(); ro.disconnect(); };
  }, [id, keys, labels, scores, overall, themeMode]);

  return (
    <div className="radar-chart-shell">
      <div ref={ref} id={id} className="radar-chart-canvas" />
      {overall && (
        <div className="radar-summary">
          <span>Overall</span>
          <strong className={levelClass(overall.level)}>{overall.level.toUpperCase()}</strong>
          <em>{formatMean(overall.mean)}</em>
        </div>
      )}
    </div>
  );
}
