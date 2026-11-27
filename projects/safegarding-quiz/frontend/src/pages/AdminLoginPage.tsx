import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE, apiFetch } from "../api";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    apiFetch<{ enabled: boolean }>("/auth/lms/config/").then(config => {
      if (config.enabled) navigate("/", { replace: true });
      else setReady(true);
    }).catch(() => setError("Could not load sign-in. Please refresh and try again."));
  }, [navigate]);
  if (!ready) return <div className="page"><div className="card"><p>{error || "Loading sign-in…"}</p></div></div>;
  const handleMicrosoftLogin = () => {
    window.location.href = `${API_BASE}/admin/auth/microsoft/start/`;
  };

  return (
    <div className="admin-login-page">
      <main className="admin-login-shell">
        <section className="admin-login-panel">
          <div className="admin-login-brand">
            <img src="/kbc-logo.png" alt="Kent Business College" />
            <div>
              <span>Staff access</span>
              <h1>KBC Admin Login</h1>
            </div>
          </div>

          <button
            className="admin-ms-btn admin-ms-btn-primary"
            type="button"
            onClick={handleMicrosoftLogin}
          >
            <ShieldCheck size={18} aria-hidden="true" />
            Continue with Microsoft Teams
          </button>
        </section>
      </main>
    </div>
  );
}
