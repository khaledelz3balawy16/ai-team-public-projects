import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";

const performanceDomains = ["Governance", "Scope", "Schedule", "Finance", "Stakeholders", "Resources", "Risk"];
const questionTypes = ["Single Response", "Multiple Response", "Case Study", "Graphic", "Case Study Graphic"];
const methodologies = ["Agile", "Hybrid", "Predictive", "Waterfall", "General"];
const practiceMethodologies = ["Agile", "Hybrid", "Predictive", "General"];
const difficulties = ["Medium"];
const practiceExamModes = ["practice_1", "practice_2", "practice_3", "practice_4", "practice_5"];
const aiReportRequests = new Map();
function generateReportOnce(attemptId, force=false) {
  const key = `${attemptId}:${force ? "force" : "normal"}`;
  if (!aiReportRequests.has(key)) aiReportRequests.set(key, api.generateReport(attemptId, force ? {force:true} : {}).finally(()=>aiReportRequests.delete(key)));
  return aiReportRequests.get(key);
}
function Layout({ children, admin=false }) {
  const location = useLocation();
  const path = location.pathname;
  const pageKey = admin ? "admin" : path.includes("/exam/") || path.includes("/practice") ? "practice" : path.includes("/result/") || path.includes("/history") ? "results" : path.includes("/profile") ? "profile" : path.includes("/dashboard") ? "dashboard" : "auth";
  const pageLabel = admin ? "Admin" : path.includes("/exam/") ? "In exam" : path.includes("/practice") ? "Practice" : path.includes("/result/") ? "Result report" : path.includes("/history") ? "Results" : path.includes("/profile") ? "Profile" : path.includes("/dashboard") ? "Dashboard" : "Sign in";
  const active = (key)=> key === "results" ? (path.includes("/result/") || path.includes("/history")) : path.includes(`/pmp-assessment/${key}`);
  const adminActive = (key)=>path.includes(`/admin/${key}`);
  return <><header data-page={pageKey}><div className="brand-wrap"><Link to="/pmp-assessment" className="brand"><span>PM</span>P Assessment</Link><span className="current-page-pill">{pageLabel}</span></div>{pageKey !== "auth" && <nav>{admin ? <><Link className={adminActive("pmp-question-bank") ? "active" : ""} to="/admin/pmp-question-bank">Question Bank</Link><Link className={adminActive("pmp-users") ? "active" : ""} to="/admin/pmp-users">Users</Link><Link className={adminActive("pmp-reports") ? "active" : ""} to="/admin/pmp-reports">Reports</Link><Link className={adminActive("pmp-domains") ? "active" : ""} to="/admin/pmp-domains">Domains</Link></> : <><Link className={active("dashboard") ? "active" : ""} to="/pmp-assessment/dashboard">Dashboard</Link><Link className={active("practice") ? "active" : ""} to="/pmp-assessment/practice">Practice</Link><Link className={active("results") ? "active" : ""} to="/pmp-assessment/history">Results</Link><Link className={active("profile") ? "active" : ""} to="/pmp-assessment/profile">Profile</Link></>}</nav>}</header><main>{children}</main><footer>Focused practice. Clear evidence. A better next move.</footer></>;
}
function Loading({ text="Loading..." }) { return <div className="state"><div className="spinner" />{text}</div>; }
function ErrorBox({ error }) { return error ? <div className="error">{error}</div> : null; }
function Stat({ label, value }) { return <article className="stat"><span>{label}</span><strong>{value ?? "-"}</strong></article>; }
function learnerSafeLabel(value="") {
  return String(value).replace(/exam0?([1-5])\.xlsx\s*Mock Exam/gi, "Mock Exam $1").replace(/exam0?([1-5])\.xlsx/gi, "Mock Exam $1");
}
function sameIds(a=[], b=[]) {
  const left = [...a].map(Number).sort((x,y)=>x-y);
  const right = [...b].map(Number).sort((x,y)=>x-y);
  return left.length === right.length && left.every((value,i)=>value === right[i]);
}
function attemptLabel(a) {
  if (a?.selected_domain_name) return learnerSafeLabel(a.selected_domain_name);
  if (a?.selected_topic_name) return learnerSafeLabel(a.selected_topic_name);
  if (a?.selected_methodology) return `${a.selected_methodology} Drill`;
  if (a?.selected_difficulty) return `${a.selected_difficulty} Drill`;
  const labels = {exam_simulator:"Full PMP Simulator", quick:"Quick Practice", random:"Random Practice", topic:"Topic Practice", full_practice:"Full Bank Practice", practice_1:"Mock Exam 1", practice_2:"Mock Exam 2", practice_3:"Mock Exam 3", practice_4:"Mock Exam 4", practice_5:"Mock Exam 5", methodology:"Methodology Drill", difficulty:"Difficulty Drill"};
  return labels[a?.exam_mode] || "PMP Practice";
}
function mockExamLabel(mode) {
  const number = String(mode || "").match(/\d+/)?.[0] || "";
  return number ? `Mock Exam ${Number(number)}` : "Mock Exam";
}
function isScoredAttempt(a) {
  return ["submitted", "report_generated"].includes(a?.status) && a.score_percentage !== null && a.score_percentage !== undefined;
}
function attemptResultSummary(a) {
  if (a?.status === "in_progress") return `${a.current_question_index || 0}/${a.question_count} answered`;
  if (isScoredAttempt(a)) return `${Math.round(a.score_percentage || 0)}% score | ${a.correct_count || 0}/${a.question_count} correct`;
  return a?.status === "abandoned" ? "Ended without submission" : titleize(a?.status || "Closed");
}
function attemptScoreTitle(a) {
  if (a?.status === "in_progress") return "In progress";
  if (isScoredAttempt(a)) return `${Math.round(a.score_percentage || 0)}%`;
  return a?.status === "abandoned" ? "Ended" : titleize(a?.status || "Closed");
}
function attemptPrimaryPath(a) {
  if (a?.status === "in_progress") return `/pmp-assessment/exam/${a.id}`;
  if (isScoredAttempt(a)) return `/pmp-assessment/result/${a.id}`;
  return "";
}
function DeleteAttemptButton({ attempt, onDelete }) {
  const [deleting, setDeleting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    if (deleting) return;
    setDeleting(true);
    setError("");
    try { await api.deleteAttempt(attempt.id); onDelete?.(attempt.id); setConfirming(false); }
    catch(error) { setError(error.message || "Unable to delete this attempt right now."); setDeleting(false); }
  }
  function open(e) {
    e.stopPropagation();
    if (deleting) return;
    setError("");
    setConfirming(true);
  }
  return <>
    <button type="button" className="danger delete-attempt-button" onClick={open} disabled={deleting}>{deleting ? "Deleting..." : "Delete"}</button>
    <DeleteAttemptModal attempt={attempt} open={confirming} deleting={deleting} error={error} onClose={()=>!deleting && setConfirming(false)} onDelete={remove}/>
  </>;
}
function DeleteAttemptModal({ attempt, open, deleting, error, onClose, onDelete }) {
  if (!open) return null;
  const blockOutsideInteraction = (e)=>{
    e.stopPropagation();
  };
  return createPortal(<div className="submit-warning-backdrop delete-attempt-backdrop" role="alertdialog" aria-modal="true" aria-labelledby={`delete-attempt-${attempt.id}`} onClick={blockOutsideInteraction} onMouseMove={blockOutsideInteraction}>
    <div className="submit-warning-modal delete-attempt-modal" onClick={e=>e.stopPropagation()}>
      <p className="eyebrow">DELETE ATTEMPT</p>
      <h2 id={`delete-attempt-${attempt.id}`}>Delete this attempt?</h2>
      <div className="submit-warning-message">
        <strong>{attemptLabel(attempt)}</strong>
        <p>This removes the attempt, answers, score, and report. This cannot be undone.</p>
      </div>
      <ErrorBox error={error}/>
      <div className="submit-warning-actions">
        <button type="button" className="secondary" onClick={onClose} disabled={deleting}>Cancel</button>
        <button type="button" className="danger" onClick={onDelete} disabled={deleting}>{deleting ? "Deleting..." : "Delete attempt"}</button>
      </div>
    </div>
  </div>, document.body);
}
function AttemptActions({ attempt, onDelete }) {
  const deleteButton = <DeleteAttemptButton attempt={attempt} onDelete={onDelete}/>;
  if (attempt.status === "in_progress") return <div className="attempt-actions" onClick={e=>e.stopPropagation()}><Link className="button" to={`/pmp-assessment/exam/${attempt.id}`}>Resume</Link>{deleteButton}</div>;
  if (isScoredAttempt(attempt)) return <div className="attempt-actions" onClick={e=>e.stopPropagation()}><Link className="button secondary" to={`/pmp-assessment/result/${attempt.id}`}>View Report</Link><Link className="button secondary" to={`/pmp-assessment/exam/${attempt.id}`}>Review Exam</Link>{deleteButton}</div>;
  return <div className="attempt-actions" onClick={e=>e.stopPropagation()}><span className="attempt-ended-note">No result</span>{deleteButton}</div>;
}
function isAuthError(error) { return error?.status === 401 || error?.status === 403; }
function formatDuration(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}` : `${minutes}:${String(secs).padStart(2, "0")}`;
}
const pmpMindsetChecklist = [
  "Find the real problem before choosing an action.",
  "Prefer assess, communicate, and collaborate before escalate.",
  "Use the plan, contract, charter, or risk process when governance matters.",
  "Choose servant leadership for people issues, not avoidance."
];
function domainMindset(domain="") {
  const key = String(domain).toLowerCase();
  if (key.includes("risk")) return "Risk questions usually reward proactive analysis, ownership, and planned responses.";
  if (key.includes("stakeholder")) return "Stakeholder questions usually reward engagement, empathy, and clear communication.";
  if (key.includes("resource")) return "Resource questions usually reward servant leadership, coaching, and removing blockers.";
  if (key.includes("schedule")) return "Schedule questions usually reward impact analysis before compressing or changing the plan.";
  if (key.includes("scope")) return "Scope questions usually reward change control and protecting agreed value.";
  if (key.includes("finance")) return "Finance questions usually reward evidence, forecasts, and control thresholds.";
  if (key.includes("governance")) return "Governance questions usually reward following the right authority, plan, or agreement first.";
  return "PMP questions usually test the next best action, not the fastest reaction.";
}
function pmpTrapHint(item={}) {
  const selected = String(item.selected_answer || "").toLowerCase();
  const question = String(item.question || "").toLowerCase();
  if (selected.includes("ignore") || selected.includes("continue")) return "Ignoring a visible issue is usually a trap; PMI expects timely ownership and communication.";
  if (selected.includes("escalat")) return "Escalation can be correct, but only after the project manager understands the facts and uses the right process.";
  if (selected.includes("report") && question.includes("vendor")) return "Internal reports do not solve vendor accountability; contracts and procurement agreements drive the next move.";
  if (question.includes("change") || question.includes("scope")) return "If the scenario changes scope, look for impact analysis and formal change control before action.";
  if (question.includes("risk")) return "Risk scenarios reward identifying, analysing, and responding through the risk process instead of reacting late.";
  return domainMindset(item.domain || item.performance_domain);
}

function titleize(value) {
  return String(value || "").replace(/_/g, " ").replace(/\b\w/g, c=>c.toUpperCase());
}
function reportItems(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === "object") return Object.entries(value).map(([key, val])=>({title:titleize(key), value:val}));
  return [value];
}
function reportText(value) {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) return value.map(reportText).filter(Boolean).join("; ");
  if (typeof value === "object") return Object.entries(value).filter(([,v])=>v !== null && v !== undefined && v !== "").map(([k,v])=>`${titleize(k)}: ${reportText(v)}`).join("; ");
  return learnerSafeLabel(String(value));
}
function isInternalSheetReference(value) {
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.some(isInternalSheetReference);
  if (typeof value === "object") return Object.values(value).some(isInternalSheetReference);
  return /\.xlsx\b/i.test(String(value));
}
function ReportField({ name, value }) {
  if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) return null;
  const text = reportText(value);
  const listItems = Array.isArray(value) ? value.filter(item=>!isInternalSheetReference(item)).map(reportText).filter(Boolean) : [];
  if (!text || isInternalSheetReference(value) || (Array.isArray(value) && !listItems.length)) return null;
  return <div className="ai-field"><b>{titleize(name)}</b>{Array.isArray(value) ? <ul>{listItems.map((item,index)=><li key={index}>{item}</li>)}</ul> : <p>{text}</p>}</div>;
}
function ReportCard({ item, fallback }) {
  const obj = item && typeof item === "object" && !Array.isArray(item) ? item : {detail:item};
  if (Object.keys(obj).length === 1 && obj.detail !== undefined && isInternalSheetReference(obj.detail)) return null;
  const isChapter = Boolean(obj.chapter_title || obj.core_lesson || obj.correct_thinking_pattern);
  const heading = obj.chapter_title || obj.title || obj.area || obj.topic || obj.domain || obj.theme || obj.day || obj.focus_area || fallback;
  const hiddenKeys = ["chapter_title","title","area","topic","domain","theme","day","focus_area","source","source_file","source_sheet","source_exam","source_label"];
  const safeHeading = heading && !isInternalSheetReference(heading) ? reportText(heading) : fallback;
  return <article className={isChapter ? "ai-chapter-card" : ""}>{safeHeading && <h3>{obj.chapter_number ? `Chapter ${obj.chapter_number}: ` : ""}{safeHeading}</h3>}{Object.entries(obj).map(([key,value])=>hiddenKeys.includes(key) ? null : <ReportField key={key} name={key} value={value}/>)}</article>;
}
function ReportSection({ title, value, compact=false }) {
  const items = reportItems(value);
  if (!items.length) return null;
  const isChapters = title === "Learning chapters" || title === "Personal Study Chapters";
  return <div className={`${compact ? "ai-section compact" : "ai-section"} ${isChapters ? "learning-chapters" : ""}`}><h3>{title}</h3><div className={isChapters ? "ai-card-grid chapter-grid" : "ai-card-grid"}>{items.map((item,index)=><ReportCard key={index} item={item} fallback={`${title} ${index+1}`} />)}</div></div>;
}
function ProfileContextSummary({ context }) {
  if (!context || !Object.keys(context).length) return null;
  const name = context.name || context.full_name;
  const role = context.job_title;
  const company = context.company || context.company_name;
  const industry = context.industry;
  const country = context.country;
  const years = Number(context.years_project_experience || 0);
  const roleDescription = String(context.role_description || "").trim();
  const chips = [role, company, industry, country, years ? `${context.years_project_experience} year${years === 1 ? "" : "s"} experience` : ""].filter(value=>String(value || "").trim());
  const applications = [];
  if (role || company) applications.push({title:"Role lens", text:`Coaching examples are framed around ${[role, company].filter(Boolean).join(" at ")} decisions, so recommendations stay close to the learner's real work.`});
  if (industry) applications.push({title:"Industry lens", text:`Study guidance keeps ${industry} scenarios in mind while still using PMI-first exam logic.`});
  if (years) applications.push({title:"Experience calibration", text: years <= 2 ? "Advice focuses on repeatable PMP decision patterns, traps, and first-step discipline." : "Advice can move faster into judgement calls, governance tradeoffs, and exam traps."});
  if (roleDescription) applications.push({title:"Work context", text:`Relevant day-to-day context: ${roleDescription.length > 150 ? `${roleDescription.slice(0,150)}...` : roleDescription}`});
  if (country) applications.push({title:"Local relevance", text:`Country context is kept for wording and career relevance, not for changing the PMP scoring logic.`});
  if (!name && !chips.length && !applications.length) return null;
  return <section className="profile-application-section"><div className="profile-application-head"><div><p className="eyebrow">PROFILE APPLICATION</p><h3>{name ? `How ${name}'s profile shaped this report` : "How the profile shaped this report"}</h3><p>This context is used to make the coaching more applicable. It does not change the exam score.</p></div>{chips.length > 0 && <div className="profile-context-chips">{chips.map((chip,index)=><span key={index}>{chip}</span>)}</div>}</div>{applications.length > 0 && <div className="profile-application-grid">{applications.map(item=><article key={item.title}><strong>{item.title}</strong><p>{item.text}</p></article>)}</div>}</section>;
}
function Auth() {
  const nav = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({full_name:"", email:"", password:"", confirm_password:""});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function signInWith(email, password) {
    setBusy(true); setError("");
    setForm(current=>({...current, email, password}));
    try {
      await api.login({email, password});
      nav("/pmp-assessment/dashboard");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  useEffect(()=>{
    const params = new URLSearchParams(location.search);
    if (params.get("login") === "ahmed") signInWith("contact+cb09dcc78932@example.com", "PmpTemp#2026!");
  },[location.search]);
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      if (mode === "login") await api.login({email:form.email.trim(), password:form.password});
      else await api.register(form);
      nav("/pmp-assessment/dashboard");
    } catch (e) {
      if (mode === "register" && /already has an account|already exists/i.test(e.message || "")) setError("This email is already registered. Use the correct password and I will sign you straight in.");
      else setError(e.message);
    } finally { setBusy(false); }
  }
  return <Layout><section className="hero"><div><p className="eyebrow">STANDALONE PMP PRACTICE</p><h1>{mode === "login" ? "Sign in to your PMP dashboard." : "Create your PMP account."}</h1><p className="lead">KBC learner status is detected securely from your email. External candidates use the same PMP exam engine.</p></div><form className="panel form-grid" onSubmit={submit}>{mode === "register" && <label className="wide">Full name<input value={form.full_name} onChange={e=>setForm({...form, full_name:e.target.value})} /></label>}<label className="wide">Email<input required type="email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} /></label><label className="wide">Password<input required type="password" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} /></label>{mode === "register" && <label className="wide">Confirm password<input required type="password" value={form.confirm_password} onChange={e=>setForm({...form, confirm_password:e.target.value})} /></label>}<ErrorBox error={error}/><button disabled={busy}>{busy ? "Working..." : mode === "login" ? "Sign in" : "Register"}</button><button type="button" className="secondary" onClick={()=>setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create account" : "I already have an account"}</button>{mode === "login" && <button type="button" className="secondary wide" disabled={busy} onClick={()=>signInWith("contact+cb09dcc78932@example.com", "PmpTemp#2026!")}>Use Ahmed test account</button>}</form></section></Layout>;
}

function Dashboard() {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [selectedFocus, setSelectedFocus] = useState("all");
  const [attemptFilter, setAttemptFilter] = useState("all");
  const [selectedAttemptId, setSelectedAttemptId] = useState(null);
  const [error, setError] = useState("");
  const [quick, setQuick] = useState({question_count:10, selected_domain_id:""});
  const [topicDomainId, setTopicDomainId] = useState("");
  const [topics, setTopics] = useState([]);
  const [topicPractice, setTopicPractice] = useState({question_count:20, selected_topic_id:""});
  const [methodologyPractice, setMethodologyPractice] = useState({question_count:20, selected_methodology:"Agile"});
  const [difficultyPractice, setDifficultyPractice] = useState({question_count:20, selected_difficulty:"Medium"});

  useEffect(()=>{
    Promise.all([api.dashboard(), api.attempts()])
      .then(([dashboardData, attemptRows])=>{ setData(dashboardData); setAttempts(attemptRows || []); setError(""); })
      .catch(e=>{ if (isAuthError(e)) nav("/pmp-assessment"); else setError(e.message); });
  },[nav]);
  useEffect(()=>{
    api.topics(topicDomainId)
      .then(rows=>{
        setTopics(rows);
        setTopicPractice(current=>({...current, selected_topic_id: rows.some(t=>String(t.id) === String(current.selected_topic_id)) ? current.selected_topic_id : ""}));
      })
      .catch(e=>setError(e.message));
  },[topicDomainId]);

  async function start(payload) {
    try {
      setError("");
      const attempt = await api.createAttempt(payload);
      nav(`/pmp-assessment/exam/${attempt.id}`);
    } catch(e) {
      if (e.status === 409 && e.data?.attempt) {
        setError(`You already have an active ${attemptLabel(e.data.attempt)}. Resume it from the card above, or let it expire before starting another assessment.`);
        return;
      }
      setError(e.message);
    }
  }
  function removeAttemptFromDashboard(attemptId) {
    setAttempts(current=>current.filter(attempt=>String(attempt.id) !== String(attemptId)));
    setSelectedAttemptId(current=>String(current) === String(attemptId) ? null : current);
    setData(current=>current ? {
      ...current,
      recent_attempts: (current.recent_attempts || []).filter(attempt=>String(attempt.id) !== String(attemptId)),
      active_attempt: String(current.active_attempt?.id) === String(attemptId) ? null : current.active_attempt,
      stats: {...(current.stats || {}), total_attempts: Math.max(0, Number(current.stats?.total_attempts || 0) - 1)},
    } : current);
  }

  if (error && !data) {
    return <Layout><ErrorBox error={error}/><button onClick={()=>window.location.reload()}>Try again</button></Layout>;
  }
  if (!data) return <Layout><Loading /></Layout>;

  const p = data.profile;
  const allAttempts = attempts.length ? attempts : (data.recent_attempts || []);
  const completedAttempts = allAttempts.filter(a=>a.status !== "in_progress" && a.score_percentage !== null && a.score_percentage !== undefined);
  const activeAttempts = allAttempts.filter(a=>a.status === "in_progress");
  const chronological = [...completedAttempts].sort((a,b)=>new Date(a.submitted_at || a.started_at || 0) - new Date(b.submitted_at || b.started_at || 0));
  const recentTrend = chronological.slice(-8);
  const scores = completedAttempts.map(a=>Number(a.score_percentage || 0));
  const completed = scores.length || data.stats.completed_attempts;
  const averageScore = scores.length ? Math.round(scores.reduce((sum,score)=>sum+score,0)/scores.length) : Math.round(data.stats.average_score || 0);
  const bestScore = scores.length ? Math.round(Math.max(...scores)) : Math.round(data.stats.best_score || 0);
  const firstScore = chronological[0]?.score_percentage;
  const latestScore = chronological[chronological.length - 1]?.score_percentage ?? data.stats.latest_score;
  const movement = firstScore !== undefined && latestScore !== undefined ? Math.round(latestScore - firstScore) : 0;
  const focusRows = data.domains.filter(d=>d.attempts).map(d=>({name:d.name, count:d.attempts, average:Math.round(d.latest_score ?? 0), best:Math.round(d.best_score ?? d.latest_score ?? 0), latest:Math.round(d.latest_score ?? 0)})).sort((a,b)=>a.average-b.average);
  const attemptsByFocus = selectedFocus === "all" ? allAttempts : allAttempts.filter(a=>attemptLabel(a) === selectedFocus);
  const visibleAttempts = attemptsByFocus.filter(a=>attemptFilter === "all" ? true : attemptFilter === "active" ? a.status === "in_progress" : a.status !== "in_progress");
  const selectedAttempt = allAttempts.find(a=>String(a.id) === String(selectedAttemptId)) || chronological[chronological.length - 1] || allAttempts[0];
  const trendChartPoints = recentTrend.map((a,index)=>{ const x = recentTrend.length === 1 ? 200 : 24 + (index * (352/(recentTrend.length-1))); const y = 136 - (Number(a.score_percentage || 0) * 1.12); return `${x},${Math.max(20, Math.min(136, y))}`; }).join(" ");
  const simulatorReady = data.simulator?.ready ?? data.domains.every(d=>d.exam_ready);
  const simulatorBlueprint = data.simulator?.blueprint || [];
  const selectedTopic = topics.find(t=>String(t.id) === String(topicPractice.selected_topic_id));
  const topicAvailable = selectedTopic?.available_questions || 0;
  const topicCounts = [10, 20, 40].filter(value=>value <= topicAvailable);
  const topicCountOptions = topicCounts.length ? topicCounts : (topicAvailable ? [topicAvailable] : []);
  const readinessPct = completed ? Math.round(latestScore || averageScore || 0) : 0;
  const attemptedDomains = data.domains.filter(d=>d.attempts).sort((a,b)=>Number(a.latest_score ?? 999)-Number(b.latest_score ?? 999));
  const recommendedDomains = attemptedDomains.length ? attemptedDomains.slice(0,3) : data.domains.slice(0,3);
  const recommendedDomain = recommendedDomains[0];
  const nextMoveText = data.active_attempt ? "Resume your active assessment" : completed ? `Focus next on ${recommendedDomain?.name || "targeted practice"}` : "Start with one focused practice attempt";
  const statusText = completedAttempts.length ? `${completedAttempts.length} completed, ${activeAttempts.length} in progress` : activeAttempts.length ? `${activeAttempts.length} in progress` : "No scored attempts yet";
  return (
    <Layout>
      <div className="page-head">
        <p className="eyebrow">{p.user_type === "KBC_LEARNER" ? "KBC LEARNER" : "EXTERNAL CANDIDATE"}</p>
        <h1>Welcome back, {p.name || p.full_name}</h1>
        <p>{p.user_type === "KBC_LEARNER" ? `Programme: ${p.programme || "Not provided"}` : "Choose a clear practice path and keep your progress in one place."}</p>
      </div>

      <ErrorBox error={error}/>

      <section className="dashboard-insights learner-insights">
        <article className="insight-card readiness-card">
          <button className="ring ring-button" type="button" style={{"--value": `${readinessPct}%`}} onClick={()=>setAttemptFilter("completed")}><strong>{completed ? `${readinessPct}%` : "--"}</strong><span>latest</span></button>
          <div><p className="eyebrow">YOUR READINESS</p><h2>{completed ? latestScore ? `${Math.round(latestScore)}% latest` : `${averageScore}% avg` : "Not measured yet"}</h2><p>{completed ? `${movement >= 0 ? "+" : ""}${movement}% movement from first to latest completed attempt.` : "Complete one practice attempt to unlock personalised progress."}</p></div>
        </article>
        <article className="insight-card trend-card compact-trend">
          <div><p className="eyebrow">SCORE TREND</p><h2>{completed ? `${averageScore}% average` : "No scores yet"}</h2></div>
          {recentTrend.length ? <svg viewBox="0 0 400 170" role="img" aria-label="Interactive score trend chart"><line x1="24" y1="24" x2="24" y2="140"/><line x1="24" y1="140" x2="380" y2="140"/><polyline points={trendChartPoints}/>{recentTrend.map((a,index)=>{ const [x,y]=trendChartPoints.split(" ")[index].split(","); const selected = String(selectedAttempt?.id) === String(a.id); return <g key={a.id} className={selected ? "selected-point" : ""} onClick={()=>setSelectedAttemptId(a.id)}><circle cx={x} cy={y} r={selected ? "7" : "5"}/><text x={x} y={Number(y)-11}>{Math.round(a.score_percentage)}%</text></g>; })}</svg> : <p className="muted">Complete an attempt to see movement.</p>}
        </article>
        <article className="insight-card focus-card">
          <p className="eyebrow">NEXT BEST MOVE</p>
          <h2>{nextMoveText}</h2>
          <p className="next-move-note">Choose a domain to start a 40-question practice attempt.</p>
          <div className="mini-rank interactive-rank">{recommendedDomains.map(d=><button type="button" key={d.id} onClick={()=>start({exam_mode:"domain", selected_domain_id:d.id, question_count:40})}><span>{d.name}</span><b>{d.latest_score ? `${Math.round(d.latest_score)}%` : "Start"}</b></button>)}</div>
        </article>
      </section>

      <section className="history-summary dashboard-history-summary">
        <article className="history-hero-card"><span>Progress snapshot</span><strong>{completed ? `${bestScore}% best score` : "Keep going"}</strong><p>{completed ? `Average score is ${averageScore}%. Click any chart point or domain below to inspect the evidence.` : "Complete an assessment to unlock score trend charts."}</p></article>
        <Stat label="Attempts" value={allAttempts.length}/>
        <Stat label="Completed" value={completedAttempts.length || data.stats.completed_attempts}/>
        <Stat label="Average" value={completed ? `${averageScore}%` : "-"}/>
        <Stat label="Active" value={activeAttempts.length}/>
      </section>

      <section className="history-grid dashboard-progress-grid">
        <article className="panel history-chart interactive-chart">
          <div className="history-panel-head"><div><p className="eyebrow">READINESS OVER TIME</p><h2>Progress trend</h2></div><span>{statusText}</span></div>
          {recentTrend.length ? <><svg viewBox="0 0 400 170" role="img" aria-label="Score trend chart"><line x1="24" y1="24" x2="24" y2="140"/><line x1="24" y1="140" x2="380" y2="140"/><polyline points={trendChartPoints}/>{recentTrend.map((a,index)=>{ const [x,y]=trendChartPoints.split(" ")[index].split(","); const selected = String(selectedAttempt?.id) === String(a.id); return <g key={a.id} className={selected ? "selected-point" : ""} onClick={()=>setSelectedAttemptId(a.id)}><circle cx={x} cy={y} r={selected ? "8" : "5"}/><text x={x} y={Number(y)-12}>{Math.round(a.score_percentage)}%</text></g>; })}</svg>{selectedAttempt && <div className="selected-attempt-card"><span>Selected attempt</span><strong>{attemptLabel(selectedAttempt)}</strong><p>{attemptResultSummary(selectedAttempt)}</p><AttemptActions attempt={selectedAttempt} onDelete={removeAttemptFromDashboard}/></div>}</> : <p className="muted">No completed attempts yet.</p>}
        </article>
      </section>

      <section className="panel history-list-panel dashboard-attempt-panel">
        <div className="history-panel-head"><div><p className="eyebrow">ATTEMPT LOG</p><h2>{selectedFocus === "all" ? "Recent activity" : selectedFocus}</h2></div><div className="attempt-filter-tabs">{["all","completed","active"].map(filter=><button key={filter} type="button" className={attemptFilter === filter ? "on" : ""} onClick={()=>setAttemptFilter(filter)}>{titleize(filter)}</button>)}</div></div>
        {visibleAttempts.length ? <div className="history-attempt-list">{visibleAttempts.map(a=><article key={a.id} className={String(selectedAttempt?.id) === String(a.id) ? "selected" : ""} onClick={()=>setSelectedAttemptId(a.id)}><div><span>{attemptLabel(a)}</span><h3>{attemptScoreTitle(a)}</h3><p>{a.question_count} questions | {a.duration_minutes} minutes | {a.started_at ? new Date(a.started_at).toLocaleString() : "Not started"}</p></div><div className="attempt-score-pill"><b>{a.status === "in_progress" ? `${a.current_question_index || 0}/${a.question_count}` : isScoredAttempt(a) ? `${a.correct_count || 0}/${a.question_count}` : "-"}</b><small>{a.status === "in_progress" ? "answered" : isScoredAttempt(a) ? "correct" : "not scored"}</small></div><AttemptActions attempt={a} onDelete={removeAttemptFromDashboard}/></article>)}</div> : <p className="muted">No attempts match this filter yet.</p>}
      </section>
      {data.active_attempt && (
        <section className="panel resume-panel">
          <div>
            <p className="eyebrow">RESUME YOUR ASSESSMENT</p>
            <h2>{attemptLabel(data.active_attempt)}</h2>
            <p>{data.active_attempt.answered_count} / {data.active_attempt.question_count} answered</p>
          </div>
          <Link className="button" to={`/pmp-assessment/exam/${data.active_attempt.id}`}>Resume</Link>
        </section>
      )}

      <section className="panel blueprint-panel">
        <div>
          <p className="eyebrow">EXAM BLUEPRINT</p>
          <h2>Official PMP exam vs practice map</h2>
          <p>The full simulator follows the official PMI exam domains. The seven practice domains below are our learner-friendly map for drilling weak skills.</p>
        </div>
        <div className="blueprint-grid">
          <article><span>Official exam</span><strong>3 domains</strong><p>People, Process, Business Environment</p></article>
          <article><span>Practice diagnosis</span><strong>7 domains</strong><p>Governance, Scope, Schedule, Finance, Stakeholders, Resources, Risk</p></article>
          <article><span>Why both</span><strong>Sellable coaching</strong><p>Compliance for mocks, detail for personal study plans.</p></article>
        </div>
      </section>

    </Layout>
  );
}

function ExhibitImage({ exhibit, mode="inline", zoom=1, fitMode="screen", pan={x:0,y:0}, retryKey=0, onLoad, onError, onOpen, panHandlers={} }) {
  if (!exhibit?.url) return null;
  const alt = exhibitDisplayText(exhibit) || "Question exhibit";
  const style = mode === "modal" ? {transform:`translate(${pan.x}px, ${pan.y}px) scale(${zoom})`} : undefined;
  return <button type="button" className={`exhibit-image-frame ${mode} fit-${fitMode}`} onClick={onOpen} {...panHandlers}>
    <img key={`${exhibit.url}-${retryKey}`} src={exhibit.url} alt={alt} loading="lazy" decoding="async" onLoad={onLoad} onError={onError} style={style} draggable="false" />
  </button>;
}
function isGenericExhibitText(value) {
  return /^question\s+\d+\s+exhibit$/i.test(String(value || "").trim()) || /^question\s+exhibit$/i.test(String(value || "").trim());
}
function exhibitDisplayText(exhibit) {
  const title = isGenericExhibitText(exhibit?.title) ? "" : String(exhibit?.title || "").trim();
  const caption = isGenericExhibitText(exhibit?.caption) ? "" : String(exhibit?.caption || "").trim();
  return title || caption;
}
function ExhibitViewer({ question }) {
  const fallback = question?.exhibit_url ? [{id:"legacy", title:question.exhibit_alt_text || "Question exhibit", type:"image", url:question.exhibit_url, content:null, caption:question.exhibit_alt_text || ""}] : [];
  const exhibits = question?.exhibits?.length ? question.exhibits : fallback;
  const [activeIndex, setActiveIndex] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [loadState, setLoadState] = useState({});
  const [retryKeys, setRetryKeys] = useState({});
  const [zoom, setZoom] = useState(1);
  const [fitMode, setFitMode] = useState("screen");
  const [pan, setPan] = useState({x:0,y:0});
  const drag = useRef(null);
  const modalRef = useRef(null);
  const active = exhibits[activeIndex] || exhibits[0];
  const displayText = exhibitDisplayText(active);
  const keyFor = exhibit=>String(exhibit?.id || exhibit?.url || exhibit?.title || activeIndex);
  const activeKey = keyFor(active);
  const state = loadState[activeKey] || (active?.url ? "loading" : "ready");
  const setImageState = value=>setLoadState(current=>({...current, [activeKey]:value}));
  const resetView = (nextFit=fitMode)=>{ setZoom(1); setPan({x:0,y:0}); setFitMode(nextFit); };
  const zoomBy = amount=>{ setFitMode("free"); setZoom(value=>Math.min(4, Math.max(.5, Number((value + amount).toFixed(2))))); };
  useEffect(()=>{ setActiveIndex(0); resetView("screen"); }, [question?.id]);
  useEffect(()=>{ resetView("screen"); }, [activeKey]);
  useEffect(()=>{
    if (!modalOpen) return;
    const close = event=>{ if (event.key === "Escape") setModalOpen(false); };
    window.addEventListener("keydown", close);
    return ()=>window.removeEventListener("keydown", close);
  }, [modalOpen]);
  function fullScreen() {
    const node = modalRef.current;
    if (node?.requestFullscreen) node.requestFullscreen().catch(()=>{});
  }
  function retry() {
    setImageState("loading");
    setRetryKeys(current=>({...current, [activeKey]:(current[activeKey] || 0) + 1}));
  }
  const panHandlers = {
    onMouseDown:event=>{ if (zoom <= 1) return; drag.current = {x:event.clientX - pan.x, y:event.clientY - pan.y}; event.preventDefault(); },
    onMouseMove:event=>{ if (!drag.current) return; setPan({x:event.clientX - drag.current.x, y:event.clientY - drag.current.y}); },
    onMouseUp:()=>{ drag.current = null; },
    onMouseLeave:()=>{ drag.current = null; },
    onTouchStart:event=>{ if (zoom <= 1 || !event.touches[0]) return; drag.current = {x:event.touches[0].clientX - pan.x, y:event.touches[0].clientY - pan.y}; },
    onTouchMove:event=>{ if (!drag.current || !event.touches[0]) return; setPan({x:event.touches[0].clientX - drag.current.x, y:event.touches[0].clientY - drag.current.y}); },
    onTouchEnd:()=>{ drag.current = null; },
  };
  if (!exhibits.length) return null;
  return <>
    <aside className="exhibit-panel" aria-label="Question exhibits">
      <div className="exhibit-panel-head"><span>Exhibits</span><strong>{exhibits.length}</strong></div>
      {exhibits.length > 1 && <div className="exhibit-tabs" role="tablist" aria-label="Select exhibit">{exhibits.map((exhibit,index)=><button type="button" role="tab" aria-selected={index === activeIndex} className={index === activeIndex ? "active" : ""} key={keyFor(exhibit)} onClick={()=>setActiveIndex(index)}>Exhibit {index+1}</button>)}</div>}
      <article className={`exam-exhibit ${active?.type || "image"}`}>
        <div className="exam-exhibit-title">
          <div><span>{titleize(active?.type || "image")}</span>{displayText && <h3>{displayText}</h3>}</div>
          {active?.url && <button type="button" className="secondary" onClick={()=>setModalOpen(true)}>Full screen</button>}
        </div>
        {active?.content && <div className="case-study-content">{String(active.content).split(/\n{2,}/).map((part,i)=><p key={i}>{part}</p>)}</div>}
        {active?.url && <div className={`exhibit-load-wrap ${state === "error" ? "broken" : ""}`}>
          {state === "loading" && <div className="exhibit-loading">Loading exhibit...</div>}
          {state !== "error" ? <ExhibitImage exhibit={active} onLoad={()=>setImageState("ready")} onError={()=>setImageState("error")} onOpen={()=>setModalOpen(true)} retryKey={retryKeys[activeKey] || 0} /> : <div className="exhibit-fallback"><span>Exhibit could not be loaded.</span><button type="button" className="secondary" onClick={retry}>Retry</button></div>}
        </div>}
        {displayText && <p className="exhibit-caption">{displayText}</p>}
      </article>
    </aside>
    {modalOpen && <div className="exhibit-modal" role="dialog" aria-modal="true" aria-label="Exhibit full screen viewer" ref={modalRef}>
      <div className="exhibit-modal-toolbar">
        <div><span>{exhibits.length > 1 ? `Exhibit ${activeIndex+1} of ${exhibits.length}` : "Exhibit"}</span>{displayText && <strong>{displayText}</strong>}</div>
        <div className="exhibit-controls" aria-label="Exhibit controls">
          <button type="button" onClick={()=>zoomBy(.25)}>Zoom in</button>
          <button type="button" onClick={()=>zoomBy(-.25)}>Zoom out</button>
          <button type="button" onClick={()=>resetView("screen")}>Fit screen</button>
          <button type="button" onClick={()=>resetView("width")}>Fit width</button>
          <button type="button" onClick={()=>resetView("free")}>Reset</button>
          <button type="button" onClick={fullScreen}>Full screen</button>
          <button type="button" className="exhibit-close-button" aria-label="Close exhibit preview" onClick={()=>setModalOpen(false)}>X</button>
        </div>
      </div>
      {exhibits.length > 1 && <div className="exhibit-modal-tabs">{exhibits.map((exhibit,index)=><button type="button" className={index === activeIndex ? "active" : ""} key={keyFor(exhibit)} onClick={()=>setActiveIndex(index)}>Exhibit {index+1}</button>)}</div>}
      <div className="exhibit-modal-body">
        {active?.content && <div className="case-study-content large">{String(active.content).split(/\n{2,}/).map((part,i)=><p key={i}>{part}</p>)}</div>}
        {active?.url && state !== "error" && <ExhibitImage exhibit={active} mode="modal" zoom={zoom} fitMode={fitMode} pan={pan} panHandlers={panHandlers} onLoad={()=>setImageState("ready")} onError={()=>setImageState("error")} retryKey={retryKeys[activeKey] || 0} />}
        {state === "error" && <div className="exhibit-fallback large"><span>Exhibit could not be loaded.</span><button type="button" className="secondary" onClick={retry}>Retry</button></div>}
      </div>
      {displayText && <p className="exhibit-modal-caption">{displayText}</p>}
    </div>}
  </>;
}
function Practice() {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [topics, setTopics] = useState([]);
  const [topicDomainId, setTopicDomainId] = useState("");
  const [topicPractice, setTopicPractice] = useState({question_count:20, selected_topic_id:""});
  const [methodologyPractice, setMethodologyPractice] = useState({question_count:20, selected_methodology:"Agile"});
  const [difficultyPractice, setDifficultyPractice] = useState({question_count:20, selected_difficulty:"Medium"});
  const [fullPracticeCount, setFullPracticeCount] = useState(40);
  const [quickCount, setQuickCount] = useState(10);
  const [error, setError] = useState("");
  const friendlyPracticeError = "Unable to refresh assessment data.";

  function formatDate(value) {
    if (!value) return "Not available";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Not available";
    return date.toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"});
  }

  function formatDuration(minutes) {
    if (!minutes) return "Duration not set";
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (!hours) return `${mins} min`;
    return mins ? `${hours} hr ${mins} min` : `${hours} hr`;
  }

  function formatTimeRemaining(attempt) {
    if (!attempt?.started_at || !attempt?.duration_minutes) return "Not available";
    const endAt = new Date(attempt.started_at).getTime() + Number(attempt.duration_minutes) * 60 * 1000;
    const totalSeconds = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    if (!hours) return `${minutes} min`;
    return `${hours} hr ${minutes.toString().padStart(2, "0")} min`;
  }

  function handlePracticeError(error) {
    console.error("Practice Center data error", error);
    if (isAuthError(error)) nav("/pmp-assessment");
    else setError(friendlyPracticeError);
  }

  function reloadPracticeData() {
    setError("");
    api.dashboard()
      .then(x=>{ setData(x); setTopicDomainId(current=>current || String(x.domains?.[0]?.id || "")); })
      .catch(handlePracticeError);
    api.attempts()
      .then(rows=>setAttempts(rows || []))
      .catch(e=>console.error("Practice Center attempts error", e));
  }

  useEffect(()=>{
    reloadPracticeData();
  },[nav]);

  useEffect(()=>{
    if (!topicDomainId) { setTopics([]); return; }
    api.topics(topicDomainId)
      .then(rows=>{
        setTopics(rows || []);
        setTopicPractice(current=>({...current, selected_topic_id: rows?.some(t=>String(t.id) === String(current.selected_topic_id)) ? current.selected_topic_id : ""}));
      })
      .catch(e=>{ console.error("Practice Center topics error", e); setTopics([]); setError(friendlyPracticeError); });
  },[topicDomainId]);

  async function start(payload) {
    try {
      setError("");
      const attempt = await api.createAttempt(payload);
      nav(`/pmp-assessment/exam/${attempt.id}`);
    } catch(e) {
      if (e.status === 409 && e.data?.attempt) {
        setError(`You already have an active ${attemptLabel(e.data.attempt)}. Resume it from the card above before starting a new one.`);
        return;
      }
      console.error("Practice Center start error", e);
      setError("Unable to start this practice attempt. Please try again.");
    }
  }

  if (!data) return <Layout>
    <div className="page-head practice-head">
      <p className="eyebrow">PMP ASSESSMENT</p>
      <h1>Practice Center</h1>
      <p>Aligned to the current PMP preparation structure.</p>
    </div>
    {error && <div className="practice-error" role="alert"><span>{error}</span><button type="button" className="secondary" onClick={reloadPracticeData}>Retry</button></div>}
    <div className="practice-skeleton-grid" aria-label="Loading Practice Center">
      {[1,2,3,4,5,6].map(item=><div key={item} className="practice-skeleton-card" />)}
    </div>
  </Layout>;

  const domains = data.domains || [];
  const simulatorReady = data.simulator?.ready ?? domains.every(d=>d.exam_ready);
  const simulatorDuration = data.simulator?.duration_minutes || 240;
  const simulatorQuestionCount = data.simulator?.question_count || 180;
  const selectedTopic = topics.find(t=>String(t.id) === String(topicPractice.selected_topic_id));
  const topicAvailable = selectedTopic?.available_questions || 0;
  const topicCountOptions = [10, 20, 40].filter(value=>value <= topicAvailable);
  const safeTopicCounts = topicCountOptions.length ? topicCountOptions : (topicAvailable ? [topicAvailable] : []);
  const selectedDomain = domains.find(d=>String(d.id) === String(topicDomainId));
  const domainAvailable = Number(selectedDomain?.available_questions || 0);
  const domainCountOptions = [10, 20, 25, 40, 60, 100, 120, 180].filter(value=>value <= domainAvailable);
  const safeDomainCounts = domainCountOptions.length ? domainCountOptions : (domainAvailable ? [domainAvailable] : []);
  const domainPracticeCount = safeDomainCounts.includes(Number(topicPractice.question_count)) ? Number(topicPractice.question_count) : (safeDomainCounts[0] || 0);
  const thinDomains = [...domains].sort((a,b)=>Number(a.available_questions || 0)-Number(b.available_questions || 0)).slice(0,3);
  const practiceSets = data.practice_sets?.length ? data.practice_sets : practiceExamModes.map(mode=>({mode, name:attemptLabel({exam_mode:mode}), available_questions:0, question_count:180, duration_minutes:240, ready:true}));
  const completedMockModes = new Set((attempts.length ? attempts : (data.recent_attempts || [])).filter(attempt=>practiceExamModes.includes(attempt.exam_mode) && isScoredAttempt(attempt)).map(attempt=>attempt.exam_mode));
  const officialDomains = data.simulator?.blueprint || [];
  const active = data.active_attempt;
  const activeProgress = active?.question_count ? Math.round((Number(active.answered_count || 0) / Number(active.question_count)) * 100) : 0;

  return <Layout>
    <div className="page-head practice-head practice-page-title">
      <p className="eyebrow">PMP ASSESSMENT</p>
      <h1>Practice Center</h1>
      <p>Aligned to the current PMP preparation structure.</p>
    </div>

    {error && <div className="practice-error" role="alert"><span>{error}</span><button type="button" className="secondary" onClick={reloadPracticeData}>Retry</button></div>}

    {active && <section className="panel practice-active-card">
      <div className="practice-active-main">
        <p className="eyebrow">ACTIVE ATTEMPT</p>
        <h2>{attemptLabel(active)}</h2>
        <p>{active.answered_count} of {active.question_count} answered</p>
        <div className="practice-progress" aria-label={`${activeProgress}% complete`}><i style={{width:`${Math.min(100, activeProgress)}%`}} /></div>
      </div>
      <div className="practice-active-stats">
        <span><b>{activeProgress}%</b>progress</span>
        <span><b>{formatTimeRemaining(active)}</b>remaining</span>
        <span><b>{formatDate(active.started_at)}</b>started</span>
      </div>
      <Link className="button practice-resume-button" to={`/pmp-assessment/exam/${active.id}`}>Resume attempt</Link>
    </section>}

    <section className="practice-primary-grid">
      <article className="panel practice-hero-card practice-simulator-card">
        <div>
          <p className="eyebrow">PRIMARY EXAM</p>
          <h2>Full PMP Simulator</h2>
          <p>Exam-style environment using the configured PMP simulator bank.</p>
        </div>
        <div className="practice-metric-row">
          <span><b>{simulatorQuestionCount}</b>questions</span>
          <span><b>{formatDuration(simulatorDuration)}</b>duration</span>
          <span><b>Exam</b>style</span>
        </div>
        <p className="practice-muted">Scheduled breaks will appear when they are supported by the current exam configuration.</p>
        <button disabled={!simulatorReady} onClick={()=>start({exam_mode:"exam_simulator"})}>{simulatorReady ? "Start simulator" : "Simulator not ready"}</button>
      </article>
      <div className="practice-quick-grid" aria-label="Quick practice">
        <article className="panel practice-control-card">
          <p className="eyebrow">QUICK PRACTICE</p>
          <h2>Random Practice</h2>
          <label>Questions<select value={quickCount} onChange={e=>setQuickCount(Number(e.target.value))}>{[10,20,40,60].map(x=><option key={x} value={x}>{x}</option>)}</select></label>
          <button onClick={()=>start({exam_mode:"random", question_count:quickCount})}>Start random</button>
        </article>
        <article className="panel practice-control-card">
          <p className="eyebrow">QUESTION BANK</p>
          <h2>Question Bank Practice</h2>
          <label>Questions<select value={fullPracticeCount} onChange={e=>setFullPracticeCount(Number(e.target.value))}>{[40,60,100,180].map(x=><option key={x} value={x}>{x}</option>)}</select></label>
          <button onClick={()=>start({exam_mode:"full_practice", question_count:fullPracticeCount})}>Start bank</button>
        </article>
      </div>
    </section>

    <section className="practice-section">
      <div className="section-title-row"><div><p className="eyebrow">PRACTICE EXAMS</p><h2>Five mock exams</h2></div></div>
      <div className="practice-set-grid">{practiceSets.map(set=>{ const completed = completedMockModes.has(set.mode); return <article key={set.mode} className={`practice-set-card ${completed ? "completed-mock" : ""}`}>
        <span>{mockExamLabel(set.mode)}{completed && <i aria-label="Completed mock exam" title="Completed">✓</i>}</span>
        <b>{set.question_count || set.available_questions || 0} questions | {set.duration_minutes || 0} min</b>
        <button type="button" disabled={!set.ready} onClick={()=>start({exam_mode:set.mode, question_count:set.question_count || set.available_questions || 180})}>{set.ready ? completed ? "Start new attempt" : "Start mock" : "Not ready"}</button>
      </article>})}</div>
    </section>

    <section className="practice-section">
      <div className="section-title-row"><div><p className="eyebrow">OFFICIAL PMP PERFORMANCE DOMAINS</p><h2>People, Process, Business Environment</h2></div><span>Simulator blueprint</span></div>
      <div className="practice-official-domain-grid">
        {officialDomains.length ? officialDomains.map(domain=><article key={domain.name} className="panel">
          <span>{domain.name}</span>
          {domain.weight != null && <strong>{domain.weight}%</strong>}
          {domain.count != null && <p>{domain.count} classified questions available.</p>}
        </article>) : ["People", "Process", "Business Environment"].map(name=><article key={name} className="panel">
          <span>{name}</span>
          <p>Performance metadata is not available from the current API response.</p>
        </article>)}
      </div>
    </section>

    <section className="practice-section">
      <div className="section-title-row"><div><p className="eyebrow">PRACTICE KNOWLEDGE AREAS</p><h2>Practice by category</h2></div><span>Existing question counts</span></div>
      <div className="practice-knowledge-grid">{domains.map((d,index)=><article className={`practice-knowledge-card accent-${index % 3}`} key={d.id}>
        <div className="domain-title"><span>{d.name}</span><strong>{d.available_questions}</strong></div>
        <p>{d.available_questions} questions available</p>
        {d.latest_score ? <small>Latest performance: {Math.round(d.latest_score)}%</small> : <small>Not attempted yet</small>}
        <div className="dashboard-bar"><i style={{width:`${Math.min(100, (Number(d.available_questions || 0) / 40) * 100)}%`}} /></div>
        <button disabled={!d.available_questions} onClick={()=>start({exam_mode:"domain", selected_domain_id:d.id})}>Start category</button>
      </article>)}</div>
    </section>

    <section className="practice-section">
      <div className="section-title-row"><div><p className="eyebrow">ADVANCED DRILLS</p><h2>Focused practice tools</h2></div></div>
      <div className="practice-drill-grid">
        <article className="panel practice-control-card wide-practice-card">
          <p className="eyebrow">DOMAIN DRILL</p>
          <h2>Target a performance domain</h2>
          <div className="practice-form-row"><label>Domain<select value={topicDomainId} onChange={e=>setTopicDomainId(e.target.value)}>{domains.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select></label><label>Questions<select value={domainPracticeCount || ""} onChange={e=>setTopicPractice({...topicPractice, question_count:Number(e.target.value)})}>{safeDomainCounts.length ? safeDomainCounts.map(x=><option key={x} value={x}>{x}</option>) : <option value="">No questions available</option>}</select></label></div>
          <button disabled={!topicDomainId || !domainAvailable || !domainPracticeCount} onClick={()=>start({exam_mode:"domain", selected_domain_id:Number(topicDomainId), question_count:domainPracticeCount})}>Start domain drill</button>
        </article>
        <article className="panel practice-control-card">
          <p className="eyebrow">APPROACH DRILL</p>
          <h2>Scenario style</h2>
          <label>Approach<select value={methodologyPractice.selected_methodology} onChange={e=>setMethodologyPractice({...methodologyPractice, selected_methodology:e.target.value})}>{practiceMethodologies.map(x=><option key={x}>{x}</option>)}</select></label>
          <button onClick={()=>start({exam_mode:"methodology", selected_methodology:methodologyPractice.selected_methodology, question_count:methodologyPractice.question_count})}>Start drill</button>
        </article>
        <article className="panel practice-control-card">
          <p className="eyebrow">DIFFICULTY DRILL</p>
          <h2>Build consistency</h2>
          <label>Level<select value={difficultyPractice.selected_difficulty} onChange={e=>setDifficultyPractice({...difficultyPractice, selected_difficulty:e.target.value})}>{difficulties.map(x=><option key={x}>{x}</option>)}</select></label>
          <button onClick={()=>start({exam_mode:"difficulty", selected_difficulty:difficultyPractice.selected_difficulty, question_count:difficultyPractice.question_count})}>Start drill</button>
        </article>
      </div>
    </section>

    {false && <section className="practice-section">
      <div className="section-title-row"><div><p className="eyebrow">PRACTICE EXAMS</p><h2>Five mock exams</h2></div></div>
      <div className="practice-set-grid">{practiceSets.map(set=>{ const completed = completedMockModes.has(set.mode); return <article key={set.mode} className={`practice-set-card ${completed ? "completed-mock" : ""}`}>
        <span>{mockExamLabel(set.mode)}{completed && <i aria-label="Completed mock exam" title="Completed">✓</i>}</span>
        <b>{set.question_count || set.available_questions || 0} questions | {set.duration_minutes || 0} min</b>
        <button type="button" disabled={!set.ready} onClick={()=>start({exam_mode:set.mode, question_count:set.question_count || set.available_questions || 180})}>{set.ready ? completed ? "Start new attempt" : "Start mock" : "Not ready"}</button>
      </article>})}</div>
    </section>}

    <section className="panel next-stock-panel practice-insights-panel">
      <div>
        <p className="eyebrow">CONTENT INSIGHTS</p>
        <h2>Content focus</h2>
      </div>
      <div className="mini-rank">{thinDomains.map(d=><div key={d.id}><span>{d.name}</span><b>{d.available_questions}</b></div>)}</div>
    </section>

  </Layout>;
}
function SubmitConfirmModal({ warning, submitting, onClose, onReviewUnanswered, onSubmit }) {
  if (!warning) return null;
  const isClear = warning.type === "confirm";
  return <div className="submit-warning-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
    <div className={`submit-warning-modal ${isClear ? "confirm" : ""}`} onClick={e=>e.stopPropagation()}>
      <p className="eyebrow">{isClear ? "FINAL CHECK" : "SUBMIT WARNING"}</p>
      <h2>{isClear ? "Ready to submit?" : "Submit this exam now?"}</h2>
      {isClear ? <div className="submit-confirm-message">
        <strong>Your answers are ready.</strong>
        <p>Once you submit, your answers will be locked and cannot be changed.</p>
      </div> : <div className="submit-warning-message">
        {warning.unanswered > 0 && <strong>{warning.unanswered} unanswered question{warning.unanswered === 1 ? "" : "s"}</strong>}
        {warning.flaggedCount > 0 && <span>{warning.flaggedCount} flagged for review</span>}
        <p>{warning.unanswered > 0 ? "Unanswered questions will be marked incorrect. " : ""}Once you submit, your answers will be locked and cannot be changed.</p>
      </div>}
      <div className="submit-warning-actions">
        <button type="button" className="secondary" onClick={onClose}>Keep working</button>
        {!isClear && <button type="button" className="secondary" disabled={!warning.unanswered} onClick={onReviewUnanswered}>Review unanswered</button>}
        <button type="button" className={isClear ? "primary" : "danger"} onClick={onSubmit} disabled={submitting}>{submitting ? "Submitting..." : isClear ? "Submit exam" : "Submit anyway"}</button>
      </div>
    </div>
  </div>;
}
function EndExamModal({ open, ending, onClose, onEnd }) {
  if (!open) return null;
  return <div className="submit-warning-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
    <div className="submit-warning-modal end-exam-modal" onClick={e=>e.stopPropagation()}>
      <p className="eyebrow">END EXAM</p>
      <h2>End this exam?</h2>
      <div className="submit-warning-message">
        <strong>This attempt will be discarded without a score.</strong>
        <p>Your exam will not be submitted, no result report will be created, and no answers from this attempt will be saved. Saved history and previous results will not be changed.</p>
      </div>
      <div className="submit-warning-actions">
        <button type="button" className="secondary" onClick={onClose} disabled={ending}>Keep working</button>
        <button type="button" className="danger" onClick={onEnd} disabled={ending}>{ending ? "Ending..." : "End exam"}</button>
      </div>
    </div>
  </div>;
}
function SaveStatus({ status, reviewMode }) {
  const state = reviewMode ? "submitted" : status === "Saved" ? "saved" : ["Saving...", "Syncing..."].includes(status) ? "saving" : status === "Saved locally" ? "local" : "error";
  return <span className={`save-status ${state}`}>{reviewMode ? "Review mode" : status}</span>;
}
function TimerDisplay({ startedAt, durationMinutes, status, onExpire }) {
  const [remaining, setRemaining] = useState(null);
  const expiredRef = useRef(false);
  useEffect(()=>{
    if (!startedAt || !durationMinutes || status !== "in_progress") return;
    const endAt = new Date(startedAt).getTime() + Number(durationMinutes) * 60 * 1000;
    function tick() {
      const next = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
      setRemaining(next);
      if (next === 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpire?.();
      }
    }
    tick();
    const timer = window.setInterval(tick, 1000);
    return ()=>window.clearInterval(timer);
  }, [startedAt, durationMinutes, status, onExpire]);
  const minutes = remaining === null ? null : Math.ceil(remaining / 60);
  const alert = minutes !== null && [30, 10, 5, 1].includes(minutes) ? `${minutes} min left` : "";
  return <span className={`timer ${remaining !== null && remaining <= 300 ? "urgent" : ""}`}><b>{remaining === null ? `${durationMinutes} min` : formatDuration(remaining)}</b>{alert && <small>{alert}</small>}</span>;
}
function ExamHeader({ attempt, index, total, reviewMode, saveState, submitting, flagged, onFlag, onSubmit, onEndExam, onReport, navCollapsed, onToggleNavigator, onExpire }) {
  return <div className="exam-top exam-header">
    <div className="exam-brand-group"><span className="brand"><span>PM</span>P Assessment</span><button type="button" className="secondary navigator-toggle" onClick={onToggleNavigator}>{navCollapsed ? "Show questions" : "Hide questions"}</button></div>
    <div className="exam-title"><strong>{attemptLabel(attempt)}</strong><small>Question {index+1} of {total} | <SaveStatus status={saveState} reviewMode={reviewMode}/></small></div>
    <div className="exam-controls">
      {!reviewMode && <button type="button" className="secondary end-exam-button" onClick={onEndExam}>End exam</button>}
      {reviewMode ? <span className="review-status-pill">Submitted</span> : <TimerDisplay startedAt={attempt?.started_at} durationMinutes={attempt?.duration_minutes} status={attempt?.status} onExpire={onExpire}/>}
      {!reviewMode && <button type="button" className={`flag-button header-flag ${flagged ? "active" : ""}`} onClick={onFlag}><i />{flagged ? "Flagged" : "Flag for Review"}</button>}
      {reviewMode ? <Link className="ghost exam-link" to={onReport}>Result report</Link> : <button className="ghost" onClick={onSubmit}>{submitting ? "Submitting..." : "Submit Exam"}</button>}
    </div>
  </div>;
}
function QuestionNavigator({ questions, index, answers, flagged, confidence, answerReviews, reviewMode, questionIsCorrect, filter, onFilter, collapsed, onToggle, onJump, answeredCount, unansweredCount, incorrectCount, flaggedCount, progress }) {
  const visibleQuestions = questions.map((question,i)=>({question,i})).filter(({question})=>filter === "flagged" ? flagged.has(question.id) : filter === "unanswered" ? !(answers[question.id] || []).length : true);
  return <aside className={`exam-navigator-panel ${collapsed ? "collapsed" : ""}`}>
    <div className="exam-side-summary"><strong>{reviewMode ? "Exam review" : `${progress}% complete`}</strong><span>{answeredCount} answered</span><span>{reviewMode ? `${incorrectCount} incorrect` : `${unansweredCount} unanswered`}</span><span>{flaggedCount} flagged</span></div>
    <div className="exam-side-actions">
      <button className={filter === "all" ? "secondary on" : "secondary"} onClick={()=>onFilter("all")}>All questions</button>
      <button className={filter === "unanswered" ? "secondary on" : "secondary"} disabled={reviewMode || !unansweredCount} onClick={()=>onFilter("unanswered")}>Unanswered</button>
      <button className={filter === "flagged" ? "secondary on" : "secondary"} disabled={!flaggedCount} onClick={()=>onFilter("flagged")}>Flagged</button>
      <button className="secondary collapse-nav" onClick={onToggle}>{collapsed ? "Open navigator" : "Collapse"}</button>
    </div>
    <div className="navigator">{visibleQuestions.map(({question,i})=>{ const isCorrect = questionIsCorrect(question); return <button key={question.id} aria-label={`Question ${i+1}${answers[question.id]?.length ? ", answered" : ", unanswered"}${flagged.has(question.id) ? ", flagged" : ""}`} title={`Question ${i+1}`} onClick={()=>onJump(i)} className={`${i===index?"current":""} ${answers[question.id]?.length?"answered":""} ${flagged.has(question.id)?"flagged":""} ${reviewMode ? (isCorrect ? "review-correct" : "review-wrong") : ""} ${answerReviews[question.id] ? "answer-revealed" : ""} ${confidence[question.id] ? `confidence-${confidence[question.id]}` : ""}`}>{i+1}</button>; })}</div>
    {!visibleQuestions.length && <p className="muted navigator-empty">No questions in this filter.</p>}
    <div className="exam-legend">{reviewMode ? <><span><i className="review-correct"/>Correct</span><span><i className="review-wrong"/>Incorrect</span><span><i className="current"/>Current</span></> : <><span><i className="answered"/>Answered</span><span><i className="flagged"/>Flagged</span><span><i className="current"/>Current</span></>}</div>
  </aside>;
}
function ExamFooter({ index, total, reviewMode, submitting, canReviewAnswer, reviewLoading, revealAnswer, selectedCount, flagged, onPrevious, onNext, onFlag, onReviewAnswer, onSubmit, reportUrl }) {
  return <div className="exam-footer">
    <button className="secondary" disabled={!index} onClick={onPrevious}>Previous</button>
    <div className="exam-footer-middle">
      {reviewMode ? <Link className="button secondary" to={reportUrl}>Result report</Link> : <>
        <button className="secondary" onClick={onFlag}>{flagged ? "Unflag" : "Flag for review"}</button>
        {canReviewAnswer && <button className="secondary review-answer-button" onClick={onReviewAnswer} disabled={reviewLoading || revealAnswer || !selectedCount}>{reviewLoading ? "Reviewing..." : revealAnswer ? "Answer reviewed" : "Review answer"}</button>}
        {index===total-1 && <button className="submit-bottom-button" onClick={onSubmit} disabled={submitting}>{submitting ? "Submitting..." : "Submit Exam"}</button>}
      </>}
    </div>
    <button disabled={index===total-1} onClick={onNext}>Next</button>
  </div>;
}
function QuestionRenderer({ q, index, reviewMode, showPracticeAids, revealAnswer, selectedForQuestion, correctForQuestion, revealedReview, confidence, canReviewAnswer, reviewLoading, error, onChoose, onToggleFlag, onConfidence, onReviewAnswer, onPrevious, onNext, onSubmit, submitting, total, flagged, attemptId }) {
  return <section className={`question exam-question ${q.exhibits?.length || q.exhibit_url ? "with-exhibits" : ""}`}>
    <div className="question-main">
      <div className="question-meta"><p className="eyebrow">{showPracticeAids ? <>QUESTION {index+1} | {q.performance_domain} | {q.methodology}</> : <>QUESTION {index+1}</>}</p>{revealAnswer ? <span className={`answer-state ${sameIds(selectedForQuestion, correctForQuestion) ? "correct" : "wrong"}`}>{sameIds(selectedForQuestion, correctForQuestion) ? "Correct" : "Review"}</span> : <button className={`flag-button ${flagged ? "active" : ""}`} onClick={onToggleFlag}><i />{flagged ? "Flagged" : "Flag"}</button>}</div>
      {q.case_text && <p className="case-text">{q.case_text}</p>}
      {showPracticeAids && <div className="mindset-card"><div><span>PMP mindset</span><strong>{domainMindset(q.performance_domain)}</strong></div><ul>{pmpMindsetChecklist.map(item=><li key={item}>{item}</li>)}</ul></div>}
      <h2>{q.question_text}</h2>
      <div className="options">{q.options.map(o=>{const picked=selectedForQuestion.includes(o.id); const correct=correctForQuestion.includes(o.id); const optionClass = `${picked?"picked":""} ${revealAnswer && correct ? "correct-option" : ""} ${revealAnswer && picked && !correct ? "wrong-option" : ""} ${revealAnswer && correct && !picked ? "missed-option" : ""}`; return <label className={optionClass} key={o.id}><input disabled={reviewMode || revealAnswer} type={q.question_type === "Multiple Response" ? "checkbox" : "radio"} name={`q${q.id}`} checked={picked} onChange={e=>onChoose(q,o.id,e.target.checked)} /><b aria-hidden="true">{o.option_label}</b><span>{o.option_text}</span>{revealAnswer && correct && <em>Correct</em>}{revealAnswer && picked && !correct && <em>Your choice</em>}</label>})}</div>
      {revealAnswer && <div className="review-explanation live-review"><b>{reviewMode ? "Explanation" : "Answer review"}</b><p>{reviewMode ? (q.explanation || "No explanation available for this question yet.") : (revealedReview?.explanation || "No explanation available for this question yet.")}</p></div>}
      {!reviewMode && showPracticeAids && <div className="confidence-row"><span>Confidence</span>{["low","medium","high"].map(level=><button type="button" key={level} className={confidence[q.id] === level ? "on" : ""} onClick={()=>onConfidence(level)}>{titleize(level)}</button>)}</div>}
      <ErrorBox error={error}/>
      <ExamFooter index={index} total={total} reviewMode={reviewMode} submitting={submitting} canReviewAnswer={canReviewAnswer} reviewLoading={reviewLoading} revealAnswer={revealAnswer} selectedCount={selectedForQuestion.length} flagged={flagged} onPrevious={onPrevious} onNext={onNext} onFlag={onToggleFlag} onReviewAnswer={onReviewAnswer} onSubmit={onSubmit} reportUrl={`/pmp-assessment/result/${attemptId}`}/>
    </div>
    <ExhibitViewer question={q}/>
  </section>;
}
function Exam() {
  const { attemptId } = useParams(); const nav = useNavigate();
  const [data, setData] = useState(null); const [index, setIndex] = useState(0); const [answers, setAnswers] = useState({}); const [flagged, setFlagged] = useState(new Set()); const [confidence, setConfidence] = useState({}); const [saveState, setSaveState] = useState("Saved"); const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false); const [submitWarning, setSubmitWarning] = useState(null); const [endWarning, setEndWarning] = useState(false); const [endingExam, setEndingExam] = useState(false); const [answerReviews, setAnswerReviews] = useState({}); const [reviewLoading, setReviewLoading] = useState(false); const [navFilter, setNavFilter] = useState("all"); const [navCollapsed, setNavCollapsed] = useState(false);
  const answersRef = useRef({});
  const flaggedRef = useRef(new Set());
  const indexRef = useRef(0);
  const pendingRef = useRef({});
  const inFlightRef = useRef({});
  const saveCounterRef = useRef(0);
  const submittingRef = useRef(false);
  const recoveryKey = `pmp_attempt_recovery_${attemptId}`;

  function readRecovery() {
    try {
      const raw = window.localStorage.getItem(recoveryKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return String(parsed.attemptId) === String(attemptId) ? parsed : null;
    } catch(e) {
      console.warn("Unable to read local exam recovery", e);
      return null;
    }
  }
  function writeRecovery(nextAnswers=answersRef.current, nextFlagged=flaggedRef.current, nextIndex=indexRef.current) {
    try {
      window.localStorage.setItem(recoveryKey, JSON.stringify({
        attemptId,
        answers: nextAnswers,
        flagged_question_ids: [...nextFlagged],
        current_question_index: nextIndex,
        pending: pendingRef.current,
        updated_at: Date.now()
      }));
    } catch(e) {
      console.warn("Unable to write local exam recovery", e);
    }
  }
  function clearRecovery() {
    try { window.localStorage.removeItem(recoveryKey); } catch(e) { console.warn("Unable to clear local exam recovery", e); }
  }
  function setIndexSafely(nextIndex) {
    const bounded = Math.max(0, Math.min(nextIndex, (data?.questions?.length || 1) - 1));
    indexRef.current = bounded;
    setIndex(bounded);
    if (data?.status === "in_progress") writeRecovery(undefined, undefined, bounded);
  }
  async function processPending(key) {
    if (inFlightRef.current[key]) return;
    inFlightRef.current[key] = true;
    try {
      while (pendingRef.current[key]) {
        const pending = pendingRef.current[key];
        setSaveState(navigator.onLine ? "Syncing..." : "Saved locally");
        await api.saveAnswer(attemptId, pending.questionId, pending.payload);
        if (pendingRef.current[key]?.version === pending.version) {
          delete pendingRef.current[key];
          writeRecovery();
        }
      }
      if (!Object.keys(pendingRef.current).length) setSaveState("Saved");
    } catch(e) {
      setSaveState(navigator.onLine ? "Sync failed" : "Saved locally");
      setError("Your answer is kept locally. It will sync when the connection is available.");
      console.error("Exam autosave failed", e);
    } finally {
      inFlightRef.current[key] = false;
    }
  }
  function queueSave(key, questionId, payload, nextAnswers=answersRef.current, nextFlagged=flaggedRef.current, nextIndex=indexRef.current) {
    const version = saveCounterRef.current + 1;
    saveCounterRef.current = version;
    pendingRef.current = {...pendingRef.current, [key]: {questionId, payload, version}};
    writeRecovery(nextAnswers, nextFlagged, nextIndex);
    setSaveState(navigator.onLine ? "Saving..." : "Saved locally");
    if (navigator.onLine) processPending(key);
  }
  function syncPending() {
    Object.keys(pendingRef.current).forEach(key=>processPending(key));
  }
  useEffect(()=>{
    let cancelled = false;
    api.questions(attemptId).then(x=>{
      if (cancelled) return;
      setData(x);
      if (x.status !== "in_progress") {
        clearRecovery();
        answersRef.current = x.answers || {};
        flaggedRef.current = new Set(x.flagged_question_ids || []);
        indexRef.current = x.current_question_index || 0;
        setAnswers(answersRef.current);
        setFlagged(flaggedRef.current);
        setIndex(indexRef.current);
        setSaveState("Saved");
        return;
      }
      const recovery = readRecovery();
      const recoveredAnswers = recovery?.answers ? {...(x.answers || {}), ...recovery.answers} : (x.answers || {});
      const recoveredFlagged = new Set(recovery?.flagged_question_ids || x.flagged_question_ids || []);
      const recoveredIndex = Number.isInteger(recovery?.current_question_index) ? recovery.current_question_index : (x.current_question_index || 0);
      pendingRef.current = recovery?.pending || {};
      answersRef.current = recoveredAnswers;
      flaggedRef.current = recoveredFlagged;
      indexRef.current = Math.max(0, Math.min(recoveredIndex, (x.questions?.length || 1) - 1));
      setAnswers(recoveredAnswers);
      setFlagged(recoveredFlagged);
      setIndex(indexRef.current);
      setSaveState(Object.keys(pendingRef.current).length ? "Saved locally" : "Saved");
      if (navigator.onLine && Object.keys(pendingRef.current).length) syncPending();
    }).catch(e=>{ if (isAuthError(e)) nav("/pmp-assessment"); else setError(e.message); });
    return ()=>{cancelled = true;};
  },[attemptId, nav]);
  useEffect(()=>{
    const sync = ()=>syncPending();
    window.addEventListener("online", sync);
    return ()=>window.removeEventListener("online", sync);
  }, [attemptId]);
  function questionIsCorrect(item) { return data?.status !== "in_progress" ? sameIds(answers[item.id] || [], item.correct_option_ids || []) : Boolean((answers[item.id] || []).length); }
  async function choose(q, optionId, checked) {
    if (data.status !== "in_progress") return;
    const current = answersRef.current[q.id] || [];
    const selected = q.question_type === "Multiple Response" ? (checked ? [...new Set([...current, optionId])] : current.filter(x=>x!==optionId)) : [optionId];
    const nextAnswers = {...answersRef.current, [q.id]: selected};
    answersRef.current = nextAnswers;
    setAnswers(nextAnswers);
    setError("");
    queueSave(`answer:${q.id}`, q.id, {selected_option_ids:selected, current_question_index:indexRef.current}, nextAnswers);
  }
  function toggleFlag(q) {
    if (data.status !== "in_progress") return;
    const nextFlagged = new Set(flaggedRef.current);
    const next = !nextFlagged.has(q.id);
    if (next) nextFlagged.add(q.id); else nextFlagged.delete(q.id);
    flaggedRef.current = nextFlagged;
    setFlagged(nextFlagged);
    setError("");
    queueSave(`flag:${q.id}`, q.id, {is_flagged:next, current_question_index:indexRef.current}, undefined, nextFlagged);
  }
  function jumpToFirst(type) {
    const target = data.questions.findIndex(item=>type === "flagged" ? flagged.has(item.id) : type === "incorrect" ? !questionIsCorrect(item) : !(answers[item.id] || []).length);
    if (target >= 0) setIndexSafely(target);
  }
  function markConfidence(level) {
    setConfidence({...confidence, [q.id]: level});
  }
  async function reviewCurrentAnswer() {
    if (!q || reviewMode || !(answers[q.id] || []).length) return;
    if (answerReviews[q.id]) return;
    setReviewLoading(true);
    setError("");
    try {
      const review = await api.reviewAnswer(attemptId, q.id);
      setAnswerReviews(current=>({...current, [q.id]: review}));
    } catch(e) {
      setError("Unable to review this answer right now. Please try again.");
      console.error("Question review error", e);
    } finally {
      setReviewLoading(false);
    }
  }
  async function submit(auto=false, confirmed=false) {
    if (data.status !== "in_progress" || submittingRef.current) return;
    const unanswered = data?.questions?.filter(q=>!(answers[q.id]||[]).length).length || 0;
    const flaggedCount = flagged.size;
    if(!auto && !confirmed) {
      setSubmitWarning({unanswered, flaggedCount, type: unanswered || flaggedCount ? "warning" : "confirm"});
      return;
    }
    setSubmitWarning(null);
    submittingRef.current = true;
    setSubmitting(true);
    if (Object.keys(pendingRef.current).length && navigator.onLine) {
      setSaveState("Syncing...");
      await Promise.allSettled(Object.keys(pendingRef.current).map(key=>processPending(key)));
    }
    try { await api.submit(attemptId); clearRecovery(); nav(`/pmp-assessment/result/${attemptId}`); }
    catch(e) { setError(e.message); setSubmitting(false); submittingRef.current = false; }
  }
  async function endExam() {
    if (data.status !== "in_progress" || endingExam) return;
    setEndingExam(true);
    setError("");
    try {
      await api.abandon(attemptId);
      pendingRef.current = {};
      clearRecovery();
      nav("/pmp-assessment/history", {replace:true});
    } catch(e) {
      setError(e.message || "Unable to end this exam right now.");
      setEndingExam(false);
    }
  }
  if (error && !data) return <Layout><ErrorBox error={error}/></Layout>;
  if (!data) return <Layout><Loading text="Preparing your assessment..." /></Layout>;
  const reviewMode = data.status !== "in_progress";
  const q = data.questions[index];
  const selectedForQuestion = answers[q.id] || [];
  const revealedReview = answerReviews[q.id];
  const revealAnswer = reviewMode || Boolean(revealedReview);
  const correctForQuestion = reviewMode ? (q.correct_option_ids || []) : (revealedReview?.correct_option_ids || []);
  const answeredCount = data.questions.filter(item=>(answers[item.id] || []).length).length;
  const unansweredCount = data.questions.length - answeredCount;
  const flaggedCount = flagged.size;
  const incorrectCount = reviewMode ? data.questions.filter(item=>!questionIsCorrect(item)).length : 0;
  const progress = Math.round(answeredCount * 100 / data.questions.length);
  const seriousExamModes = ["exam_simulator", ...practiceExamModes];
  const isSeriousExam = seriousExamModes.includes(data.attempt?.exam_mode);
  const showPracticeAids = !reviewMode && !isSeriousExam;
  return <div className={`exam-shell ${reviewMode ? "review-mode" : ""} ${isSeriousExam ? "serious-exam" : ""} ${navCollapsed ? "nav-collapsed" : ""}`}>
    <ExamHeader attempt={data.attempt} index={index} total={data.questions.length} reviewMode={reviewMode} saveState={saveState} submitting={submitting} flagged={flagged.has(q.id)} onFlag={()=>toggleFlag(q)} onSubmit={()=>submit(false)} onEndExam={()=>setEndWarning(true)} onReport={`/pmp-assessment/result/${attemptId}`} navCollapsed={navCollapsed} onToggleNavigator={()=>setNavCollapsed(value=>!value)} onExpire={()=>submit(true, true)} />
    <div className="exam-progress"><i style={{width:`${progress}%`}} /></div>
    <SubmitConfirmModal warning={submitWarning} submitting={submitting} onClose={()=>setSubmitWarning(null)} onReviewUnanswered={()=>{setSubmitWarning(null); jumpToFirst("unanswered");}} onSubmit={()=>submit(false, true)} />
    <EndExamModal open={endWarning} ending={endingExam} onClose={()=>setEndWarning(false)} onEnd={endExam} />
    <div className="exam-body">
      <QuestionNavigator questions={data.questions} index={index} answers={answers} flagged={flagged} confidence={confidence} answerReviews={answerReviews} reviewMode={reviewMode} questionIsCorrect={questionIsCorrect} filter={navFilter} onFilter={setNavFilter} collapsed={navCollapsed} onToggle={()=>setNavCollapsed(value=>!value)} onJump={setIndexSafely} answeredCount={answeredCount} unansweredCount={unansweredCount} incorrectCount={incorrectCount} flaggedCount={flaggedCount} progress={progress} />
      <QuestionRenderer q={q} index={index} reviewMode={reviewMode} showPracticeAids={showPracticeAids} revealAnswer={revealAnswer} selectedForQuestion={selectedForQuestion} correctForQuestion={correctForQuestion} revealedReview={revealedReview} confidence={confidence} canReviewAnswer={true} reviewLoading={reviewLoading} error={error} onChoose={choose} onToggleFlag={()=>toggleFlag(q)} onConfidence={markConfidence} onReviewAnswer={reviewCurrentAnswer} onPrevious={()=>setIndexSafely(index-1)} onNext={()=>setIndexSafely(index+1)} onSubmit={()=>submit(false)} submitting={submitting} total={data.questions.length} flagged={flagged.has(q.id)} attemptId={attemptId} />
    </div>
  </div>;
}
function ReviewAnswerCard({ item }) {
  const unanswered = String(item.selected_answer || "").toLowerCase() === "unanswered";
  return <article className={`review-answer-card ${item.is_flagged ? "flagged-review" : ""}`}>
    <div className="review-answer-top"><span className="review-domain-pill">{item.domain || "Unmapped"}</span>{item.is_flagged && <span className="review-flag-pill">Flagged</span>}</div>
    <h3>{item.question}</h3>
    <div className="review-answer-grid">
      <div className={unanswered ? "missed" : ""}><b>Your answer</b><p>{item.selected_answer}</p></div>
      <div className="correct"><b>Correct answer</b><p>{item.correct_answer}</p></div>
    </div>
    <div className="review-explain-box"><b>Why this works</b><p>{item.explanation}</p></div>
    <p className="mindset-note"><b>PMP thinking:</b> {pmpTrapHint(item)}</p>
  </article>;
}
function Result() {
  const { attemptId } = useParams();
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [selectedFocus, setSelectedFocus] = useState("all");
  const [attemptFilter, setAttemptFilter] = useState("all");
  const [selectedAttemptId, setSelectedAttemptId] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [reportError, setReportError] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportRequested, setReportRequested] = useState(false);

  async function generateAiReport(force=false) {
    setReportLoading(true); setReportError(""); setReportRequested(true);
    try { setReport(await generateReportOnce(attemptId, force)); }
    catch(e) { setReportError(e.message); }
    finally { setReportLoading(false); }
  }

  useEffect(()=>{
    let cancelled = false;
    setError(""); setReportError(""); setReport(null); setData(null); setReportRequested(false);
    api.result(attemptId)
      .then(result=>{ if (!cancelled) setData(result); })
      .catch(e=>{ if (!cancelled) setError(e.message); });
    api.report(attemptId)
      .then(existing=>{ if (!cancelled) { setReport(existing); setReportRequested(!!existing.learning_chapters); } })
      .catch(e=>{ if (!cancelled && e.status !== 404) setReportError(e.message); });
    return ()=>{ cancelled = true; };
  },[attemptId]);

  useEffect(()=>{
    if (data && !report && !reportLoading && !reportRequested && !error) generateAiReport(false);
    if (data && report && !report.learning_chapters && !reportLoading && !reportRequested && !error) generateAiReport(true);
  },[data, report, reportLoading, reportRequested, error]);

  if (error) return <Layout><ErrorBox error={error}/></Layout>;
  if (!data) return <Layout><Loading text="Calculating your result..." /></Layout>;
  const summary = report?.performance_summary || {};
  const profileContext = Object.fromEntries(Object.entries(report?.profile_context || {}).filter(([,value])=>value !== null && value !== undefined && String(value).trim() !== ""));
  return <Layout>
    <div className="result-top-actions">
      <Link className="button secondary" to="/pmp-assessment/history">Back to results</Link>
    </div>
    <div className="result-hero"><div><p className="eyebrow">ASSESSMENT COMPLETE</p><h1>{data.performance_level}</h1><p>Your result is ready. AI analysis starts automatically and turns this score into a focused study plan.</p></div><div className="big-score"><strong>{Math.round(data.score_percentage)}%</strong><span>overall score</span></div></div>
    <div className="stat-grid"><Stat label="Correct" value={data.correct_count}/><Stat label="Incorrect" value={data.incorrect_count}/><Stat label="Questions" value={data.total_questions}/></div>
    <section className="panel ai-report">
      <div className="ai-report-head"><div><p className="eyebrow">AI ANALYSIS</p><h2>Personal result coach</h2><p>The AI reviews your score, domain performance, wrong-answer themes, and profile context, then gives you next actions.</p></div><div className="ai-report-actions"><Link className="button secondary" to="/pmp-assessment/history">Back to results</Link><button onClick={()=>generateAiReport(!!report)} disabled={reportLoading}>{reportLoading ? "Generating..." : report?.learning_chapters ? "Regenerate chapters" : report ? "Add learning chapters" : "Retry AI analysis"}</button><Link className="button secondary" to={`/pmp-assessment/exam/${attemptId}`}>Review answers</Link>{report && <a className="button secondary" href={api.reportPdfUrl(attemptId)} target="_blank" rel="noreferrer">Preview PDF</a>}</div></div>
      <ErrorBox error={reportError}/>
      {reportLoading && <Loading text="AI is analysing your attempt..." />}
      {!reportLoading && !report && !reportError && <p className="muted">AI analysis will appear here automatically.</p>}
      {report && <div className="ai-report-body">
        <div className="ai-summary"><div><span>AI readiness</span><strong>{summary.performance_level || report.performance_level || data.performance_level}</strong></div><div><span>Score evidence</span><strong>{summary.score_percentage ?? Math.round(data.score_percentage)}%</strong></div></div>
        {report.profile_report_stale && <div className="error">Your profile changed after this AI analysis. Regenerate chapters to rebuild the coaching with your latest profile.</div>}
        <ProfileContextSummary context={profileContext} />
        <p className="ai-overview">{report.overall_summary}</p>
        <div className="ai-two-col"><ReportSection title="Strengths" value={report.strengths} compact/><ReportSection title="Weak areas" value={report.weak_areas} compact/></div>
        <ReportSection title="Wrong answer themes" value={report.wrong_answer_analysis?.common_themes || report.wrong_answer_analysis} />
        <ReportSection title="Coaching examples" value={report.wrong_answer_analysis?.examples} />
        <ReportSection title="Study recommendations" value={report.study_recommendations} />
        <ReportSection title="Personal Study Chapters" value={report.learning_chapters} />
        <ReportSection title="Personalised study plan" value={report.personalised_study_plan} />
        <ReportSection title="Exam strategy" value={report.exam_strategy_advice} />
        {report.final_advice && <div className="ai-final"><b>Final advice</b><p>{reportText(report.final_advice)}</p></div>}
      </div>}
    </section>
    <section className="panel"><h2>Domain performance</h2><div className="question-list">{data.domain_breakdown.map(d=><article key={d.domain}><span>{d.risk_level} risk</span><h3>{d.domain}: {Math.round(d.score_percentage)}%</h3><p>{d.correct_answers} correct of {d.total_questions}</p></article>)}</div></section>
    <div className="result-actions"><Link className="button secondary" to="/pmp-assessment/history">Back to results</Link><Link className="button" to="/pmp-assessment/practice">Practice Center</Link></div>
  </Layout>;
}
function History() {
  const nav = useNavigate();
  const [attempts, setAttempts] = useState([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  useEffect(()=>{api.attempts().then(rows=>{setAttempts(rows); setError("");}).catch(e=>{ if (isAuthError(e)) nav("/pmp-assessment"); else setError(e.message); }).finally(()=>setLoading(false));},[nav]);
  const completed = attempts.filter(a=>a.status !== "in_progress" && a.score_percentage !== null && a.score_percentage !== undefined);
  const active = attempts.filter(a=>a.status === "in_progress");
  const chronological = [...completed].sort((a,b)=>new Date(a.submitted_at || a.started_at || 0) - new Date(b.submitted_at || b.started_at || 0));
  const recentTrend = chronological.slice(-8);
  const scores = completed.map(a=>Number(a.score_percentage || 0));
  const average = scores.length ? Math.round(scores.reduce((sum,score)=>sum+score,0)/scores.length) : 0;
  const best = scores.length ? Math.round(Math.max(...scores)) : 0;
  const firstScore = chronological[0]?.score_percentage;
  const latestScore = chronological[chronological.length-1]?.score_percentage;
  const movement = firstScore !== undefined && latestScore !== undefined ? Math.round(latestScore - firstScore) : 0;
  const domainRows = Object.entries(completed.reduce((acc,a)=>{ const key=attemptLabel(a); const item=acc[key] || {count:0,total:0,best:0}; const score=Number(a.score_percentage || 0); item.count += 1; item.total += score; item.best = Math.max(item.best, score); acc[key]=item; return acc; },{})).map(([name,item])=>({name,count:item.count,average:Math.round(item.total/item.count),best:Math.round(item.best)})).sort((a,b)=>b.average-a.average);
  const chartPoints = recentTrend.map((a,index)=>{ const x = recentTrend.length === 1 ? 200 : 24 + (index * (352/(recentTrend.length-1))); const y = 136 - (Number(a.score_percentage || 0) * 1.12); return `${x},${Math.max(20, Math.min(136, y))}`; }).join(" ");
  const latestAttempt = attempts[0];
  const statusText = completed.length ? `${completed.length} completed, ${active.length} in progress` : active.length ? `${active.length} in progress` : "No scored attempts yet";
  function removeAttemptFromHistory(attemptId) {
    setAttempts(current=>current.filter(attempt=>String(attempt.id) !== String(attemptId)));
  }
  if (loading) return <Layout><Loading text="Loading your progress..." /></Layout>;
  return <Layout><div className="page-head history-head"><p className="eyebrow">YOUR ACTIVITY</p><h1>Attempt history</h1><p>Track score movement, domain practice, and unfinished attempts from one place.</p></div><ErrorBox error={error}/>{attempts.length ? <><section className="history-summary"><article className="history-hero-card"><span>Progress snapshot</span><strong>{completed.length ? `${best}% best score` : "Keep going"}</strong><p>{completed.length ? `Average score is ${average}%. ${movement >= 0 ? "+" : ""}${movement}% movement from first to latest completed attempt.` : "Complete an assessment to unlock score trend charts."}</p></article><Stat label="Attempts" value={attempts.length}/><Stat label="Completed" value={completed.length}/><Stat label="Average" value={completed.length ? `${average}%` : "-"}/><Stat label="Active" value={active.length}/></section><section className="history-grid"><article className="panel history-chart"><div className="history-panel-head"><div><p className="eyebrow">SCORE TREND</p><h2>Readiness over time</h2></div><span>{statusText}</span></div>{recentTrend.length ? <svg viewBox="0 0 400 170" role="img" aria-label="Score trend chart"><line x1="24" y1="24" x2="24" y2="140"/><line x1="24" y1="140" x2="380" y2="140"/><polyline points={chartPoints}/>{recentTrend.map((a,index)=>{ const [x,y]=chartPoints.split(" ")[index].split(","); return <g key={a.id}><circle cx={x} cy={y} r="5"/><text x={x} y={Number(y)-10}>{Math.round(a.score_percentage)}%</text></g>; })}</svg> : <p className="muted">No completed attempts yet.</p>}</article><article className="panel history-focus"><div className="history-panel-head"><div><p className="eyebrow">DOMAIN SIGNALS</p><h2>Practice performance</h2></div></div>{domainRows.length ? <div className="domain-progress-list">{domainRows.map(row=><div key={row.name}><div><strong>{row.name}</strong><span>{row.average}% avg | {row.count} attempt{row.count === 1 ? "" : "s"}</span></div><i><b style={{width:`${Math.min(100,row.average)}%`}} /></i></div>)}</div> : <p className="muted">Domain charts appear after completed attempts.</p>}</article></section><section className="panel history-list-panel"><div className="history-panel-head"><div><p className="eyebrow">ATTEMPT LOG</p><h2>Recent activity</h2></div>{latestAttempt && <span>Latest: {attemptLabel(latestAttempt)}</span>}</div><div className="history-attempt-list">{attempts.map(a=><article key={a.id} className={attemptPrimaryPath(a) ? "clickable-attempt" : ""} onClick={()=>{ const path = attemptPrimaryPath(a); if (path) nav(path); }}><div><span>{attemptLabel(a)}</span><h3>{attemptScoreTitle(a)}</h3><p>{a.question_count} questions | {a.duration_minutes} minutes | {a.started_at ? new Date(a.started_at).toLocaleString() : "Not started"}</p></div><div className="attempt-score-pill"><b>{a.status === "in_progress" ? `${a.current_question_index || 0}/${a.question_count}` : isScoredAttempt(a) ? `${a.correct_count || 0}/${a.question_count}` : "-"}</b><small>{a.status === "in_progress" ? "answered" : isScoredAttempt(a) ? "correct" : "not scored"}</small></div><AttemptActions attempt={a} onDelete={removeAttemptFromHistory}/></article>)}</div></section></> : <section className="panel history-empty"><h2>No attempts yet</h2><p className="muted">Start a practice session to build your progress chart.</p><Link className="button" to="/pmp-assessment/dashboard">View Dashboard</Link></section>}</Layout>;
}

function Profile() {
  const nav = useNavigate();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [editing, setEditing] = useState(false);
  useEffect(()=>{api.me().then(x=>setProfile(x.profile || x)).catch(e=>{ if (isAuthError(e)) nav("/pmp-assessment"); else setError(e.message); });},[nav]);
  const profileIsComplete = current=>Boolean(current?.profile_completed || [current?.full_name || current?.name, current?.job_title, current?.company_name, current?.industry, current?.country].every(value=>String(value || "").trim()));
  async function submit(e) {
    e.preventDefault(); setError(""); setSaved(false);
    try {
      const updated = await api.updateMe(profile);
      const next = updated.profile || updated;
      setProfile(next); setSaved(true);
      if (profileIsComplete(next)) setEditing(false);
    } catch(e) { setError(e.message); }
  }
  if (error && !profile) return <Layout><ErrorBox error={error}/></Layout>;
  if (!profile) return <Layout><Loading /></Layout>;
  const set = (key, value)=>setProfile({...profile, [key]: value});
  const complete = profileIsComplete(profile);
  const displayName = profile.full_name || profile.name || "PMP learner";
  const initials = displayName.split(" ").filter(Boolean).slice(0,2).map(part=>part[0]).join("").toUpperCase() || "PM";
  const roleLine = [profile.job_title, profile.company_name].filter(Boolean).join(" at ");
  const details = [
    ["Industry", profile.industry],
    ["Experience", profile.years_project_experience ? `${profile.years_project_experience} year${Number(profile.years_project_experience) === 1 ? "" : "s"}` : profile.experience_level],
    ["Country", profile.country],
    ["Learner type", profile.user_type === "KBC_LEARNER" ? "KBC learner" : "External candidate"],
  ].filter(([,value])=>String(value || "").trim());
  const showForm = editing || !complete;
  return <Layout><div className="page-head profile-page-head"><p className="eyebrow">PROFILE</p><h1>Your PMP profile</h1><p>{complete ? "Your professional context is ready for personalised reports." : profile.user_type === "KBC_LEARNER" ? `KBC learner: ${profile.programme || "programme pending"}` : "Complete your professional context once, then reports can use it."}</p></div>{!showForm ? <section className="panel profile-card"><div className="profile-card-head"><div className="profile-avatar">{initials}</div><div><p className="eyebrow">PROFILE READY</p><h2>{displayName}</h2>{roleLine && <p>{roleLine}</p>}</div><button onClick={()=>{setEditing(true); setSaved(false);}}>Edit profile</button></div><div className="profile-details">{details.map(([label,value])=><div className="profile-detail" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>{profile.marketing_consent && profile.apprenticeship_interest && <div className="profile-note apprenticeship-note"><span>Apprenticeship interest</span><p>You opted in to receive apprenticeship and career opportunity updates. You can turn this off from Edit profile.</p></div>}{profile.role_description && <div className="profile-note"><span>Role context</span><p>{profile.role_description}</p></div>}<div className="profile-footer-actions">{profile.linkedin_url && <a className="button secondary" href={profile.linkedin_url} target="_blank" rel="noreferrer">Open LinkedIn</a>}<Link className="button" to="/pmp-assessment/dashboard">View dashboard</Link></div></section> : <form className="panel form-grid" onSubmit={submit}><label className="wide">Full name<input value={profile.full_name || profile.name || ""} onChange={e=>set("full_name", e.target.value)} /></label><label>Job title<input value={profile.job_title || ""} onChange={e=>set("job_title", e.target.value)} /></label><label>Company<input value={profile.company_name || ""} onChange={e=>set("company_name", e.target.value)} /></label><label>Industry<input value={profile.industry || ""} onChange={e=>set("industry", e.target.value)} /></label><label>Experience level<input value={profile.experience_level || ""} onChange={e=>set("experience_level", e.target.value)} /></label><label>Years of project experience<input type="number" step="0.5" min="0" value={profile.years_project_experience || ""} onChange={e=>set("years_project_experience", e.target.value)} /></label><label>Country<input value={profile.country || ""} onChange={e=>set("country", e.target.value)} /></label><label className="wide">LinkedIn URL<input value={profile.linkedin_url || ""} onChange={e=>set("linkedin_url", e.target.value)} /></label><label className="wide">Role description<textarea rows="4" value={profile.role_description || ""} onChange={e=>set("role_description", e.target.value)} /></label><label className="wide check consent-check"><input type="checkbox" checked={Boolean(profile.apprenticeship_interest && profile.marketing_consent)} onChange={e=>setProfile({...profile, apprenticeship_interest:e.target.checked, marketing_consent:e.target.checked, preferred_contact:e.target.checked ? (profile.preferred_contact || "email") : profile.preferred_contact})} /><span>I am interested in apprenticeship and career opportunity updates. You may contact me about relevant programmes, and I can opt out later.</span></label><ErrorBox error={error}/>{saved && <div className="success">Profile saved.</div>}<button>Save profile</button>{complete && <button type="button" className="secondary" onClick={()=>setEditing(false)}>Cancel</button>}</form>}</Layout>;
}
function AdminUsers() {
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState("");
  useEffect(()=>{ api.adminProfiles("").then(setProfiles).catch(e=>setError(e.message)); },[]);
  return <Layout admin><div className="page-head"><p className="eyebrow">ADMINISTRATION</p><h1>Learners</h1><p>Registered learner profiles and account status.</p></div><ErrorBox error={error}/><section className="panel"><h2>Users</h2><div className="question-list">{profiles.map(profile=><article key={profile.id}><span>{profile.user_type || "Learner"} | {profile.status || "active"}</span><h3>{profile.full_name || profile.name || profile.email}</h3><small>{profile.email}{profile.programme ? ` | ${profile.programme}` : ""}{profile.cohort ? ` | ${profile.cohort}` : ""}</small></article>)}</div>{!profiles.length && !error && <p className="muted">No learner profiles found.</p>}</section></Layout>;
}
function AdminReports() {
  const [leads, setLeads] = useState([]);
  const [error, setError] = useState("");
  useEffect(()=>{ api.salesLeads().then(setLeads).catch(e=>setError(e.message)); },[]);
  return <Layout admin><div className="page-head"><p className="eyebrow">ADMINISTRATION</p><h1>Reports</h1><p>Apprenticeship-ready learner report signals.</p></div><ErrorBox error={error}/><section className="panel"><h2>Sales leads</h2><div className="question-list">{leads.map(lead=><article key={lead.id}><span>Lead score {lead.lead_score} | {lead.completed_attempts} completed</span><h3>{lead.name || lead.email}</h3><small>{lead.email} | Best {lead.best_score ?? "-"}% | Latest {lead.latest_score ?? "-"}% | {lead.recommended_offer}</small></article>)}</div>{!leads.length && !error && <p className="muted">No report leads found.</p>}</section></Layout>;
}
function AdminDomains() {
  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  useEffect(()=>{ Promise.all([api.domains(), api.topics()]).then(([domainRows, topicRows])=>{setDomains(domainRows); setTopics(topicRows);}).catch(e=>setError(e.message)); },[]);
  return <Layout admin><div className="page-head"><p className="eyebrow">ADMINISTRATION</p><h1>Domains</h1><p>Performance domains and topic coverage.</p></div><ErrorBox error={error}/><section className="panel"><h2>Performance domains</h2><div className="domain-counter-grid">{domains.map(domain=><article key={domain.id} className="ready"><span>{domain.name}</span><strong>{topics.filter(topic=>topic.domain === domain.id).length}</strong><small>topics</small></article>)}</div>{!domains.length && !error && <p className="muted">No domains found.</p>}</section></Layout>;
}
function QuestionBank() {
  const [questions, setQuestions] = useState([]); const [stats, setStats] = useState(null); const [error, setError] = useState(""); const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({performance_domain:"", methodology:"", question_type:"", source:"", active:""});
  async function load() { try { const params = new URLSearchParams(); if(search) params.set("search", search); Object.entries(filters).forEach(([k,v])=>v&&params.set(k,v)); const [qs, st] = await Promise.all([api.adminQuestions(params.toString()), api.questionBankStats()]); setQuestions(qs); setStats(st); setError(""); } catch(e) { setError(e.message); } }
  useEffect(()=>{load();},[]);
  return <Layout admin><div className="page-head"><p className="eyebrow">ADMINISTRATION</p><h1>PMP question bank</h1><p>Counts show all active valid unique production questions. A domain is exam ready when it has at least 40.</p></div>{stats && <section className="panel bank-readiness"><div className="bank-status-line"><div><span>Total active questions</span><strong>{stats.total}</strong></div><b className={stats.ready?"ready":"not-ready"}>Bank Status: {stats.ready ? "Exam Ready" : "Not Ready"}</b></div><div className="domain-counter-grid">{stats.domains.map(d=><article className={d.ready?"ready":"missing"} key={d.name}><span>{d.name}</span><strong>{d.count}</strong><small>{d.ready ? "Exam ready" : `Needs ${d.missing} more`}</small></article>)}</div></section>}<section className="panel"><h2>Questions</h2><div className="filter-grid"><input placeholder="Search" value={search} onChange={e=>setSearch(e.target.value)} /><select value={filters.performance_domain} onChange={e=>setFilters({...filters,performance_domain:e.target.value})}><option value="">Domain</option>{performanceDomains.map(x=><option key={x}>{x}</option>)}</select><select value={filters.methodology} onChange={e=>setFilters({...filters,methodology:e.target.value})}><option value="">Methodology</option>{methodologies.map(x=><option key={x}>{x}</option>)}</select><select value={filters.question_type} onChange={e=>setFilters({...filters,question_type:e.target.value})}><option value="">Question Type</option>{questionTypes.map(x=><option key={x}>{x}</option>)}</select><input placeholder="Source" value={filters.source} onChange={e=>setFilters({...filters,source:e.target.value})}/><select value={filters.active} onChange={e=>setFilters({...filters,active:e.target.value})}><option value="">Active / Inactive</option><option value="true">Active</option><option value="false">Inactive</option></select><button onClick={load}>Apply</button></div><ErrorBox error={error}/><div className="question-list">{questions.map(q=><article key={q.id}><span>{q.performance_domain || "Needs mapping"} | {q.methodology} | {q.question_type}</span><h3>{q.question_text}</h3><small>{q.source_file ? "Imported mock question" : "No source"}{q.is_synthetic ? " | synthetic" : ""}</small></article>)}</div></section></Layout>;
}

export default function App() {
  return <Routes><Route path="/pmp-assessment" element={<Auth/>}/><Route path="/pmp-assessment/dashboard" element={<Dashboard/>}/><Route path="/pmp-assessment/practice" element={<Practice/>}/><Route path="/pmp-assessment/exam/:attemptId" element={<Exam/>}/><Route path="/pmp-assessment/result/:attemptId" element={<Result/>}/><Route path="/pmp-assessment/history" element={<History/>}/><Route path="/pmp-assessment/profile" element={<Profile/>}/><Route path="/admin/pmp-question-bank" element={<QuestionBank/>}/><Route path="/admin/pmp-users" element={<AdminUsers/>}/><Route path="/admin/pmp-reports" element={<AdminReports/>}/><Route path="/admin/pmp-domains" element={<AdminDomains/>}/><Route path="*" element={<Auth/>}/></Routes>;
}
