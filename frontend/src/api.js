const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function parseJson(res) {
  const text = await res.text();
  if (!text) {
    throw new Error(`Empty response (status ${res.status}). Backend running at http://127.0.0.1:8000?`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON: ${text.slice(0, 150)}`);
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders(), ...options.headers },
  });
  return parseJson(res);
}

async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  return parseJson(res);
}

async function putJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  return parseJson(res);
}

export const api = {
  // FL Demo endpoints
  getGlobalModel: () => fetchApi('/get_global_model'),
  trustHistory: () => fetchApi('/trust_history'),
  currentTrust: () => fetchApi('/current_trust'),
  ganacheAccountsTrust: (limit = 10) => fetchApi(`/ganache_accounts_trust?limit=${limit}`),
  clientsSnapshot: () => fetchApi('/clients_snapshot'),
  aggregate: () => postJson('/aggregate', {}),
  modelMetrics: () => fetchApi('/model_metrics'),

  // Upwork Job Workflow (demo)
  upwork: {
    createJob: (payload) => postJson('/upwork/job/create', payload),
    submitProof: (payload) => postJson('/upwork/job/submit_proof', payload),
    runAi: (jobId) => postJson('/upwork/job/run_ai', { job_id: jobId }),
    approve: (jobId, clientIndex) => postJson('/upwork/job/approve', { job_id: jobId, client_index: clientIndex }),
    dispute: (jobId, clientIndex) => postJson('/upwork/job/dispute', { job_id: jobId, client_index: clientIndex }),
    status: (jobId) => fetchApi(`/upwork/job/status?job_id=${jobId}`),
  },

  // Auth
  auth: {
    signup: (payload) => postJson('/auth/signup', payload),
    login: (payload) => postJson('/auth/login', payload),
  },

  // User Profile
  user: {
    profile: () => fetchApi('/user/profile'),
    publicProfile: (userId) => fetchApi(`/user/profile/${userId}`),
    updateProfile: (payload) => putJson('/user/profile', payload),
    linkWallet: (walletAddress) => postJson('/user/link_wallet', { wallet_address: walletAddress }),
    trustHistory: () => fetchApi('/user/trust_history'),
  },

  // Subscriptions
  subscription: {
    subscribe: (tier = 'premium', days = 30) => postJson('/subscription/subscribe', { tier, duration_days: days }),
    status: () => fetchApi('/subscription/status'),
  },

  // Jobs (milestone-based)
  jobs: {
    create: (payload) => postJson('/jobs/create', payload),
    list: (statusFilter, skills, limit = 50) => {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status_filter', statusFilter);
      if (skills) params.set('skills', skills);
      params.set('limit', limit);
      return fetchApi(`/jobs/list?${params}`);
    },
    detail: (jobId) => fetchApi(`/jobs/${jobId}`),
    apply: (jobId) => postJson(`/jobs/${jobId}/apply`, {}),
    matchFreelancers: (jobId, query = {}) => postJson(`/jobs/${jobId}/match_freelancers`, query),
    review: (jobId, rating, comment) => postJson(`/jobs/${jobId}/review`, { rating, comment }),
  },

  // Milestones
  milestones: {
    submit: (jobId, step, githubUrl, proofText) =>
      postJson(`/jobs/${jobId}/milestones/${step}/submit`, { github_repo_url: githubUrl, proof_text: proofText }),
    aiReview: (jobId, step) => postJson(`/jobs/${jobId}/milestones/${step}/ai_review`, {}),
    approve: (jobId, step) => postJson(`/jobs/${jobId}/milestones/${step}/approve`, {}),
    fail: (jobId, step) => postJson(`/jobs/${jobId}/milestones/${step}/fail`, {}),
    blockchain: (jobId, step) => fetchApi(`/jobs/${jobId}/milestones/${step}/blockchain`),
  },

  // Worker Score
  worker: {
    score: (userId) => fetchApi(`/worker/score/${userId}`),
    milestoneHistory: (userId) => fetchApi(`/worker/${userId}/milestone_history`),
  },

  // AI Analysis
  analyze: {
    repo: (githubUrl, criteria) => postJson('/analyze/repo', { github_repo_url: githubUrl, acceptance_criteria: criteria }),
  },
};
