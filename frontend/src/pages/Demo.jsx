import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import TrustChart from '../components/TrustChart'
import { api } from '../api'

function shortAddr(addr) {
  if (!addr) return '-'
  return String(addr).slice(0, 10) + '...' + String(addr).slice(-6)
}

function riskBadge(trust, blacklisted) {
  if (blacklisted) return <span className="badge badge-blacklisted">Blacklisted</span>
  if (trust == null) return <span className="badge badge-blacklisted">N/A</span>
  if (trust <= 0) return <span className="badge badge-high">Blacklisted</span>
  if (trust < 40) return <span className="badge badge-high">High</span>
  if (trust < 80) return <span className="badge badge-medium">Medium</span>
  return <span className="badge badge-low">Low</span>
}

export default function Demo() {
  const [trustHistory, setTrustHistory] = useState({})
  const [accounts, setAccounts] = useState({})
  const [clientsSnapshot, setClientsSnapshot] = useState({})
  const [round, setRound] = useState('-')
  const [log, setLog] = useState('Ready.')
  const [autoOn, setAutoOn] = useState(true)

  const refresh = async () => {
    try {
      const [hist, acc, clients, roundData] = await Promise.all([
        api.trustHistory(),
        api.ganacheAccountsTrust(8),
        api.currentTrust(),
        api.getGlobalModel(),
      ])
      setTrustHistory(hist)
      setAccounts(acc)
      setClientsSnapshot(clients)
      setRound(roundData?.round ?? '-')
      setLog('Last refreshed: ' + new Date().toLocaleTimeString())
    } catch (e) {
      setLog('Error fetching demo data. Is the backend running?')
    }
  }

  const aggregate = async () => {
    try {
      setLog('Calling /aggregate ...')
      await api.aggregate()
      await refresh()
    } catch (e) {
      setLog('Aggregate failed. Check terminal logs.')
    }
  }

  useEffect(() => {
    refresh()
    if (!autoOn) return
    const id = setInterval(refresh, 2500)
    return () => clearInterval(id)
  }, [autoOn])

  const clientIds = Object.keys(trustHistory || {}).sort()

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ marginBottom: '0.25rem' }}>TrustScore for Freelancing Trust (ML + Blockchain)</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
          Live demo UI. Uses your running backend (API) and Ganache contract state.
        </p>
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
          <span><span style={{ color: 'var(--muted)' }}>Server</span> FastAPI</span>
          <span><span style={{ color: 'var(--muted)' }}>Round</span> <span className="badge badge-low">{round}</span></span>
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">API Docs</a>
        </div>
      </div>

      <div className="grid-2">
        <motion.div className="card" whileHover={{ y: -2 }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '1rem' }}>
            <button className="btn btn-primary" onClick={aggregate}>Aggregate (next round)</button>
            <button className="btn btn-secondary" onClick={refresh}>Refresh</button>
            <span style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>Auto-refresh: {autoOn ? 'ON' : 'OFF'}</span>
            <button className="btn btn-secondary" onClick={() => setAutoOn((o) => !o)}>Toggle</button>
          </div>
          <div className="log" style={{ marginBottom: '1rem' }}>{log}</div>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', lineHeight: 1.6 }}>
            <strong>Demo steps</strong><br />
            1. Run clients (terminals): client1, client2, client3, malicious_client<br />
            2. Click <strong>Aggregate</strong> to record one trust snapshot.<br />
            3. Malicious client trust should drop, and blacklist should flip.
          </p>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }}>
          <h2 style={{ marginBottom: '0.5rem' }}>On-chain Trust (Ganache)</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Latest trust & blacklist for blockchain accounts.</p>
          <div style={{ overflowX: 'auto', maxHeight: 220 }}>
            <table>
              <thead>
                <tr><th>Address</th><th>Trust</th><th>Blacklist</th></tr>
              </thead>
              <tbody>
                {Object.entries(accounts).map(([addr, info]) => (
                  <tr key={addr}>
                    <td style={{ fontSize: '0.8rem' }}>{addr}</td>
                    <td>{info.trust}</td>
                    <td>
                      <span className={`badge ${info.blacklisted ? 'badge-blacklisted' : info.trust < 40 ? 'badge-high' : info.trust < 80 ? 'badge-medium' : 'badge-low'}`}>
                        {info.blacklisted ? 'Blacklisted' : 'Active'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>

      <div className="grid-2" style={{ marginTop: '1.5rem' }}>
        <motion.div className="card" whileHover={{ y: -2 }}>
          <h2 style={{ marginBottom: '0.5rem' }}>Trust Evolution (per client)</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Each click of Aggregate records one trust snapshot.</p>
          <TrustChart trustHistory={trustHistory} />
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }}>
          <h2 style={{ marginBottom: '0.5rem' }}>Risk Levels</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>Latest trust + blacklist for client_* participants.</p>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr><th>Client</th><th>Address</th><th>Latest Trust</th><th>Risk</th></tr>
              </thead>
              <tbody>
                {clientIds.map((cid) => {
                  const snap = clientsSnapshot[cid] || {}
                  const trust = typeof snap.trust === 'number' ? snap.trust : null
                  const blacklisted = !!snap.blacklisted
                  return (
                    <tr key={cid}>
                      <td>{cid}</td>
                      <td>{shortAddr(snap.address)}</td>
                      <td>{trust ?? 'N/A'}</td>
                      <td>{riskBadge(trust, blacklisted)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
