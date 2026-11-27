import { afterEach, describe, expect, it } from 'vitest';
import { traceWeeklyLearning } from '../weeklyLearningDiagnostics';

afterEach(() => {
  sessionStorage.removeItem('lms:weekly-trace');
  delete window.__weeklyLearningTrace;
});

describe('temporary Weekly Learning tracing', () => {
  it('does not record CHANGE_ME unless CHANGE_MEly enabled', () => {
    traceWeeklyLearning('read', 'commercial:CHANGE_ME-learner|CHANGE_ME-module');
    expect(window.__weeklyLearningTrace).toBeUndefined();
  });

  it('correlates requests without retaining learner or module IDs in the trace', () => {
    sessionStorage.setItem('lms:weekly-trace', '1');
    const identity = 'commercial:CHANGE_ME-learner|CHANGE_ME-module';
    traceWeeklyLearning('read', identity, 'revalidate=false; fresh=false');
    traceWeeklyLearning('request-start', identity);
    traceWeeklyLearning('request-success', identity);
    const trace = window.__weeklyLearningTrace!;
    expect(trace.map(entry => entry.event)).toEqual(['read', 'request-start', 'request-success']);
    expect(new Set(trace.map(entry => entry.key)).size).toBe(1);
    expect(trace[0].stack).toContain('weeklyLearningDiagnostics.test');
    expect(JSON.stringify(trace)).not.toContain('CHANGE_ME-learner');
    expect(JSON.stringify(trace)).not.toContain('CHANGE_ME-module');
    expect(trace.every(entry => Number.isFinite(entry.at) && Number.isFinite(entry.elapsed))).toBe(true);
  });
});
