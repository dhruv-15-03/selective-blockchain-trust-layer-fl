import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import TrustChart from '../components/TrustChart'
import { api } from '../api'

function shortAddr(addr) {
  if (!addr) return '-'
  return String(addr).slice(0, 10) + '...' + String(addr).slice(-6)
}

function statusBadge(trust, blacklisted) {
  if (blacklisted) return <span className="badge badge-blacklisted">Blacklisted</span>
  if (trust == null) return <span className="badge badge-blacklisted">N/A</span>
  if (trust <= 0) return <span className="badge badge-high">Blacklisted</span>
  if (trust < 40) return <span className="badge badge-high">High</span>
  if (trust < 80) return <span className="badge badge-medium">Medium</span>
  return <span className="badge badge-low">Low</span>
}

export default function Results() {
  const [trustHistory, setTrustHistory] = useState({})
  const [clients, setClients] = useState({})
  const [round, setRound] = useState('-')
  const [log, setLog] = useState('Loading...')

  useEffect(() => {
    const load = async () => {
      try {
        const [hist, snap, roundData] = await Promise.all([
          api.trustHistory(),
          api.clientsSnapshot(),
          api.getGlobalModel(),
        ])
        setTrustHistory(hist)
        setClients(snap)
        setRound(roundData?.round ?? '-')
        setLog('Refreshed at ' + new Date().toLocaleTimeString())
      } catch (e) {
        setLog('Error: ' + e.message)
      }
    }
    load()
  }, [])

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Results</h1>
          <p style={{ color: 'var(--muted)' }}>After clicking Aggregate, trust snapshots are recorded on server + blockchain.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/run" className="btn btn-secondary">Back to Run</Link>
          <Link to="/dashboard" className="btn btn-primary">Dashboard</Link>
          <Link to="/" className="btn btn-secondary">Home</Link>
        </div>
      </div>

      <div className="log" style={{ marginBottom: '1.5rem' }}>{log}</div>

      <div className="grid-12">
        <motion.div className="card col-6" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem' }}>On-chain Trust Snapshot</div>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Round: {round}</p>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr><th>Client</th><th>Address</th><th>Trust</th><th>Status</th></tr>
              </thead>
              <tbody>
                {Object.entries(clients).map(([cid, info]) => (
                  <tr key={cid}>
                    <td>{cid}</td>
                    <td>{shortAddr(info.address)}</td>
                    <td>{info.trust}</td>
                    <td>{statusBadge(info.trust, info.blacklisted)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        <motion.div className="card col-6" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem' }}>Trust Evolution (history)</div>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Chart updates from /trust_history.</p>
          <TrustChart trustHistory={trustHistory} />
        </motion.div>

        <motion.div className="card col-12" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.5rem' }}>What to mention during demo</div>
          <p style={{ color: 'var(--muted)', lineHeight: 1.8 }}>
            1) Client submits model update hash on-chain.<br />
            2) Server verifies weights hash match for that round.<br />
            3) ML gate flags malicious updates.<br />
            4) Server penalizes client and blacklists on-chain.<br />
            5) UI shows trust drop & blacklist clearly.
          </p>
        </motion.div>
      </div>
    </motion.div>
  )
}
