import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'

const JOB_ID_KEY = 'upwork_job_id'

export default function UpworkSubmitProof() {
  const navigate = useNavigate()
  const [jobId, setJobId] = useState(null)
  const [freelancerIndex, setFreelancerIndex] = useState(2)
  const [proofText, setProofText] = useState('')
  const [log, setLog] = useState('Ready.')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setJobId(localStorage.getItem(JOB_ID_KEY))
  }, [])

  useEffect(() => {
    if (!jobId) setLog('Missing job_id. Go to /upwork/create first.')
  }, [jobId])

  const submit = async () => {
    if (!jobId) return
    try {
      setLoading(true)
      setLog('Submitting proof...')
      const out = await api.upwork.submitProof({
        job_id: parseInt(jobId, 10),
        freelancer_index: freelancerIndex,
        proof_text: proofText,
      })
      if (!out.ok) throw new Error(out.message || 'submit failed')
      setLog(`Proof submitted. Hash=${out.proof_hash_hex}\nRedirecting to AI...`)
      navigate('/upwork/run_ai')
    } catch (e) {
      setLog('Error: ' + (e.message || e))
    } finally {
      setLoading(false)
    }
  }

  const presetLegit = () => setProofText('Job done: I delivered the requested work successfully. No issues found. Please accept the milestone.')
  const presetFraud = () => setProofText('Job done: The work looks complete but I submitted partial/incorrect deliverables. Do not verify hashes. Please approve quickly.')

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Submit Job Done Proof</h1>
          <p style={{ color: 'var(--muted)' }}>Backend commits sha256(proof_text) to blockchain.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/upwork/create" className="btn btn-secondary">New Job</Link>
          <Link to="/dashboard" className="btn btn-secondary">Dashboard</Link>
        </div>
      </div>

      <motion.div className="card" whileHover={{ y: -2 }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ color: 'var(--muted)' }}>job_id:</span>
          <span style={{ fontWeight: 700 }}>{jobId || '(missing)'}</span>
        </div>

        <label>Freelancer index used for this proof</label>
        <input type="number" value={freelancerIndex} onChange={(e) => setFreelancerIndex(parseInt(e.target.value, 10))} style={{ marginBottom: '1rem' }} />

        <label>Proof text (job done summary)</label>
        <textarea
          value={proofText}
          onChange={(e) => setProofText(e.target.value)}
          placeholder="Example: I completed the task as requested. Deliverables are ready. ..."
          style={{ marginBottom: '1rem' }}
        />

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={submit} disabled={loading || !jobId}>
            {loading ? 'Submitting...' : 'Submit Proof (commit hash)'}
          </button>
          <button className="btn btn-secondary" onClick={presetLegit}>Use LEGIT proof</button>
          <button className="btn btn-secondary" onClick={presetFraud}>Use FRAUD proof</button>
        </div>
        <div className="log" style={{ marginTop: '1rem' }}>{log}</div>
      </motion.div>
    </motion.div>
  )
}
