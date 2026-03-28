const API_BASE = import.meta.env.VITE_API_URL || '/api';

function parseResponseBody(text, res) {
  if (!text) {
    throw new Error(
      `Empty response (HTTP ${res.status}). Is the backend running at http://127.0.0.1:8000?`
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(text.slice(0, 200) || `HTTP ${res.status} ${res.statusText}`);
  }
}

async function parseJson(res) {
  const text = await res.text();
  const data = parseResponseBody(text, res);
  if (!res.ok) {
    const d = data?.detail;
    if (Array.isArray(d)) throw new Error(d.map((x) => x.msg || String(x)).join(', '));
    if (typeof d === 'string') throw new Error(d);
    throw new Error(JSON.stringify(data));
  }
  return data;
}

async function fetchApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  return parseJson(res);
}

async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const data = parseResponseBody(text, res);
  if (!res.ok) {
    const d = data?.detail;
    if (Array.isArray(d)) throw new Error(d.map((x) => x.msg || String(x)).join(', '));
    if (typeof d === 'string') throw new Error(d);
    throw new Error(typeof data?.message === 'string' ? data.message : JSON.stringify(data));
  }
  return data;
}

export const api = {
  getGlobalModel: () => fetchApi('/get_global_model'),
  trustHistory: () => fetchApi('/trust_history'),
  currentTrust: () => fetchApi('/current_trust'),
  ganacheAccountsTrust: (limit = 10) => fetchApi(`/ganache_accounts_trust?limit=${limit}`),
  clientsSnapshot: () => fetchApi('/clients_snapshot'),
  aggregate: () => postJson('/aggregate', {}),

  upwork: {
    createJob: (payload) => postJson('/upwork/job/create', payload),
    submitProof: (payload) => postJson('/upwork/job/submit_proof', payload),
    runAi: (jobId) => postJson('/upwork/job/run_ai', { job_id: jobId }),
    approve: (jobId, clientIndex) => postJson('/upwork/job/approve', { job_id: jobId, client_index: clientIndex }),
    dispute: (jobId, clientIndex) => postJson('/upwork/job/dispute', { job_id: jobId, client_index: clientIndex }),
    status: (jobId) => fetchApi(`/upwork/job/status?job_id=${jobId}`),
  },

  auth: {
    signup: (payload) => postJson('/auth/signup', payload),
    login: (payload) => postJson('/auth/login', payload),
  },
};
