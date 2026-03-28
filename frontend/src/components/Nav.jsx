import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getStoredUser, getUserInitial, logout } from '../utils/trustAuth'

const primaryLinks = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/results', label: 'Results' },
]

const publicOverflowLinks = [
  { to: '/login', label: 'Login' },
  { to: '/signup', label: 'Sign Up' },
  { to: '/upwork/create', label: 'Start Demo' },
  { to: '/run', label: 'Run' },
  { to: '/demo', label: 'FL Demo' },
]

const authedOverflowLinks = [
  { to: '/upwork/create', label: 'Start Demo' },
  { to: '/run', label: 'Run' },
  { to: '/demo', label: 'FL Demo' },
]

function HamburgerIcon({ open }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      {open ? (
        <>
          <path d="M18 6L6 18M6 6l12 12" />
        </>
      ) : (
        <>
          <path d="M4 7h16M4 12h16M4 17h16" />
        </>
      )}
    </svg>
  )
}

export default function Nav() {
  const loc = useLocation()
  const navigate = useNavigate()
  const user = getStoredUser()

  const [burgerOpen, setBurgerOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const burgerRef = useRef(null)
  const profileRef = useRef(null)

  const overflowLinks = user ? authedOverflowLinks : publicOverflowLinks

  useEffect(() => {
    setBurgerOpen(false)
    setProfileOpen(false)
  }, [loc.pathname])

  useEffect(() => {
    if (!burgerOpen && !profileOpen) return
    const onMouseDown = (e) => {
      if (burgerOpen && burgerRef.current && !burgerRef.current.contains(e.target)) {
        setBurgerOpen(false)
      }
      if (profileOpen && profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [burgerOpen, profileOpen])

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

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end', marginLeft: 'auto' }}>
        {primaryLinks.map((l) => (
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

        <div ref={burgerRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setBurgerOpen((v) => !v)
              setProfileOpen(false)
            }}
            aria-expanded={burgerOpen}
            aria-label={burgerOpen ? 'Close menu' : 'Open menu'}
            style={{
              padding: '0.5rem 0.75rem',
              minWidth: 44,
              minHeight: 44,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <HamburgerIcon open={burgerOpen} />
          </button>

          {burgerOpen && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 0.5rem)',
                minWidth: 220,
                background: 'rgba(10, 10, 15, 0.97)',
                border: '1px solid var(--border)',
                borderRadius: 16,
                padding: '0.5rem',
                backdropFilter: 'blur(12px)',
                boxShadow: '0 16px 40px rgba(0,0,0,0.45)',
              }}
            >
              {overflowLinks.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  onClick={() => setBurgerOpen(false)}
                  className="btn btn-secondary"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    padding: '0.65rem 0.85rem',
                    borderRadius: 12,
                    marginBottom: '0.25rem',
                    fontSize: '0.85rem',
                    background: loc.pathname === l.to ? 'rgba(99, 102, 241, 0.2)' : undefined,
                    borderColor: loc.pathname === l.to ? 'var(--accent)' : undefined,
                  }}
                >
                  {l.label}
                </Link>
              ))}
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary"
                onClick={() => setBurgerOpen(false)}
                style={{
                  width: '100%',
                  justifyContent: 'flex-start',
                  padding: '0.65rem 0.85rem',
                  borderRadius: 12,
                  fontSize: '0.85rem',
                }}
              >
                API Docs
              </a>
            </div>
          )}
        </div>

        {user && (
          <div ref={profileRef} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {user.role && (
              <span
                className="badge badge-low"
                style={{ fontSize: '0.65rem', textTransform: 'capitalize', whiteSpace: 'nowrap' }}
                title="Account type"
              >
                {user.role}
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setProfileOpen((v) => !v)
                setBurgerOpen(false)
              }}
              aria-expanded={profileOpen}
              aria-label="Account"
              style={{
                width: 40,
                height: 40,
                borderRadius: 999,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0,
                background: 'rgba(99, 102, 241, 0.18)',
                borderColor: 'rgba(99, 102, 241, 0.4)',
              }}
              title="Profile"
            >
              <span style={{ fontWeight: 900 }}>{getUserInitial(user)}</span>
            </button>

            {profileOpen && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 'calc(100% + 0.5rem)',
                  minWidth: 220,
                  background: 'rgba(10, 10, 15, 0.95)',
                  border: '1px solid var(--border)',
                  borderRadius: 16,
                  padding: '0.5rem',
                  backdropFilter: 'blur(12px)',
                }}
              >
                <Link
                  to="/profile"
                  onClick={() => setProfileOpen(false)}
                  className="btn btn-secondary"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    padding: '0.65rem 0.85rem',
                    borderRadius: 12,
                    marginBottom: '0.25rem',
                  }}
                >
                  Profile
                </Link>

                <button
                  type="button"
                  onClick={() => {
                    logout()
                    setProfileOpen(false)
                    navigate('/')
                  }}
                  className="btn btn-secondary"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    padding: '0.65rem 0.85rem',
                    borderRadius: 12,
                  }}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.nav>
  )
}
