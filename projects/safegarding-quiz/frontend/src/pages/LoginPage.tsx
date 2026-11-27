import { type FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, type LoginResponse, setToken } from "../api";
import { InclusionLoading } from "../components/InclusionLoading";

export default function LoginPage() {
  const [email, setEmail] = useState<string>("");
  const [error, setError] = useState<string>("");
  const navigate = useNavigate();
  const [lmsEnabled, setLmsEnabled] = useState<boolean | null>(null);
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    apiFetch<{ enabled: boolean }>("/auth/lms/config/").then(async config => {
      setLmsEnabled(config.enabled);
      if (config.enabled) {
        const data = await apiFetch<{ verifier: string; url: string }>("/auth/lms/start/", { method: "POST" });
        sessionStorage.setItem("lms_sso_verifier", data.verifier);
        window.location.replace(data.url);
      }
    }).catch(err => setError(err instanceof Error ? err.message : "Could not start sign-in."));
  }, []);

  if (lmsEnabled !== false && !error) return <InclusionLoading />;
  if (lmsEnabled !== false) return <div className="page"><div className="card">
    <img src="/kbc-logo.png" alt="Kent Business College" className="login-logo" />
    <h1>Wellbeing &amp; Safeguarding</h1>
    {error ? <><p className="error">{error}</p><button onClick={() => window.location.reload()}>Try again</button></> : <p>Taking you to LMS sign-in…</p>}
  </div></div>;

  const handleLogin = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    try {
      const data = await apiFetch<LoginResponse>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email }),
      });

      setToken(data.token);
      localStorage.setItem("learner_email", data.learner?.email ?? email);
      navigate(data.next_route || "/onboarding");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <div className="login-logo-wrap">
          <img src="/kbc-logo.png" alt="Kent Business College" className="login-logo" />
        </div>
        <h1>Wellbeing & Safeguarding Login</h1>
        <p>Please enter your Aptem learner email to log in.</p>

        <form onSubmit={handleLogin}>
          <input
            type="email"
            placeholder="Enter your Aptem learner email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit">Login</button>
        </form>

        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
