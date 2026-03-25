import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'

const JOB_ID_KEY = 'upwork_job_id'

export default function UpworkRunAI() {
  const navigate = useNavigate()
  const [jobId, setJobId] = useState(null)
  const [log, setLog] = useState('Ready.')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setJobId(localStorage.getItem(JOB_ID_KEY))
  }, [])

  useEffect(() => {
    if (!jobId) setLog('Missing job_id. Go to /upwork/create.')
  }, [jobId])

  const runAi = async () => {
    if (!jobId) return
    try {
      setLoading(true)
      setLog('Running AI...')
      const out = await api.upwork.runAi(parseInt(jobId, 10))
      if (!out.ok) throw new Error(out.message || 'run_ai failed')
      const r = out.ai_result || {}
      setLog(`AI verdict: ${r.verdict || '-'}\nRiskScore: ${r.riskScore ?? '-'}\nAI hash: ${out.ai_hash_hex}`)
      navigate('/upwork/decision')
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
          <h1 style={{ marginBottom: '0.25rem' }}>Run AI Risk Scoring</h1>
          <p style={{ color: 'var(--muted)' }}>Server commits AI hash on-chain.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/upwork/submit_proof" className="btn btn-secondary">Back</Link>
          <Link to="/dashboard" className="btn btn-secondary">Dashboard</Link>
        </div>
      </div>

      <motion.div className="card" whileHover={{ y: -2 }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ color: 'var(--muted)' }}>job_id:</span>
          <span style={{ fontWeight: 700 }}>{jobId || '(missing)'}</span>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={runAi} disabled={loading || !jobId}>
            {loading ? 'Running...' : 'Run AI (commit hash)'}
          </button>
          <Link to="/upwork/decision" className="btn btn-secondary">Go to Decision</Link>
        </div>
        <div className="log" style={{ marginTop: '1rem' }}>{log}</div>
      </motion.div>
    </motion.div>
  )
}
