import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'

const JOB_ID_KEY = 'upwork_job_id'

function shortAddr(addr) {
  if (!addr) return '-'
  return String(addr).slice(0, 10) + '...' + String(addr).slice(-6)
}

export default function UpworkResults() {
  const [jobId, setJobId] = useState(null)
  const [job, setJob] = useState(null)
  const [clients, setClients] = useState({})

  useEffect(() => {
    setJobId(localStorage.getItem(JOB_ID_KEY))
  }, [])

  useEffect(() => {
    if (!jobId) return
    const load = async () => {
      try {
        const [status, clientsRes] = await Promise.all([
          api.upwork.status(jobId),
          api.clientsSnapshot(),
        ])
        setJob(status?.job)
        setClients(clientsRes || {})
      } catch (e) {
        console.error(e)
      }
    }
    load()
  }, [jobId])

  if (!jobId) {
    return (
      <motion.div className="page" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <p>Missing job_id. <Link to="/upwork/create">Create a job</Link> first.</p>
      </motion.div>
    )
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
          <h1 style={{ marginBottom: '0.25rem' }}>Results</h1>
          <p style={{ color: 'var(--muted)' }}>Decision committed + trust snapshot.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/upwork/create" className="btn btn-secondary">New Job</Link>
          <Link to="/dashboard" className="btn btn-primary">Dashboard</Link>
        </div>
      </div>

      <motion.div className="card" style={{ marginBottom: '1.5rem' }} whileHover={{ y: -2 }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <span style={{ color: 'var(--muted)' }}>job_id:</span>
          <span style={{ fontWeight: 700 }}>{jobId}</span>
        </div>
      </motion.div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        <motion.div className="card" whileHover={{ y: -2 }}>
          <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>AI Verdict</div>
          <div className="log">
            {job ? JSON.stringify(job.ai_result || {}, null, 2) : 'Loading...'}
          </div>
        </motion.div>
        <motion.div className="card" whileHover={{ y: -2 }}>
          <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Decision</div>
          <div className="log">
            {job ? JSON.stringify({ decision: job.decision, decision_hash_hex: job.decision_hash_hex }, null, 2) : 'Loading...'}
          </div>
        </motion.div>
      </div>

      <motion.div className="card" style={{ marginBottom: '1.5rem' }} whileHover={{ y: -2 }}>
        <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>On-chain commitment hashes</div>
        <div className="log">
          {job ? JSON.stringify(job.onchain_commitments || {}, null, 2) : 'Loading...'}
        </div>
      </motion.div>

      <motion.div className="card" whileHover={{ y: -2 }}>
        <div style={{ fontWeight: 700, marginBottom: '1rem' }}>Clients trust (known demo participants)</div>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr><th>client</th><th>address</th><th>trust</th><th>blacklisted</th></tr>
            </thead>
            <tbody>
              {Object.entries(clients).map(([cid, info]) => (
                <tr key={cid}>
                  <td>{cid}</td>
                  <td>{shortAddr(info.address)}</td>
                  <td>{info.trust}</td>
                  <td>{String(info.blacklisted)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
