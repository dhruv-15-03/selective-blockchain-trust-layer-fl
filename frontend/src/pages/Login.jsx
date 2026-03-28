import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'
import './Login.css'

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
    <div className="login-page">
      <div className="login-page__bg" aria-hidden />
      <div className="login-page__earth-wrap" aria-hidden>
        <div className="login-page__earth-glow" />
        <div className="login-page__earth">
          <div className="login-page__earth-surface" />
        </div>
      </div>
      <div className="login-page__vignette" aria-hidden />
      <div className="login-page__grid" aria-hidden />

      <motion.div
        className="login-shell"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="login-brand-row">
          <Link to="/" className="login-brand">
            TrustScore
          </Link>
          <span className="badge login-badge">Blockchain</span>
        </div>

        <div className="login-card">
          <h1>Welcome back</h1>
          <p className="login-card__lead">Sign in with your email to access your profile and demos.</p>

          <form className="login-form" onSubmit={handleSubmit}>
            {error && (
              <motion.div
                className="login-error"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                role="alert"
              >
                {error}
              </motion.div>
            )}

            <div>
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary login-submit">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="login-footer">
            Don&apos;t have an account?{' '}
            <Link to="/signup">Create one</Link>
          </p>

          <Link to="/" className="login-back">
            ← Back to home
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
