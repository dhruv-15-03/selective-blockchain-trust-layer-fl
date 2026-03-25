import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function Run() {
  return (
    <motion.div
      className="page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <h1 style={{ marginBottom: '0.5rem', fontSize: '1.75rem' }}>Start Demo</h1>
      <p style={{ color: 'var(--muted)', marginBottom: '2rem' }}>
        Run clients, then click Aggregate to record trust results.
      </p>

      <div className="grid-2">
        <motion.div
          className="card"
          whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
        >
          <h2 style={{ marginBottom: '0.5rem' }}>Upwork TrustScore Demo</h2>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
            This project has a job workflow site. Use the button below to start.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Link to="/upwork/create" className="btn btn-primary">
              Start Upwork Flow
            </Link>
            <Link to="/dashboard" className="btn btn-secondary">
              Open Dashboard
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="card"
          whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
        >
          <h2 style={{ marginBottom: '0.5rem' }}>(Optional) API-based demo</h2>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
            Run backend endpoints manually using <code style={{ background: 'var(--bg-dark)', padding: '0.2rem 0.5rem', borderRadius: 6 }}>/docs</code>.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="btn btn-secondary">
              API Docs
            </a>
            <Link to="/demo" className="btn btn-secondary">
              Legacy /demo
            </Link>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
