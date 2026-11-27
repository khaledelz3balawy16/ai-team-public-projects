import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch, setToken, type LoginResponse } from "../api";
import { InclusionLoading } from "../components/InclusionLoading";

export default function LMSCallbackPage() {
  const started = useRef(false);
  const [payload] = useState(() => ({
    assertion: new URLSearchParams(window.location.hash.slice(1)).get("assertion"),
    verifier: sessionStorage.getItem("lms_sso_verifier"),
  }));
  const [error, setError] = useState(() => payload.assertion && payload.verifier ? "" : "This sign-in link has expired. Please start again.");
  const navigate = useNavigate();
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const { assertion, verifier } = payload;
    window.history.replaceState(null, "", window.location.pathname);
    sessionStorage.removeItem("lms_sso_verifier");
    if (!assertion || !verifier) {
      return;
    }
    apiFetch<LoginResponse>("/auth/lms/complete/", {
      method: "POST", body: JSON.stringify({ assertion, verifier }),
    }).then(data => {
      setToken(data.token);
      localStorage.setItem("learner_email", data.learner.email);
      localStorage.removeItem("admin_email");
      localStorage.removeItem("admin_name");
      localStorage.removeItem("admin_token");
      navigate(data.next_route, { replace: true });
    }).catch(err => setError(err instanceof Error ? err.message : "Sign-in failed."));
  }, [navigate, payload]);
  if (!error) return <InclusionLoading />;
  return <div className="page"><div className="card">
    <h1>Wellbeing &amp; Safeguarding</h1>
    {error ? <><p className="error">{error}</p><Link to="/">Sign in again</Link></> : <p>Completing LMS sign-in…</p>}
  </div></div>;
}
