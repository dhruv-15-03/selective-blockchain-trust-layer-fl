import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'

const JOB_ID_KEY = 'upwork_job_id'

export default function UpworkDecision() {
  const navigate = useNavigate()
  const [jobId, setJobId] = useState(null)
  const [clientIndex, setClientIndex] = useState(1)
  const [log, setLog] = useState('Ready.')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setJobId(localStorage.getItem(JOB_ID_KEY))
  }, [])

  const finalize = async (action) => {
    if (!jobId) return
    try {
      setLoading(true)
      setLog(`Finalizing action=${action}...`)
      const url = action === 'APPROVE' ? api.upwork.approve : api.upwork.dispute
      const out = await url(parseInt(jobId, 10), clientIndex)
      if (!out.ok) throw new Error(out.message || 'finalize failed')
      setLog('Decision committed. Redirecting to results...')
      navigate('/upwork/results')
    } catch (e) {
      setLog('Error: ' + (e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const autoFinalize = async () => {
    if (!jobId) return
    try {
      setLoading(true)
      const status = await api.upwork.status(jobId)
      const job = status?.job
      const verdict = job?.ai_result?.verdict
      if (!verdict) throw new Error('AI verdict missing. Run AI first.')
      const action = verdict === 'LEGIT' ? 'DISPUTE' : 'APPROVE'
      setLog(`AI verdict=${verdict}. Auto choosing action=${action}.`)
      await finalize(action)
    } catch (e) {
      setLog('Error: ' + (e.message || e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Client Decision (Approve / Dispute)</h1>
          <p style={{ color: 'var(--muted)' }}>Choose action; server penalizes inconsistent parties and updates TrustScore.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/upwork/run_ai" className="btn btn-secondary">Back</Link>
          <Link to="/dashboard" className="btn btn-secondary">Dashboard</Link>
        </div>
      </div>

      <motion.div className="card" whileHover={{ y: -2 }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ color: 'var(--muted)' }}>job_id:</span>
          <span style={{ fontWeight: 700 }}>{jobId || '(missing)'}</span>
        </div>

        <div className="grid-2" style={{ marginBottom: '1rem' }}>
          <div>
            <label>Choose client_index</label>
            <select value={clientIndex} onChange={(e) => setClientIndex(parseInt(e.target.value, 10))}>
              <option value={1}>client_index=1 (client_1)</option>
              <option value={2}>client_index=2 (client_2)</option>
              <option value={3}>client_index=3 (client_3)</option>
            </select>
          </div>
          <div>
            <label>Auto finalize (recommended)</label>
            <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
              Picks an action inconsistent with AI verdict to show penalties clearly.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={autoFinalize} disabled={loading || !jobId}>
            {loading ? 'Processing...' : 'Auto finalize'}
          </button>
          <button className="btn btn-secondary" onClick={() => finalize('APPROVE')} disabled={loading || !jobId}>
            Approve (manual)
          </button>
          <button className="btn btn-secondary" onClick={() => finalize('DISPUTE')} disabled={loading || !jobId}>
            Dispute (manual)
          </button>
          <Link to="/upwork/results" className="btn btn-secondary">View Results</Link>
        </div>
        <div className="log" style={{ marginTop: '1rem' }}>{log}</div>
      </motion.div>
    </motion.div>
  )
}
