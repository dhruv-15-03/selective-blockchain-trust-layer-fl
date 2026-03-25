import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'

const links = [
  { to: '/', label: 'Home' },
  { to: '/login', label: 'Login' },
  { to: '/signup', label: 'Sign Up' },
  { to: '/upwork/create', label: 'Start Demo' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/run', label: 'Run' },
  { to: '/demo', label: 'FL Demo' },
  { to: '/results', label: 'Results' },
]

export default function Nav() {
  const loc = useLocation()

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="nav"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'rgba(10, 10, 15, 0.9)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border)',
        padding: '1rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}
    >
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text)' }}>
        <span style={{ fontSize: '1.5rem', fontWeight: 700 }}>TrustScore</span>
        <span className="badge badge-low" style={{ fontSize: '0.65rem' }}>Blockchain</span>
      </Link>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className="btn btn-secondary"
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.85rem',
              background: loc.pathname === l.to ? 'rgba(99, 102, 241, 0.2)' : undefined,
              borderColor: loc.pathname === l.to ? 'var(--accent)' : undefined,
            }}
          >
            {l.label}
          </Link>
        ))}
        <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}>
          API Docs
        </a>
      </div>
    </motion.nav>
  )
}
