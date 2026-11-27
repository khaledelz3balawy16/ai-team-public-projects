// ------------------------------------------------------------
// LMS load test: 200 virtual users browsing as one signed-in learner.
//
//   BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh
//
// Both the VPS and AWS sites use the PRODUCTION database, so:
//   - sign in ONCE (setup) and share that session: no 200 login rows,
//     no per-IP login throttle, no account lockout
//   - read-only GETs only
//   - ramp up gradually and abort early if errors or latency climb
//   - never run against both sites at the same time
// ------------------------------------------------------------
import http from 'k6/http';
import { check, fail, sleep } from 'k6';

const BASE = (__ENV.BASE_URL || '').replace(/\/$/, '');
const PEAK = Number(__ENV.PEAK_VUS || 200);

export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: Math.round(PEAK / 4) },
        { duration: __ENV.RAMP || '2m', target: PEAK }, // longer for big peaks, so auto scaling can keep up
        { duration: __ENV.HOLD || '3m', target: PEAK }, // longer to watch auto scaling react
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    // Stop the test (to protect live learners) if it starts failing
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '30s' }],
    'http_req_duration{kind:api}': [{ threshold: 'p(95)<5000', abortOnFail: true, delayAbortEval: '30s' }],
    // Report-only targets
    'http_req_duration{kind:page}': ['p(95)<1000'],
    checks: ['rate>0.95'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  userAgent: 'kbc-lms-loadtest/1.0 (k6)',
};

const XHR = { 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' };

export function setup() {
  if (!BASE) fail('BASE_URL is not set');
  if (!__ENV.LOADTEST_EMAIL || !__ENV.LOADTEST_PASSWORD) fail('LOADTEST_EMAIL / LOADTEST_PASSWORD are not set');

  const res = http.post(
    `${BASE}/login_api/login/`,
    JSON.stringify({ email: __ENV.LOADTEST_EMAIL, password: __ENV.LOADTEST_PASSWORD }),
    { headers: XHR, tags: { name: 'login' } },
  );
  if (res.status !== 200) fail(`login failed: HTTP ${res.status}`);

  const cookie = res.cookies.kbc_session && res.cookies.kbc_session[0];
  if (!cookie) fail('login returned no kbc_session cookie');
  const user = res.json('user');

  const paths = ['/login_api/me/'];
  if (user.subjectType === 'learner') {
    const learner = `${user.learnerType || 'commercial'}/${user.subjectId}`;
    paths.push(
      `/learner_api/dashboard/${learner}/header/minimal/`,
      `/learner_api/training-plan-dashboard/${learner}/?section=overview`,
      `/learner_api/training-plan-dashboard/${learner}/?section=upcoming`,
      `/learner_api/my-learning/${learner}/`,
      `/learner_api/attendance/${learner}/lectures/`,
    );
  }
  console.log(`signed in as role=${user.role} subject=${user.subjectType}; ${paths.length} API paths per iteration`);
  return { session: cookie.value, paths };
}

export default function (data) {
  const auth = { headers: { ...XHR, Cookie: `kbc_session=${data.session}` } };

  // The page itself (CloudFront/S3 on AWS, the VPS web server on the VPS)
  const page = http.get(`${BASE}/learner/home`, { tags: { kind: 'page', name: 'page /learner/home' } });
  check(page, { 'page 200': (r) => r.status === 200 });

  // The API calls the learner home makes after it loads
  const responses = http.batch(
    data.paths.map((p) => ['GET', `${BASE}${p}`, null, { ...auth, tags: { kind: 'api', name: p.replace(/\/\d+\//, '/{id}/') } }]),
  );
  responses.forEach((r) => check(r, { 'api 200': (x) => x.status === 200 }));

  sleep(1 + Math.random() * 2); // think time between page views
}

export function teardown(data) {
  // End the shared session so it doesn't stay valid in production
  http.post(`${BASE}/login_api/logout/`, null, { headers: { ...XHR, Cookie: `kbc_session=${data.session}` } });
}
