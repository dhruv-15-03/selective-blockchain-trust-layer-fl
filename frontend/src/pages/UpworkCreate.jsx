import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'

const JOB_ID_KEY = 'upwork_job_id'

export default function UpworkCreate() {
  const navigate = useNavigate()
  const [clientIndex, setClientIndex] = useState(1)
  const [freelancerIndex, setFreelancerIndex] = useState(2)
  const [amount, setAmount] = useState(100)
  const [deadlineHours, setDeadlineHours] = useState(0.01)
  const [log, setLog] = useState('Ready.')
  const [loading, setLoading] = useState(false)
  const [storedJobId, setStoredJobId] = useState(null)

  useEffect(() => {
    setStoredJobId(localStorage.getItem(JOB_ID_KEY))
  }, [])

  const clearJobId = () => {
    localStorage.removeItem(JOB_ID_KEY)
    setStoredJobId(null)
    setLog('Cleared job_id.')
  }

  const createJob = async () => {
    try {
      setLoading(true)
      setLog('Creating job...')
      const out = await api.upwork.createJob({
        client_index: clientIndex,
        freelancer_index: freelancerIndex,
        amount,
        deadline_hours: deadlineHours,
      })
      if (!out.job_id) throw new Error(out.message || 'Create failed')
      localStorage.setItem(JOB_ID_KEY, String(out.job_id))
      setStoredJobId(String(out.job_id))
      setLog(`Job created. job_id=${out.job_id} state=${out.state}\nRedirecting...`)
      navigate('/upwork/submit_proof')
    } catch (e) {
      setLog('Error: ' + (e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const steps = [
    { n: 1, name: 'Create', active: true },
    { n: 2, name: 'Submit Proof', active: false },
    { n: 3, name: 'Run AI', active: false },
    { n: 4, name: 'Decision', active: false },
  ]

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Create Upwork Job</h1>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>Proof → AI Risk → Approve/Dispute → Results (on-chain commitments)</p>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {steps.map((s) => (
              <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span
                  className="badge"
                  style={{
                    width: 34,
                    height: 34,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: s.active ? 'var(--accent)' : 'var(--bg-card)',
                    borderColor: s.active ? 'var(--accent)' : 'var(--border)',
                  }}
                >
                  {s.n}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{s.name}</span>
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/dashboard" className="btn btn-secondary">Dashboard</Link>
          <Link to="/" className="btn btn-secondary">Home</Link>
        </div>
      </div>

      <div className="grid-2">
        <motion.div className="card" whileHover={{ y: -2 }}>
          <span className="badge badge-low" style={{ marginBottom: '1rem' }}>Step 1</span>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>Create job on-chain commitments</p>

          <label>Client (client_index)</label>
          <select value={clientIndex} onChange={(e) => setClientIndex(parseInt(e.target.value, 10))} style={{ marginBottom: '1rem' }}>
            <option value={1}>client_index=1 (client_1)</option>
            <option value={2}>client_index=2 (client_2)</option>
            <option value={3}>client_index=3 (client_3)</option>
          </select>

          <label>Freelancer (freelancer_index)</label>
          <select value={freelancerIndex} onChange={(e) => setFreelancerIndex(parseInt(e.target.value, 10))} style={{ marginBottom: '1rem' }}>
            <option value={2}>freelancer_index=2 (freelancer role)</option>
            <option value={4}>freelancer_index=4 (malicious role)</option>
          </select>

          <label>Amount (demo)</label>
          <input type="number" value={amount} onChange={(e) => setAmount(parseFloat(e.target.value))} style={{ marginBottom: '1rem' }} />

          <label>Deadline hours (demo)</label>
          <input type="number" step={0.01} value={deadlineHours} onChange={(e) => setDeadlineHours(parseFloat(e.target.value))} style={{ marginBottom: '1rem' }} />

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={createJob} disabled={loading}>
              {loading ? 'Creating...' : 'Create Job'}
            </button>
            <button className="btn btn-secondary" onClick={clearJobId}>Clear Stored job_id</button>
          </div>
          <div className="log" style={{ marginTop: '1rem' }}>{log}</div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }}>
          <span className="badge badge-low" style={{ marginBottom: '1rem' }}>Live Job Preview</span>
          <p style={{ color: 'var(--muted)', lineHeight: 1.7, marginBottom: '1rem' }}>
            <b>After "Create Job":</b><br />
            1) Redirect to /upwork/submit_proof<br />
            2) Backend commits sha256(proof_text) on-chain<br />
            3) Backend runs AI risk + commits AI hash<br />
            4) Decision updates TrustScore + blacklist
          </p>
          <label>Stored job_id (browser)</label>
          <div className="log" style={{ marginTop: '0.5rem' }}>
            <div>{storedJobId || '(none yet)'}</div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem' }}
                disabled={!storedJobId}
                onClick={async () => {
                  if (storedJobId) {
                    await navigator.clipboard.writeText(storedJobId)
                    setLog('Copied job_id: ' + storedJobId)
                  }
                }}
              >
                Copy job_id
              </button>
              <Link
                to="/upwork/submit_proof"
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem', opacity: storedJobId ? 1 : 0.5, pointerEvents: storedJobId ? 'auto' : 'none' }}
              >
                Go to Proof
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
