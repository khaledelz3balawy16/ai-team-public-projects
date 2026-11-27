import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import type { LearnerKind } from '@/api/learnerDetail';
import { fetchEvidence, getEvidenceDownloadUrl, type EvidenceRecord } from '@/api/evidence';
import { WorkspaceShell } from '@/components/feature/WorkspaceShell';
import { useCoachIdentity } from '@/hooks/useCoachIdentity';
import { coachFetch } from '@/lib/coachFetch';
import { roleNavMap } from '@/mocks/navigation';
import styles from './markingReview.module.css';

import { AssignmentAttemptHistory } from '@/components/feature/AssignmentAttemptHistory';
import type { SubmissionAttempt } from '@/api/assignmentAttempts';
import { fetchMarkingDetail, fetchMarkingSidebarQueue } from '@/features/coach/marking/api/markingApi';
import type { MonthlySections } from '@/features/coach/marking/types/marking.types';
import { readExtraActivities } from '../extra-activities/api';
import { loadLearningReflectionSubmission, type StoredLearningReflectionSubmission } from '@/api/reflectionSubmission';
import { CoachPresentationDownload } from './CoachPresentationDownload';
import { KsbReviewPanel, type KsbReview } from './KsbReviewPanel';
import { SavedReflection } from '@/components/feature/SavedReflection';
import { CoachFeedbackEditor } from '@/components/feature/CoachFeedbackEditor';
import { FormattedFeedback } from '@/components/feature/FormattedFeedback';
import { feedbackHtmlToPlainText } from '@/lib/feedbackHtml';
import { MarkingInstructionsPanel } from './MarkingInstructionsPanel';
import { MarkingPartSections } from './MarkingPartSections';

const coachNav = roleNavMap.coach;
async function personalEvidence(submissionId: string, fileId?: string) {
  const response = await coachFetch(`/coach_api/coach/personal-marking/${submissionId}/evidence${fileId ? `/${fileId}` : ''}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Could not load personal coursework evidence.');
  return data as { results: EvidenceRecord[]; url: string };
}

interface Submission {
  /** Present for a monthly (nine-step) assignment report: the content of the two review tabs. */
  monthlySections?: MonthlySections;
  ksbReview?: KsbReview;
  submissionAttempts?: SubmissionAttempt[];
  version?: number;
  contentSections?: { label: string; text: string }[];
  reviewHistory?: { decision: string; feedback: string; reviewedAt: string; reviewedBy: string }[];
  id: string;
  learnerKind: LearnerKind;
  learnerId: string;
  learner: string;
  initials: string;
  programme: string;
  activityType: string;
  activityId: string;
  activityTitle: string;
  module: string;
  week: string;
  plannedOtjh: string;
  status: string;
  learningReflection: string;
  ksbCodes: string[];
  ksbWeights: Record<string, number>;
  ksbExplanations: Record<string, string>;
  applicationType: string;
  applicationText: string;
  evidenceConsentConfirmed: boolean;
  CHANGE_MEBenefits: string[];
  benefitExplanation: string;
  actualTimeHours: string;
  completedDuringPaidHours: string;
  dateCompleted: string | null;
  otjhConfirmed: boolean;
  signedDeclaration: boolean;
  qualityScore: number;
  coachFeedback: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  submittedAt: string | null;
  submittedDisplay: string;
  elapsedDays: number;
  isOverdue: boolean;
}

interface QueueSummary {
  pendingItems: number;
  overdueItems: number;
  acceptedItems: number;
  referredItems: number;
}

type ReviewDecision = 'accepted' | 'rejected' | 'referred';
type WorkspaceTab = 'submission' | 'evidence' | 'history';
/** A monthly report: steps 2-4, steps 5-8, then one feedback and decision for the whole report. */
type MonthlyTab = 'assignment' | 'reflection' | 'feedback';
const MONTHLY_TABS: Array<[MonthlyTab, string, string]> = [
  ['assignment', 'Assignment, KSBs & evidence', 'Steps 2–4'],
  ['reflection', 'Reflection', 'Steps 5–8'],
  ['feedback', 'Feedback', 'Whole report'],
];

function statusLabel(status: string) {
  if (status === 'ksb_review') return 'KSB review required';
  if (status === 'accepted') return 'Accepted';
  if (status === 'partial') return 'Partially awarded';
  if (status === 'referred' || status === 'rejected') return 'Referred back';
  if (status === 'escalated') return 'Escalated';
  return 'Pending review';
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fileSize(bytes: number) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isAssignment(item: Submission) {
  return ['assignment', 'extra_activity'].includes((item.activityType || '').toLowerCase());
}

function kindLabel(item: Submission) {
  return item.activityType === 'extra_activity' ? 'Extra activity' : isAssignment(item) ? 'Assignment' : 'Reflection';
}

export default function CoachMarkingReviewPage() {
  const [searchParams] = useSearchParams();
  const extraActivities = useLocation().pathname.startsWith('/coach/extra-activities');
  const personal = searchParams.get('scope') === 'personal';
  const apiEndpoint = personal ? '/coach_api/coach/personal-marking' : '/coach_api/coach/marking-queue';
  const scopeQuery = personal ? '?scope=personal' : '';
  const queuePath = extraActivities ? '/coach/extra-activities' : `/coach/marking-queue${scopeQuery}`;
  const { submissionId } = useParams<{ submissionId: string }>();
  const navigate = useNavigate();
  const coach = useCoachIdentity();
  const [CHANGE_ME, setSelected] = useState<Submission | null>(null);
  const [extraDocument, setExtraDocument] = useState<StoredLearningReflectionSubmission | null>(null);
  const [extraDocumentError, setExtraDocumentError] = useState('');
  const [queueItems, setQueueItems] = useState<Submission[]>([]);
  const [queueSummary, setQueueSummary] = useState<QueueSummary>({ pendingItems: 0, overdueItems: 0, acceptedItems: 0, referredItems: 0 });
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [aiNotice, setAiNotice] = useState('');
  const [error, setError] = useState('');
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [evidenceError, setEvidenceError] = useState('');
  const [downloading, setDownloading] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [defaultPrompt, setDefaultPrompt] = useState('');
  const [promptFile, setPromptFile] = useState('');
  const [promptKind, setPromptKind] = useState('');
  const [promptAvailable, setPromptAvailable] = useState(true);
  const [promptError, setPromptError] = useState('');
  const [promptUpload, setPromptUpload] = useState<File | null>(null);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<WorkspaceTab>('submission');
  const [monthlyTab, setMonthlyTab] = useState<MonthlyTab>('assignment');

  const loadSequence = useRef(0);
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    if (!coach.isInitialized) return;
    setLoading(true);
    setError('');
    if (!coach.email) {
      setSelected(null);
      setError('Coach access is required to load submissions.');
      setLoading(false);
      return;
    }

    try {
      const detailItem = await fetchMarkingDetail<Submission>(personal ? 'personal' : 'official', submissionId || '');
      if (sequence !== loadSequence.current) return;
      if (extraActivities && detailItem?.activityType !== 'extra_activity') throw new Error('Extra activity not found.');
      // Initialise together: a later effect could overwrite the coach's first edit.
      setFeedback(detailItem?.coachFeedback ?? '');
      setPromptUpload(null);
      setSelected(detailItem);
      setMonthlyTab('assignment');

      try {
        const queueData = extraActivities ? await readExtraActivities(new URLSearchParams({ status: 'all', page: '1' })).then(data => ({
          items: data.items.map(row => ({ ...row, activityType: 'extra_activity', activityTitle: row.title, actualTimeHours: row.hours, submittedDisplay: row.month }) as unknown as Submission), summary: {},
        })) : await fetchMarkingSidebarQueue<Submission>(personal ? 'personal' : 'official');
        if (sequence !== loadSequence.current) return;
        setQueueItems(queueData.items || []);
        setQueueSummary({ pendingItems: 0, overdueItems: 0, acceptedItems: 0, referredItems: 0, ...queueData.summary });
      } catch {
        setQueueItems([]);
      }
    } catch (loadError) {
      if (sequence !== loadSequence.current) return;
      setSelected(null);
      setError(loadError instanceof Error ? loadError.message : 'Unable to load this submission.');
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [coach.email, coach.isInitialized, submissionId, personal, extraActivities]);

  useEffect(() => {
    let active = true;
    setExtraDocument(null); setExtraDocumentError('');
    if (!CHANGE_ME || CHANGE_ME.activityType !== 'extra_activity' || personal) return;
    void loadLearningReflectionSubmission({ learnerKind: CHANGE_ME.learnerKind, learnerId: CHANGE_ME.learnerId, activityType: 'extra_activity', activityId: CHANGE_ME.activityId }, { revalidate: true })
      .then(value => { if (active) setExtraDocument(value); })
      .catch(() => { if (active) setExtraDocumentError('Could not load the full activity. Reload before reviewing.'); });
    return () => { active = false; };
  }, [CHANGE_ME, personal]);

  useEffect(() => {
    const counter = loadSequence;
    void load();
    return () => { ++counter.current; };
  }, [load]);

  useEffect(() => {
    if (!CHANGE_ME) return;
    let cancelled = false;
    setEvidence([]);
    setEvidenceError('');
    (personal ? personalEvidence(CHANGE_ME.id).then(data => data.results) : fetchEvidence(CHANGE_ME.learnerKind, CHANGE_ME.learnerId, { sectionRef: CHANGE_ME.activityId }))
      .then(records => { if (!cancelled) setEvidence(records); })
      .catch(loadError => {
        if (!cancelled) setEvidenceError(loadError instanceof Error ? loadError.message : 'The uploaded files could not be listed.');
      });
    return () => { cancelled = true; };
  }, [personal, CHANGE_ME]);

  useEffect(() => {
    if (!CHANGE_ME || personal) return;
    let cancelled = false;
    setPromptError('');
    coachFetch(`${apiEndpoint}/${CHANGE_ME.id}/ai-prompt`)
      .then(async response => {
        const body = await response.text();
        let data: { prompt?: string; file?: string; kind?: string; available?: boolean; detail?: string; error?: string } = {};
        try { data = body ? JSON.parse(body) : {}; } catch { throw new Error(`The marking prompt could not be loaded (server error ${response.status}).`); }
        if (!response.ok) throw new Error(data.error || data.detail || 'The marking prompt could not be loaded.');
        if (cancelled) return;
        setDefaultPrompt(data.prompt || '');
        setPrompt(data.prompt || '');
        setPromptFile(data.file || '');
        setPromptKind(data.kind || '');
        setPromptAvailable(data.available !== false);
      })
      .catch(loadError => {
        if (!cancelled) setPromptError(loadError instanceof Error ? loadError.message : 'The marking prompt could not be loaded.');
      });
    return () => { cancelled = true; };
  }, [apiEndpoint, personal, CHANGE_ME]);

  const promptEdited = Boolean(prompt.trim()) && prompt.trim() !== defaultPrompt.trim();
  const promptCleared = !prompt.trim() && Boolean(defaultPrompt.trim());

  const visibleQueue = useMemo(() => {
    const currentItems = CHANGE_ME && !queueItems.some(item => item.id === CHANGE_ME.id)
      ? [CHANGE_ME, ...queueItems]
      : queueItems;
    const term = search.trim().toLowerCase();
    return currentItems.filter(item => {
      const searchMatches = !term || [item.learner, item.programme, item.activityTitle, item.module]
        .some(value => value?.toLowerCase().includes(term));
      return searchMatches;
    });
  }, [queueItems, search, CHANGE_ME]);

  const markedToday = useMemo(() => {
    const today = new Date().toDateString();
    return queueItems.filter(item => item.reviewedAt && new Date(item.reviewedAt).toDateString() === today).length;
  }, [queueItems]);

  const openEvidence = async (record: EvidenceRecord) => {
    if (!CHANGE_ME || downloading) return;
    const tabWindow = window.open('', '_blank');
    if (tabWindow) tabWindow.opener = null;
    setDownloading(record.id);
    setEvidenceError('');
    try {
      const url = personal ? (await personalEvidence(CHANGE_ME.id, record.id)).url : await getEvidenceDownloadUrl(CHANGE_ME.learnerKind, CHANGE_ME.learnerId, record.id);
      if (tabWindow) tabWindow.location.href = url;
      else setEvidenceError('Allow pop-ups for this site to open the document.');
    } catch (downloadError) {
      tabWindow?.close();
      setEvidenceError(downloadError instanceof Error ? downloadError.message : 'The document could not be opened.');
    } finally {
      setDownloading(null);
    }
  };

  const generateAiFeedback = async () => {
    if (!CHANGE_ME || generating) return;
    setGenerating(true);
    setError('');
    setAiNotice('');
    try {
      const request: RequestInit = { method: 'POST' };
      if (promptEdited || promptUpload) {
        const form = new FormData();
        if (promptEdited && prompt.trim()) form.append('prompt', prompt.trim());
        if (promptUpload) form.append('promptFile', promptUpload, promptUpload.name);
        request.body = form;
      }
      const response = await coachFetch(`${apiEndpoint}/${CHANGE_ME.id}/ai-feedback`, request);
      const text = await response.text();
      let data: { feedback?: string; error?: string; detail?: string; meta?: { ksbCount?: number; epaFile?: string; promptSource?: string; promptFile?: string; evidenceFiles?: { filename: string; readable: boolean }[] } } = {};
      try { data = text ? JSON.parse(text) : {}; } catch { throw new Error(`The draft could not be generated (server error ${response.status}).`); }
      if (!response.ok) throw new Error(data.error || data.detail || 'The draft could not be generated.');
      setFeedback(data.feedback || '');
      const ksbCount = data.meta?.ksbCount ?? 0;
      const promptNote = data.meta?.promptSource === 'custom-file'
        ? ` using ${data.meta?.promptFile || 'your uploaded guidance'}`
        : data.meta?.promptSource === 'custom' ? ' from your edited prompt' : '';
      const files = data.meta?.evidenceFiles ?? [];
      const unreadable = files.filter(file => !file.readable);
      const fileNote = files.length ? ` Readable text extracted from ${files.length - unreadable.length} of ${files.length} uploaded files.` : '';
      const unreadableNote = unreadable.length ? ` Could not read: ${unreadable.map(file => file.filename || 'Unnamed file').join(', ')}. Review these files separately.` : '';
      setAiNotice(`AI-assisted draft generated${promptNote}${ksbCount ? ` against ${ksbCount} assigned KSB${ksbCount === 1 ? '' : 's'}` : ''}.${fileNote}${unreadableNote} Review and edit it before deciding.`);
    } catch (aiError) {
      setError(aiError instanceof Error ? aiError.message : 'The draft could not be generated.');
    } finally {
      setGenerating(false);
    }
  };

  const saveDecision = async (decision: ReviewDecision) => {
    if (!CHANGE_ME || saving || (CHANGE_ME.activityType === 'extra_activity' && (!extraDocument || extraDocumentError))) return;
    if (!feedbackHtmlToPlainText(feedback)) {
      setError('Write feedback for the learner before sending this decision.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = await coachFetch(`${apiEndpoint}/${CHANGE_ME.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, feedback: feedback.trim(), reviewedBy: coach.name, ...(personal ? { version: CHANGE_ME.version } : {}) }),
      });
      const text = await response.text();
      let data: { detail?: string; error?: string; fields?: Record<string, string[] | string> } = {};
      try { data = text ? JSON.parse(text) : {}; } catch { throw new Error(`The review could not be saved (server error ${response.status}).`); }
      if (!response.ok) {
        const fieldMessages = Object.entries(data.fields ?? {}).map(([field, message]) => `${field}: ${Array.isArray(message) ? message.join(' ') : message}`).join('; ');
        throw new Error(fieldMessages || data.detail || data.error || 'The review could not be saved.');
      }
      navigate(queuePath);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'The review could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const uploadedEvidence = CHANGE_ME ? (
    <>
    <div className={styles.sectionHeading}><div><h4>Uploaded evidence</h4><p>Documents attached to this activity.</p></div><span>{evidence.length} files</span></div>
    {evidence.length ? (
      <ul className={styles.evidenceList}>
        {evidence.map(record => {
          const approved = record.status === 'approved';
          return (
            <li key={record.id}>
              <i className="ri-file-text-line" aria-hidden="true" />
              <div><strong>{record.filename}</strong><span>{[record.contentType, fileSize(record.sizeBytes)].filter(Boolean).join(' · ')}</span></div>
              {approved ? <button type="button" disabled={downloading === record.id} onClick={() => void openEvidence(record)}>{downloading === record.id ? 'Opening…' : 'Open file'}</button> : <em>{record.status === 'rejected' ? 'Failed scan' : 'Awaiting scan'}</em>}
            </li>
          );
        })}
      </ul>
    ) : <p className={styles.emptyText}>{evidenceError || 'No document was uploaded with this submission.'}</p>}
    {evidenceError && evidence.length > 0 && <p className={styles.inlineError}>{evidenceError}</p>}
    </>
  ) : null;

  const declarationGrid = CHANGE_ME ? (
    <div className={styles.declarationGrid}>
      <span>Completed: <strong>{formatDate(CHANGE_ME.dateCompleted)}</strong></span>
      <span>Paid hours: <strong>{CHANGE_ME.completedDuringPaidHours || '—'}</strong></span>
      <span>OTJH confirmed: <strong>{CHANGE_ME.otjhConfirmed ? 'Yes' : 'No'}</strong></span>
      <span>Declaration signed: <strong>{CHANGE_ME.signedDeclaration ? 'Yes' : 'No'}</strong></span>
    </div>
  ) : null;

  const presentationDownload = CHANGE_ME?.activityType === 'assignment' ? (
    <CoachPresentationDownload
      key={`${coach.email}:${personal}:${CHANGE_ME.id}:${CHANGE_ME.version ?? CHANGE_ME.submittedAt ?? ''}`}
      scope={personal ? 'personal' : 'official'} submissionId={CHANGE_ME.id}
      submittedAt={CHANGE_ME.submittedAt} version={CHANGE_ME.version}
    />
  ) : null;

  const ksbReviewPanel = CHANGE_ME?.ksbReview ? (
    <KsbReviewPanel key={`${CHANGE_ME.id}:${CHANGE_ME.ksbReview.revision}:${CHANGE_ME.ksbReview.status}`}
      submissionId={CHANGE_ME.id} review={CHANGE_ME.ksbReview} onSaved={() => void load()} />
  ) : null;

  // A monthly report shows this in its Feedback tab; everything else shows it below the submission.
  const feedbackPanel = CHANGE_ME && CHANGE_ME.ksbReview?.status !== 'pending' ? (
      <section className={styles.feedbackPanel}>
        <div className={styles.feedbackHeading}>
          <div><p>Coach feedback</p><h4>Review the AI draft and make the final decision</h4></div>
          {!personal && <div className={styles.feedbackActions}>
            <button type="button" disabled={generating || saving} onClick={() => void generateAiFeedback()}>
              <i className={generating ? 'ri-loader-4-line' : 'ri-sparkling-line'} aria-hidden="true" />
              {generating ? 'Generating…' : 'Generate AI draft'}
            </button>
          </div>}
        </div>
        <CoachFeedbackEditor value={feedback} onChange={setFeedback} disabled={saving} />
        {aiNotice && <p className={styles.aiNotice}><i className="ri-sparkling-line" aria-hidden="true" /> {aiNotice}</p>}
        {error && <p className={styles.inlineError}>{error}</p>}
  
        {!personal && <MarkingInstructionsPanel key={CHANGE_ME.id} edited={promptEdited} guidanceAttached={Boolean(promptUpload)}>
          <p>{promptAvailable ? `These ${promptKind === 'assignment' ? 'assignment marking' : 'reflection validation'} instructions apply to the next draft only.` : 'No saved prompt is available. You can supply instructions for this draft.'}</p>
          <textarea aria-label="AI marking instructions" value={prompt} onChange={event => setPrompt(event.target.value)} rows={8} spellCheck={false} placeholder="Write the instructions the AI should mark against…" />
          <label className={styles.promptUpload}>
            <span><i className="ri-attachment-2" aria-hidden="true" /> Upload marking guidance</span>
            <input aria-label="Upload marking guidance" type="file" accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown" onChange={event => {
              setPromptUpload(event.target.files?.[0] || null);
              setPromptError('');
              event.currentTarget.value = '';
            }} />
            <small>PDF or Word (.docx), up to 5 MB. Used for this draft only.</small>
          </label>
          {promptUpload && <div className={styles.promptFile}><i className="ri-file-text-line" aria-hidden="true" /><span>{promptUpload.name} · used for this draft</span><button type="button" onClick={() => setPromptUpload(null)}>Remove</button></div>}
          <div className={styles.promptMeta}>
            <span>{promptFile || 'No prompt file'} · {prompt.length.toLocaleString()} characters</span>
            <button type="button" disabled={!defaultPrompt || prompt === defaultPrompt} onClick={() => setPrompt(defaultPrompt)}>Reset to default</button>
          </div>
          {promptCleared && <p>The saved prompt will be used because this field is empty.</p>}
          {promptError && <p className={styles.inlineError}>{promptError}</p>}
        </MarkingInstructionsPanel>}
  
        {CHANGE_ME.monthlySections && <p className={styles.aiNotice}><i className="ri-information-line" aria-hidden="true" /> This feedback and decision cover the whole monthly report: the assignment, KSBs &amp; evidence (steps 2–4) and the reflection (steps 5–8). The AI draft is written from both.</p>}
        <div className={styles.decisionRow}>
          <button type="button" className={styles.reject} disabled={saving || (CHANGE_ME.activityType === 'extra_activity' && !extraDocument)} onClick={() => void saveDecision(personal ? 'referred' : 'rejected')}><i className="ri-arrow-go-back-line" aria-hidden="true" /> {personal ? 'Return for improvement' : 'Refer back with feedback'}</button>
          <button type="button" className={styles.accept} disabled={saving || (CHANGE_ME.activityType === 'extra_activity' && !extraDocument)} onClick={() => void saveDecision('accepted')}><i className={saving ? 'ri-loader-4-line' : 'ri-shield-check-line'} aria-hidden="true" /> {CHANGE_ME.activityType === 'extra_activity' ? 'Accept extra activity and send feedback' : 'Accept assignment and send feedback'}</button>
        </div>
      </section>
  ) : null;

  return (
    <WorkspaceShell role="coach" roleLabel={coachNav.label} navItems={coachNav.items} workspaceLabel={coachNav.workspaceLabel} pageTitle="Marking workspace" pageSubtitle="Review evidence and record your professional judgement" userName={coach.name} userRole="Progress Coach">
      <div className={styles.page}>
        <header className={styles.hero}>
          <button type="button" className={styles.back} onClick={() => navigate(queuePath)}>
            <i className="ri-arrow-left-line" aria-hidden="true" /> {extraActivities ? 'Extra activities' : 'Marking queue'}
          </button>
          <p className={styles.eyebrow}>AI-assisted marking</p>
          <div className={styles.heroRow}>
            <div>
              <h1>{extraActivities ? 'Extra activity review' : 'Monthly marking workspace'}</h1>
              <p>AI drafts are clearly labelled and require your validation. Final professional judgement is yours.</p>
            </div>
            <span className={styles.judgement}><i className="ri-shield-check-line" aria-hidden="true" /> Coach judgement final</span>
          </div>
        </header>

        {loading ? (
          <div className={styles.loading}><span /><span /><span /></div>
        ) : !CHANGE_ME ? (
          <div className={styles.errorState} role="alert">
            <i className="ri-file-search-line" aria-hidden="true" />
            <h2>Unable to open this submission</h2>
            <p>{error || 'The submission was not found.'}</p>
            <button type="button" onClick={() => void load()}>Try again</button>
          </div>
        ) : (
          <div className={styles.workspace}>
            <aside className={styles.queuePanel} aria-label={extraActivities ? 'Extra activities queue' : 'Marking queue'}>
              {!extraActivities && <div className={styles.stats}>
                <div><i className="ri-time-line" aria-hidden="true" /><span>Due</span><strong>{queueSummary.pendingItems}</strong></div>
                <div><i className="ri-error-warning-line" aria-hidden="true" /><span>Overdue</span><strong>{queueSummary.overdueItems}</strong></div>
                <div><i className="ri-checkbox-circle-line" aria-hidden="true" /><span>Marked today</span><strong>{markedToday}</strong></div>
              </div>}
              <label data-search-field className={styles.search}>
                <i className="ri-search-line" aria-hidden="true" />
                <span className="sr-only">Search marking queue</span>
                <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search learner or activity" />
              </label>
              <div className={styles.queueList}>
                {visibleQueue.map(item => (
                  <button type="button" key={item.id} className={styles.queueItem} aria-current={item.id === CHANGE_ME.id ? 'true' : undefined} onClick={() => navigate(extraActivities ? `/coach/extra-activities/${item.id}` : `/coach/marking-queue/${item.id}`)}>
                    <span className={styles.queueItemTop}><strong>{item.learner}</strong><em>{kindLabel(item)}</em></span>
                    <span className={styles.queueTitle}>{item.activityTitle}</span>
                    <span className={styles.queueMeta}>Submitted {item.submittedDisplay}</span>
                    <span className={styles.queueStatus} data-overdue={item.isOverdue || undefined}>{item.isOverdue ? `Overdue ${item.elapsedDays}d` : statusLabel(item.status)}</span>
                  </button>
                ))}
                {visibleQueue.length === 0 && <p className={styles.noQueueItems}>No submissions match this filter.</p>}
              </div>
            </aside>

            <main className={styles.reviewPanel}>
              <section className={styles.submissionHeader}>
                <div className={styles.personRow}>
                  <div><h2>{CHANGE_ME.learner}</h2><p>{CHANGE_ME.programme || 'Learner programme'}</p></div>
                  <span>{kindLabel(CHANGE_ME)}</span>
                </div>
                <h3>{CHANGE_ME.activityTitle}</h3>
                <dl className={styles.metrics}>
                  <div><dt>Submitted</dt><dd>{CHANGE_ME.submittedDisplay}</dd></div>
                  <div><dt>Status</dt><dd>{statusLabel(CHANGE_ME.status)}</dd></div>
                  <div><dt>Hours</dt><dd>{CHANGE_ME.actualTimeHours || '—'} recorded / {CHANGE_ME.plannedOtjh || '—'} planned</dd></div>
                  <div><dt>Claimed KSBs</dt><dd>{CHANGE_ME.ksbReview?.status === 'pending' ? 'Awaiting programme KSB review' : CHANGE_ME.ksbCodes.join(', ') || 'None claimed'}</dd></div>
                </dl>
              </section>

              <AssignmentAttemptHistory attempts={CHANGE_ME.submissionAttempts || []} />
              {!personal && ['session', 'recording', 'video'].includes(CHANGE_ME.activityType) && <SavedReflection
                timeOnly learnerKind={CHANGE_ME.learnerKind} learnerId={CHANGE_ME.learnerId}
                activityType={CHANGE_ME.activityType} activityId={CHANGE_ME.activityId} />}
              {CHANGE_ME.activityType === 'assignment' && !CHANGE_ME.monthlySections && presentationDownload}
              {CHANGE_ME.activityType === 'extra_activity' && <section className={styles.responseBlock}>
                <strong>Extra activity</strong>
                {extraDocumentError && <p role="alert">{extraDocumentError}</p>}
                {extraDocument?.coachCreation && <p>Added and originally approved by: {extraDocument.coachCreation.name}</p>}
                {extraDocument && <><strong>Activity description</strong><p className="whitespace-pre-wrap">{extraDocument.assignmentAnswer}</p><strong>What the learner learned</strong><p className="whitespace-pre-wrap">{extraDocument.whatYouLearned}</p></>}
              </section>}

              {CHANGE_ME.monthlySections ? <>
              <div className={`${styles.tabs} ${styles.monthlyTabs}`} role="tablist" aria-label="Monthly report">
                {MONTHLY_TABS.map(([value, label, steps]) => (
                  <button type="button" role="tab" id={`monthly-tab-${value}`} aria-controls={`monthly-panel-${value}`} aria-CHANGE_ME={monthlyTab === value} key={value} onClick={() => setMonthlyTab(value)}>
                    <span>{label}</span><small>{steps}</small>
                  </button>
                ))}
              </div>
              {monthlyTab === 'assignment' && (
                <section className={styles.tabPanel} role="tabpanel" id="monthly-panel-assignment" aria-labelledby="monthly-tab-assignment">
                  <MarkingPartSections key={`${CHANGE_ME.id}:assignment`} label="Assignment, KSBs & evidence steps" sections={CHANGE_ME.monthlySections.assignment}
                    extras={{ 3: uploadedEvidence, 4: declarationGrid }} />
                </section>
              )}
              {monthlyTab === 'reflection' && (
                <section className={styles.tabPanel} role="tabpanel" id="monthly-panel-reflection" aria-labelledby="monthly-tab-reflection">
                  <MarkingPartSections key={`${CHANGE_ME.id}:reflection`} label="Reflection steps" sections={CHANGE_ME.monthlySections.reflection}
                    extras={{ 8: presentationDownload }} />
                </section>
              )}
              {monthlyTab === 'feedback' && (
                <section className={styles.tabPanel} role="tabpanel" id="monthly-panel-feedback" aria-labelledby="monthly-tab-feedback">
                  {ksbReviewPanel}
                  {feedbackPanel}
                </section>
              )}
              </> : <>
              <div className={styles.tabs} role="tablist" aria-label="Submission detail">
                {([
                  ['submission', 'Submission'],
                  ['evidence', 'Evidence & KSBs'],
                  ['history', 'Progress history'],
                ] as Array<[WorkspaceTab, string]>).map(([value, label]) => (
                  <button type="button" role="tab" aria-CHANGE_ME={tab === value} key={value} onClick={() => setTab(value)}>{label}</button>
                ))}
              </div>

              {tab === 'submission' && (
                <section className={styles.tabPanel} role="tabpanel">
                  {personal && CHANGE_ME.contentSections?.map((section, index) => (
                    <div className={styles.responseBlock} key={`${section.label}-${index}`}>
                      <strong>{section.label}</strong><p>{section.text}</p>
                    </div>
                  ))}
                  <div className={styles.questionBlock}>
                    <span>Learner submission</span>
                    <p>{[CHANGE_ME.module, CHANGE_ME.week].filter(Boolean).join(' · ') || CHANGE_ME.activityTitle}</p>
                  </div>
                  <article className={styles.answerBlock}>
                    <header><strong>Learning reflection</strong><span>{(CHANGE_ME.learningReflection || '').trim().split(/\s+/).filter(Boolean).length} words</span></header>
                    <p>{CHANGE_ME.learningReflection || 'No learning reflection was supplied.'}</p>
                  </article>
                  <article className={styles.answerBlock}>
                    <header><strong>Workplace application</strong></header>
                    <p>{[CHANGE_ME.applicationType, CHANGE_ME.applicationText].filter(Boolean).join(' — ') || 'No workplace application was supplied.'}</p>
                  </article>
                  <article className={styles.answerBlock}>
                    <header><strong>Employer and business impact</strong></header>
                    <p>{[CHANGE_ME.CHANGE_MEBenefits.join(', '), CHANGE_ME.benefitExplanation].filter(Boolean).join(' — ') || 'No employer benefit was supplied.'}</p>
                  </article>
                  {declarationGrid}
                </section>
              )}

              {tab === 'evidence' && (
                <section className={styles.tabPanel} role="tabpanel">
                  {uploadedEvidence}

                  <div className={styles.sectionHeading}><div><h4>{CHANGE_ME.ksbReview?.status === 'pending' ? 'Original learner KSB claims — awaiting review' : 'Claimed KSBs'}</h4><p>Knowledge, skills and behaviours recorded for this activity.</p></div></div>
                  <div className={styles.ksbList}>
                    {CHANGE_ME.ksbCodes.length ? CHANGE_ME.ksbCodes.map(code => (
                      <article key={code}><span>{code}</span><div><strong>{CHANGE_ME.ksbExplanations[code] || 'No explanation supplied.'}</strong>{CHANGE_ME.ksbWeights[code] != null && <small>Weight {CHANGE_ME.ksbWeights[code]}</small>}</div></article>
                    )) : <p className={styles.emptyText}>No KSBs are assigned to this activity.</p>}
                  </div>
                </section>
              )}

              {tab === 'history' && (
                <section className={styles.tabPanel} role="tabpanel">
                  <div className={styles.historyCard}>
                    <i className={CHANGE_ME.reviewedAt ? 'ri-checkbox-circle-line' : 'ri-time-line'} aria-hidden="true" />
                    <div><h4>{CHANGE_ME.reviewedAt ? statusLabel(CHANGE_ME.status) : 'Awaiting coach review'}</h4><p>{CHANGE_ME.reviewedAt ? `${formatDate(CHANGE_ME.reviewedAt)} · ${CHANGE_ME.reviewedBy || 'Coach'}` : `Submitted ${CHANGE_ME.submittedDisplay}`}</p></div>
                  </div>
                  {CHANGE_ME.coachFeedback && <div className={styles.previousFeedback}><strong>Recorded coach feedback</strong><FormattedFeedback value={CHANGE_ME.coachFeedback} className={styles.previousFeedbackText} /></div>}
                  {personal && CHANGE_ME.reviewHistory?.map((entry, index) => (
                    <div className={styles.previousFeedback} key={`${entry.reviewedAt}-${index}`}>
                      <strong>{statusLabel(entry.decision)} · {entry.reviewedBy}</strong>
                      <p>{formatDate(entry.reviewedAt)} · </p><FormattedFeedback value={entry.feedback} className={styles.previousFeedbackText} />
                    </div>
                  ))}
                </section>
              )}

              {ksbReviewPanel}
              {feedbackPanel}
              </>}
            </main>
          </div>
        )}
      </div>
    </WorkspaceShell>
  );
}
