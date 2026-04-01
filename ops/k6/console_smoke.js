import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 smoke for Console API (read-only).
// Purpose: quick perf regression check (p95 + error rate) on hot endpoints.
// Modes:
// - PR non-prod smoke via CONSOLE_K6_PR_* secrets
// - manual live smoke via workflow_dispatch
// - nightly live smoke via schedule
// Safety: no mutations; keep low VUs/iterations.
// Env:
// - CONSOLE_API_URL
// - CONSOLE_API_TOKEN
// - optional X-Company-Id / X-Client-Id / X-Branch-Id via env
//   CONSOLE_API_COMPANY_ID / CONSOLE_API_CLIENT_ID / CONSOLE_API_BRANCH_ID

const baseUrl = __ENV.CONSOLE_API_URL || 'https://api.truffles.kz/console/v1';
const token = __ENV.CONSOLE_API_TOKEN;

if (!token) {
  throw new Error('CONSOLE_API_TOKEN is required');
}

const headers = {
  Authorization: `Bearer ${token}`,
  'Content-Type': 'application/json',
};

if (__ENV.CONSOLE_API_COMPANY_ID) {
  headers['X-Company-Id'] = __ENV.CONSOLE_API_COMPANY_ID;
}

if (__ENV.CONSOLE_API_CLIENT_ID) {
  headers['X-Client-Id'] = __ENV.CONSOLE_API_CLIENT_ID;
}

if (__ENV.CONSOLE_API_BRANCH_ID) {
  headers['X-Branch-Id'] = __ENV.CONSOLE_API_BRANCH_ID;
}

export const options = {
  vus: 1,
  iterations: 5,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<600'],
  },
};

export default function () {
  let res = http.get(`${baseUrl}/me`, { headers });
  check(res, {
    'me: status 200': (r) => r.status === 200,
  });

  res = http.get(`${baseUrl}/cases?limit=5`, { headers });
  check(res, {
    'cases: status 200': (r) => r.status === 200,
  });

  sleep(1);
}
