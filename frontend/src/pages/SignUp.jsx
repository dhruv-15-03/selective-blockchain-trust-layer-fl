import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'
import './Login.css'

export default function SignUp() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const goStep2 = (e) => {
    e.preventDefault()
    setError('')
    if (!name.trim() || !email.trim() || !password) {
      setError('Please fill name, email, and password.')
      return
    }
    setStep(2)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    if (!role) {
      setError('Choose Freelancer or Client.')
      return
    }
    setLoading(true)
    try {
      const res = await api.auth.signup({ name, email, password, role })
      if (res.ok && res.token) {
        localStorage.setItem('trust_token', res.token)
        localStorage.setItem('trust_user', JSON.stringify(res.user))
        navigate('/')
      } else {
        setError(res.detail || 'Sign up failed')
      }
    } catch (err) {
      setError(err.message || err.detail || 'Invalid data')
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
          {step === 1 && (
            <>
              <h1>Welcome</h1>
              <p className="login-card__lead">Create your account — next you’ll pick Freelancer or Client.</p>

              <form className="login-form" onSubmit={goStep2}>
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
                  <label htmlFor="signup-name">Full Name</label>
                  <input
                    id="signup-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    autoComplete="name"
                    placeholder="Your name"
                  />
                </div>

                <div>
                  <label htmlFor="signup-email">Email</label>
                  <input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </div>

                <div>
                  <label htmlFor="signup-password">Password</label>
                  <input
                    id="signup-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="••••••••"
                  />
                </div>

                <button type="submit" className="btn btn-primary login-submit">
                  Continue
                </button>
              </form>
            </>
          )}

          {step === 2 && (
            <>
              <h1>Account type</h1>
              <p className="login-card__lead">Aap kaun ho? Profile aur history isi ke hisaab se alag save hongi.</p>

              <form className="login-form" onSubmit={handleCreate}>
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
                  <span id="signup-role-label" style={{ fontWeight: 700, display: 'block', marginBottom: '0.5rem' }}>
                    Main…
                  </span>
                  <div className="signup-role-grid" role="group" aria-labelledby="signup-role-label">
                    <button
                      type="button"
                      className={`signup-role-card ${role === 'freelancer' ? 'signup-role-card--active' : ''}`}
                      onClick={() => setRole('freelancer')}
                    >
                      <span className="signup-role-card__title">Freelancer</span>
                      <span className="signup-role-card__hint">Kaam submit karna, skills, deliverables.</span>
                    </button>
                    <button
                      type="button"
                      className={`signup-role-card ${role === 'client' ? 'signup-role-card--active' : ''}`}
                      onClick={() => setRole('client')}
                    >
                      <span className="signup-role-card__title">Client</span>
                      <span className="signup-role-card__hint">Job post / hire, requirements, approvals.</span>
                    </button>
                  </div>
                </div>

                <div className="signup-step-actions">
                  <button type="submit" disabled={loading} className="btn btn-primary login-submit">
                    {loading ? 'Creating…' : 'Create account'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={loading}
                    onClick={() => {
                      setError('')
                      setStep(1)
                    }}
                  >
                    ← Back
                  </button>
                </div>
              </form>
            </>
          )}

          <p className="login-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>

          <Link to="/" className="login-back">
            ← Back to home
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
