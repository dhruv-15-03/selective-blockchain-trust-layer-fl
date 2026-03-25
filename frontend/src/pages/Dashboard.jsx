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

export default function Dashboard() {
  const [trustHistory, setTrustHistory] = useState({})
  const [clients, setClients] = useState({})
  const [log, setLog] = useState('Loading...')

  const refresh = async () => {
    try {
      const [hist, snap] = await Promise.all([api.trustHistory(), api.clientsSnapshot()])
      setTrustHistory(hist)
      setClients(snap)
      setLog('Refreshed at ' + new Date().toLocaleTimeString())
    } catch (e) {
      setLog('Error: ' + e.message)
    }
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 2500)
    return () => clearInterval(id)
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
          <h1 style={{ marginBottom: '0.25rem' }}>Dashboard</h1>
          <p style={{ color: 'var(--muted)' }}>Live view of on-chain TrustScore + trust evolution.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/run" className="btn btn-secondary">Run Demo</Link>
          <Link to="/results" className="btn btn-primary">Results</Link>
          <Link to="/" className="btn btn-secondary">Home</Link>
        </div>
      </div>

      <div className="log" style={{ marginBottom: '1.5rem' }}>{log}</div>

      <div className="grid-2">
        <motion.div className="card" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
          <h2 style={{ marginBottom: '0.5rem' }}>On-chain snapshot (latest)</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            For known demo participants (client_1/client_2/client_3/malicious_client).
          </p>
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

        <motion.div className="card" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
          <h2 style={{ marginBottom: '0.5rem' }}>Trust Evolution</h2>
          <TrustChart trustHistory={trustHistory} />
        </motion.div>
      </div>

      <motion.div className="card" style={{ marginTop: '1.5rem' }} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <h2 style={{ marginBottom: '0.5rem' }}>How to use (1 minute)</h2>
        <p style={{ color: 'var(--muted)' }}>
          1) Run clients in terminals.<br />
          2) Click <b>Aggregate</b> from <Link to="/run"><b>Start Demo</b></Link>.<br />
          3) Trust drop & blacklist will appear here.
        </p>
      </motion.div>
    </motion.div>
  )
}
