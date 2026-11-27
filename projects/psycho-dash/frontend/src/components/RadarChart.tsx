/**
 * Thin wrapper around ECharts radar chart.
 * Props-driven, no global state.
 */
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { ScoreItem } from '../types/assessment';

interface Props {
  id:     string;
  keys:   string[];
  labels: string[];
  scores: Record<string, ScoreItem>;
  overall?: ScoreItem | null;
}

function formatMean(m: number) { return m.toFixed(1); }

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

export function RadarChart({ id, keys, labels, scores, overall: storedOverall }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const el = ref.current;
    if (el.clientHeight === 0) el.style.height = '260px';

    const chart = echarts.init(el);
    const values = keys.map(k => Number(scores[k]?.mean ?? 0));
    const overall = storedOverall ?? computeOverall(scores, keys);

    chart.setOption({
      title: overall
        ? {
            text: `Overall: ${formatMean(overall.mean)} (${overall.level})`,
            left: 'center', top: 'bottom',
            textStyle: { fontSize: 12, color: '#6b7280' },
          }
        : undefined,
      tooltip: {
        trigger: 'item',
        formatter: () =>
          keys.map((k, i) => {
            const s = scores[k];
            return `${labels[i]}: ${formatMean(s?.mean ?? 0)}${s?.level ? ` (${s.level})` : ''}`;
          }).join('<br/>'),
      },
      radar: {
        indicator: labels.map(name => ({ name, max: 5 })),
        radius: 80,
        splitArea: { areaStyle: { color: ['#f8fafc'] } },
      },
      series: [{
        type: 'radar',
        symbol: 'circle',
        symbolSize: 6,
        data: [{
          name: 'Current',
          value: values,
          lineStyle: { color: '#4f2d7f', width: 2 },
          itemStyle: { color: '#4f2d7f' },
          areaStyle: { color: 'rgba(79,45,127,0.2)' },
        }],
      }],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);

    return () => { chart.dispose(); ro.disconnect(); };
  }, [id, keys, labels, scores, storedOverall]);

  return <div ref={ref} id={id} style={{ height: 260, width: '100%' }} />;
}
