// ============================================================================
// Coach caseload — learner card.
//
// Reading order is the point: who, what state, how far along, the four numbers,
// then the key dates and the way in. Hierarchy comes from type size and one
// hairline rule per band rather than from a box around every group.
//
// Every value is conditional. A learner with no attendance history shows a dash,
// not a zero, because 0% attendance and "no sessions recorded yet" are different
// facts and only one of them is a problem.
// ============================================================================
import { memo } from 'react';
import { AppIcon } from '@/components/feature/AppIcon';
import {
  EMPTY_VALUE,
  clampPercent,
  displayValue,
  formatHours,
  formatHoursRatio,
  formatPercent,
  formatRatio,
  hasValue,
  learnerProgramme,
} from '../lib/format';
import type { LearnerInsight } from '../lib/attention';
import {
  DateStatus,
  Metric,
  ProgressBar,
  RiskBadge,
  SectionLabel,
  StatusPill,
} from './primitives';
import type { Learner, QuickViewTab } from '../types';

function attendanceNote(learner: Learner): { note: string | null; tone: 'muted' | 'warning' | 'critical' | 'positive' } {
  if (!learner.liveAttendanceRateAvailable) return { note: 'No sessions recorded', tone: 'muted' };
  if (learner.attendanceRisk === 'red') return { note: 'Below threshold', tone: 'critical' };
  if (learner.attendanceRisk === 'amber') return { note: 'Below expected', tone: 'warning' };
  const sessions = learner.attendanceSessions;
  return { note: sessions ? `${sessions} session${sessions === 1 ? '' : 's'}` : null, tone: 'muted' };
}

function otjhNote(insight: LearnerInsight): { note: string | null; tone: 'muted' | 'warning' | 'critical' | 'positive' } {
  const delta = insight.otjhDeltaHours;
  if (delta === null) return { note: null, tone: 'muted' };
  if (delta < -0.5) {
    return {
      note: `${formatHours(Math.abs(delta))} behind target`,
      tone: insight.tier === 'critical' ? 'critical' : 'warning',
    };
  }
  if (delta > 0.5) return { note: `${formatHours(delta)} ahead`, tone: 'positive' };
  return { note: 'On target', tone: 'positive' };
}

const AVATAR_PALETTE = [
  'bg-[#ffe5ee] text-[#7e3451] ring-[#ffd0e0]',
  'bg-[#e4efff] text-[#183582] ring-[#cfe1ff]',
  'bg-[#eee7ff] text-[#37217f] ring-[#e0d3ff]',
] as const;

function avatarClass(initials: string): string {
  const seed = Array.from(initials).reduce((total, character) => total + character.charCodeAt(0), 0);
  return AVATAR_PALETTE[seed % AVATAR_PALETTE.length];
}

export const LearnerCard = memo(function LearnerCard({
  learner,
  insight,
  selected,
  selectionMode,
  onToggleSelect,
  onQuickView,
  onOpenProfile,
}: {
  learner: Learner;
  insight: LearnerInsight;
  selected: boolean;
  selectionMode: boolean;
  onToggleSelect: (learnerId: string) => void;
  onQuickView: (learner: Learner, tab?: QuickViewTab) => void;
  onOpenProfile: (learner: Learner) => void;
}) {
  const programme = learnerProgramme(learner);
  const attendance = attendanceNote(learner);
  const otjh = otjhNote(insight);
  const otjhProgress = learner.overallProgressAvailable ? learner.overallProgress : null;
  const otjhProgrammeTarget = learner.otjhPlanned || learner.otjhMinimum || learner.otjhTarget;
  const componentsTargetProgress = learner.componentsTargetToDate && learner.componentsTargetToDate > 0
    ? clampPercent(((learner.componentsCompleted ?? 0) / learner.componentsTargetToDate) * 100)
    : null;
  const componentsTotalProgress = learner.componentsPlanned && learner.componentsPlanned > 0
    ? clampPercent(((learner.componentsCompleted ?? 0) / learner.componentsPlanned) * 100)
    : null;

  return (
    <article
      className={`group flex h-full min-h-[36rem] flex-col overflow-hidden rounded-2xl border bg-white shadow-[0_12px_32px_-22px_rgba(15,23,42,0.28)] transition duration-200 hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-[0_20px_42px_-24px_rgba(76,29,149,0.32)] ${
        selected ? 'border-primary-400 ring-2 ring-primary-200' : 'border-foreground-200/70'
      }`}
    >
      {/* Identity */}
      <div className="flex items-start gap-4 px-6 pb-7 pt-5">
        {selectionMode ? (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(learner.id)}
            aria-label={`Select ${learner.name}`}
            className="mt-5 h-4 w-4 shrink-0 rounded border-foreground-300 accent-primary-600"
          />
        ) : null}

        <button
          type="button"
          onClick={() => onQuickView(learner)}
          title={`Quick view: ${learner.name}`}
          className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-[17px] font-semibold ring-1 ring-inset transition focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 ${avatarClass(learner.initials)}`}
        >
          {learner.initials}
        </button>

        <div className="min-w-0 flex-1 pt-1">
          <div className="flex min-w-0 items-start justify-between gap-4">
            <button
              type="button"
              onClick={() => onQuickView(learner)}
              className="min-w-0 truncate text-left text-[18px] font-bold leading-6 text-foreground-950 transition hover:text-primary-700"
            >
              {learner.name}
            </button>
            <span className="shrink-0">
              <RiskBadge tier={insight.tier} label={insight.riskLabel} size="md" className="rounded-full px-3 py-1.5" />
            </span>
          </div>

          <div className="mt-2 flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1.5 text-[14px]">
            <StatusPill value={learner.rawProgramStatus} className="rounded-full px-2.5 py-1" />
            <span className="min-w-0 truncate font-medium text-foreground-700" title={programme}>{programme}</span>
            {hasValue(learner.group) ? (
              <span className="flex min-w-0 items-center gap-2 truncate text-foreground-500 before:h-1 before:w-1 before:shrink-0 before:rounded-full before:bg-foreground-300" title={displayValue(learner.group)}>
                {displayValue(learner.group)}
              </span>
            ) : null}
          </div>
          {hasValue(learner.employer) ? (
            <p className="mt-2 truncate text-[13px] text-foreground-500">
              <AppIcon className="ri-building-4-line mr-1 text-foreground-300"></AppIcon>
              {displayValue(learner.employer)}
            </p>
          ) : null}
        </div>
      </div>

      {/* Progress to current target */}
      <div className="space-y-6 px-6 pb-5">
        <div>
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <SectionLabel>OTJH target progress</SectionLabel>
            <span className="text-[14px] font-bold tabular-nums text-foreground-950">
              {otjhProgress === null ? EMPTY_VALUE : `${otjhProgress}% - ${formatHoursRatio(learner.otjhCompleted, learner.otjhTarget)}`}
            </span>
          </div>
          <ProgressBar percent={otjhProgress} height="h-2.5" />
        </div>
        <div>
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <SectionLabel>Components target progress</SectionLabel>
            <span className="text-[14px] font-bold tabular-nums text-foreground-950">
              {componentsTargetProgress === null ? EMPTY_VALUE : `${componentsTargetProgress}% - ${formatRatio(learner.componentsCompleted, learner.componentsTargetToDate)}`}
            </span>
          </div>
          <ProgressBar percent={componentsTargetProgress} height="h-2.5" />
        </div>
      </div>

      {/* Whole programme metrics */}
      <div className="grid grid-cols-2 border-t border-foreground-100 px-4 py-5 sm:grid-cols-4 sm:[&>*+*]:border-l sm:[&>*+*]:border-foreground-100">
        <Metric
          icon="ri-time-line"
          label="OTJH"
          value={learner.overallProgressAvailable ? formatHoursRatio(learner.otjhCompleted, otjhProgrammeTarget) : EMPTY_VALUE}
          note={otjh.note}
          noteTone={otjh.tone}
        />
        <Metric
          icon="ri-calendar-check-line"
          label="Attendance"
          value={formatPercent(learner.liveAttendanceRate)}
          note={attendance.note}
          noteTone={attendance.tone}
        />
        <Metric
          icon="ri-stack-line"
          label="Components"
          value={formatRatio(learner.componentsCompleted, learner.componentsPlanned)}
          note={componentsTotalProgress === null ? null : `${componentsTotalProgress}% complete`}
        />
        <Metric
          icon="ri-file-text-line"
          label="KSB"
          value={formatRatio(learner.ksbCompleted, learner.ksbTarget)}
          note={learner.ksbProgressAvailable ? displayValue(learner.ksbStatus) : null}
        />
      </div>

      {/* Footer */}
      <footer className="mt-auto border-t border-foreground-100 px-5 pb-5 pt-5">
        <div className="grid min-w-0 grid-cols-2 sm:grid-cols-3 sm:[&>*+*]:border-l sm:[&>*+*]:border-foreground-100">
          {hasValue(learner.startDate) ? (
            <div className="flex min-w-0 gap-2 px-2.5 first:pl-0">
              <AppIcon className="ri-calendar-line mt-0.5 shrink-0 text-[18px] text-foreground-500"></AppIcon>
              <DateStatus label="Start date" date={learner.startDate} daysAway={null} labelClassName="normal-case tracking-normal text-[13px] text-foreground-500" />
            </div>
          ) : null}
          {insight.gatewayDate ? (
            <div className="flex min-w-0 gap-2 px-2.5 first:pl-0">
              <AppIcon className="ri-flag-line mt-0.5 shrink-0 text-[18px] text-foreground-500"></AppIcon>
              <DateStatus label="Gateway" date={learner.gatewayReviewDate} daysAway={insight.gatewayDaysAway} labelClassName="normal-case tracking-normal text-[13px] text-foreground-500" />
            </div>
          ) : null}
          {hasValue(learner.plannedEndDate) ? (
            <div className="flex min-w-0 gap-2 px-2.5 first:pl-0">
              <AppIcon className="ri-calendar-line mt-0.5 shrink-0 text-[18px] text-foreground-500"></AppIcon>
              <DateStatus label="End date" date={learner.plannedEndDate} daysAway={null} labelClassName="normal-case tracking-normal text-[13px] text-foreground-500" />
            </div>
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => onOpenProfile(learner)}
          className="mt-5 inline-flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-primary-50 px-4 text-[14px] font-semibold text-primary-700 ring-1 ring-inset ring-primary-100 shadow-[0_10px_24px_-14px_rgba(76,29,149,0.18)] transition hover:bg-primary-600 hover:text-white hover:ring-primary-600 hover:shadow-[0_10px_24px_-14px_rgba(76,29,149,0.8)] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 focus-visible:ring-offset-2"
        >
          Open profile
          <AppIcon className="ri-arrow-right-line text-[18px]"></AppIcon>
        </button>
      </footer>
    </article>
  );
});
