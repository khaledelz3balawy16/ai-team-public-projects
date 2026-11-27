import { Dashboard } from './pages/Dashboard';

const KENT_SITE_URL = 'https://www.kentbusinesscollege.org';
const LEARNER_EMAIL_PARAMS = ['email', 'aptem_email'];

function getLearnerEmail(): string {
  if (typeof window === 'undefined') return '';
  const params = new URLSearchParams(window.location.search);
  return LEARNER_EMAIL_PARAMS
    .map(key => params.get(key)?.trim())
    .find(Boolean) ?? '';
}

export default function App() {
  // The dashboard is only reachable via the "Login to Student Dashboard"
  // redirect, which carries the learner's email in the URL. Without an email,
  // send the visitor back to the main Kent site in production.
  if (!import.meta.env.DEV && !getLearnerEmail()) {
    if (typeof window !== 'undefined') {
      window.location.replace(KENT_SITE_URL);
    }
    return null;
  }

  return <Dashboard />;
}
