import http from 'k6/http';
import { check, sleep } from 'k6';

// k6 smoke for Console API (read-only).
// Purpose: quick perf regression check (p95 + error rate) on hot endpoints.
// Safety: no mutations; keep low VUs/iterations; prefer staging when possible.
// Env: CONSOLE_API_URL, CONSOLE_API_TOKEN (bearer).

const baseUrl = __ENV.CONSOLE_API_URL || 'https://api.truffles.kz/console/v1';
const token = __ENV.CONSOLE_API_TOKEN;

if (!token) {
  throw new Error('CONSOLE_API_TOKEN is required');
}

const headers = {
  Authorization: `Bearer ${token}`,
  'Content-Type': 'application/json',
};

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
