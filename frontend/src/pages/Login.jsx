import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import LetterForm from '../components/LetterForm'
import { api } from '../api'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.auth.login({ email, password })
      if (res.ok && res.token) {
        localStorage.setItem('trust_token', res.token)
        localStorage.setItem('trust_user', JSON.stringify(res.user))
        navigate('/')
      } else {
        setError(res.detail || 'Login failed')
      }
    } catch (err) {
      setError(err.message || err.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      className="page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.15) 0%, transparent 50%)',
      }}
    >
      <motion.div
        initial={{ y: -30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        style={{ textAlign: 'center', marginBottom: '1rem' }}
      >
        <Link to="/" style={{ color: 'var(--text)', fontSize: '1.25rem', fontWeight: 700 }}>
          TrustScore
        </Link>
      </motion.div>

      <LetterForm title="Login" isOpen={true}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {error && (
            <div
              style={{
                padding: '0.75rem',
                background: 'rgba(239,68,68,0.15)',
                border: '1px solid rgba(239,68,68,0.4)',
                borderRadius: 8,
                color: '#ef4444',
                fontSize: '0.9rem',
              }}
            >
              {error}
            </div>
          )}
          <div>
            <label style={{ display: 'block', marginBottom: 6, fontWeight: 600, color: '#334155', fontSize: '0.9rem' }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: 10,
                border: '1px solid #cbd5e1',
                background: '#fff',
                color: '#0f172a',
                fontSize: '1rem',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 6, fontWeight: 600, color: '#334155', fontSize: '0.9rem' }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: 10,
                border: '1px solid #cbd5e1',
                background: '#fff',
                color: '#0f172a',
                fontSize: '1rem',
              }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ marginTop: '0.5rem', width: '100%' }}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        <p style={{ marginTop: '1.25rem', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
          Don't have an account?{' '}
          <Link to="/signup" style={{ color: 'var(--accent)', fontWeight: 600 }}>
            Sign up
          </Link>
        </p>
      </LetterForm>
    </motion.div>
  )
}
