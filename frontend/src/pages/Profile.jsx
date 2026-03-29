import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'
import { getStoredUser } from '../utils/trustAuth'
import { getProfileStore } from '../utils/profileRoleStore'

function shortAddr(addr) {
  if (!addr) return '-'
  return String(addr).slice(0, 10) + '...' + String(addr).slice(-6)
}

function formatUnix(ts) {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  return d.toLocaleString()
}

function formatDurationSeconds(totalSeconds) {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return '-'
  const sec = Math.floor(totalSeconds)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m <= 0) return `${s}s`
  const h = Math.floor(m / 60)
  const mm = m % 60
  if (h > 0) return `${h}h ${mm}m`
  return `${m}m ${s}s`
}

export default function Profile() {
  const navigate = useNavigate()
  const user = getStoredUser()
  const userId = user?.id
  const store = useMemo(() => getProfileStore(user), [userId, user?.role])

  const isClient = user?.role === 'client'

  const [bio, setBioState] = useState('')
  const [skills, setSkillsState] = useState([])
  const [skillDraft, setSkillDraft] = useState('')

  const [jobIds, setJobIds] = useState([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsError, setJobsError] = useState('')
  const [jobs, setJobs] = useState([])

  // Backend resume data (blockchain-verified)
  const [resume, setResume] = useState(null)
  const [resumeLoading, setResumeLoading] = useState(false)

  useEffect(() => {
    if (!userId) return
    setBioState(store.getBio(userId))
    setSkillsState(store.getSkills(userId))
    setJobIds(store.getJobHistory(userId))

    // Fetch blockchain-verified resume from backend
    const loadResume = async () => {
      setResumeLoading(true)
      try {
        const data = await api.resume.mine()
        if (data && !data.ERROR) setResume(data)
      } catch {}
      setResumeLoading(false)
    }
    loadResume()
  }, [userId, store])

  useEffect(() => {
    if (!userId) return
    const loadJobs = async () => {
      setJobsLoading(true)
      setJobsError('')
      try {
        try {
          const currentJobId = localStorage.getItem('upwork_job_id')
          if (currentJobId) store.addJobToHistory(userId, currentJobId)
        } catch {}

        const ids = store.getJobHistory(userId)
        setJobIds(ids)
        const list = []
        for (const id of ids.slice(0, 20)) {
          const status = await api.upwork.status(parseInt(id, 10))
          if (status?.ok && status.job) list.push(status.job)
        }
        setJobs(list)
      } catch (e) {
        setJobsError(e?.message || String(e))
      } finally {
        setJobsLoading(false)
      }
    }
    loadJobs()
  }, [userId, store])

  const saveBio = () => {
    store.setBio(userId, bio)
  }

  const addSkillFromDraft = () => {
    const s = skillDraft.trim()
    if (!s) return
    store.addSkill(userId, s)
    const next = store.getSkills(userId)
    setSkillsState(next)
    setSkillDraft('')
  }

  const removeSkillItem = (skill) => {
    store.removeSkill(userId, skill)
    setSkillsState(store.getSkills(userId))
  }

  if (!userId) {
    return (
      <motion.div className="page" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="card">
          <h2 style={{ marginBottom: '0.5rem' }}>Login required</h2>
          <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
            Profile data and work history are shown for logged-in users.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Link to="/login" className="btn btn-primary">
              Go to Login
            </Link>
            <Link to="/" className="btn btn-secondary">
              Home
            </Link>
          </div>
        </div>
      </motion.div>
    )
  }

  const roleLabel = isClient ? 'Client' : 'Freelancer'

  return (
    <motion.div className="page" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Profile</h1>
          <p style={{ color: 'var(--muted)' }}>
            {user.name || user.email}{' '}
            <span className="badge badge-medium" style={{ marginLeft: '0.35rem', textTransform: 'capitalize' }}>
              {roleLabel}
            </span>{' '}
            <span style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>(User ID: {user.id})</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
        </div>
      </div>

      <div className="grid-2">
        <motion.div className="card" whileHover={{ y: -2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontWeight: 800, marginBottom: '0.25rem' }}>Bio</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
                {isClient ? 'Describe your company or hiring needs.' : 'Tell clients about your background.'}
              </div>
            </div>
            <span className="badge badge-low">Editable</span>
          </div>
          <textarea value={bio} onChange={(e) => setBioState(e.target.value)} placeholder={isClient ? 'Company / project context…' : 'Example: 5+ years in web3 audits…'} />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
            <button className="btn btn-primary" onClick={saveBio}>
              Save Bio
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setBioState(store.getBio(userId))
              }}
            >
              Reset
            </button>
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontWeight: 800, marginBottom: '0.25rem' }}>{isClient ? 'Focus areas' : 'Skills'}</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
                {isClient ? 'Technologies or domains you hire for.' : 'Add skills to get matched faster.'}
              </div>
            </div>
            <span className="badge badge-low">Editable</span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              value={skillDraft}
              onChange={(e) => setSkillDraft(e.target.value)}
              placeholder={isClient ? 'e.g. Solidity audits, UI design' : 'e.g. Solidity, React, Testing'}
            />
            <button className="btn btn-primary" onClick={addSkillFromDraft} style={{ whiteSpace: 'nowrap' }}>
              Add
            </button>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
            {skills.length === 0 ? (
              <div style={{ color: 'var(--muted)' }}>None yet. Add one above.</div>
            ) : (
              skills.map((s) => (
                <div
                  key={s}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.35rem 0.75rem',
                    borderRadius: 999,
                    border: '1px solid var(--border)',
                    background: 'rgba(10,10,15,0.35)',
                  }}
                >
                  <span style={{ fontWeight: 700 }}>{s}</span>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.25rem 0.6rem', borderRadius: 999, fontSize: '0.8rem' }}
                    onClick={() => removeSkillItem(s)}
                    title="Remove"
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>

          <button
            className="btn btn-secondary"
            style={{ marginTop: '1rem' }}
            onClick={() => {
              store.setSkills(userId, [])
              setSkillsState([])
            }}
            disabled={skills.length === 0}
          >
            Clear list
          </button>
        </motion.div>
      </div>

      <motion.div className="card" style={{ marginTop: '1.5rem' }} whileHover={{ y: -2 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
          <div>
            <div style={{ fontWeight: 800, marginBottom: '0.25rem' }}>Work History</div>
            <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
              Job timeline and blockchain IDs ({roleLabel.toLowerCase()} view — stored separately from the other role).
            </div>
          </div>
          <span className="badge badge-medium">{jobIds.length} jobs tracked</span>
        </div>

        {jobsLoading && <div className="log" style={{ marginBottom: '1rem' }}>Loading jobs...</div>}
        {jobsError && (
          <div className="log" style={{ marginBottom: '1rem', borderColor: 'rgba(239,68,68,0.45)' }}>
            Error: {jobsError}
          </div>
        )}

        {jobs.length === 0 ? (
          <div style={{ color: 'var(--muted)' }}>
            No jobs in your profile history yet. Go to <Link to="/upwork/create">Start Demo</Link>.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Blockchain IDs</th>
                  <th>Given Time</th>
                  <th>Completion</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => {
                  const createdAt = j?.created_at
                  const decidedAt = j?.decided_at
                  const durationSeconds =
                    createdAt && decidedAt ? decidedAt - createdAt : j?.state === 'DECIDED' && createdAt ? Math.floor(Date.now() / 1000) - createdAt : null
                  return (
                    <tr key={j.job_id}>
                      <td style={{ width: 120 }}>
                        <div style={{ fontWeight: 800 }}>#{j.job_id}</div>
                        <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{j.state}</div>
                      </td>
                      <td style={{ minWidth: 260 }}>
                        <div style={{ marginBottom: '0.35rem' }}>
                          <span style={{ color: 'var(--muted)' }}>Client:</span> <span style={{ fontWeight: 700 }}>{shortAddr(j.client_addr)}</span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--muted)' }}>Freelancer:</span>{' '}
                          <span style={{ fontWeight: 700 }}>{shortAddr(j.freelancer_addr)}</span>
                        </div>
                      </td>
                      <td style={{ minWidth: 210 }}>
                        <div style={{ fontWeight: 700 }}>{formatUnix(createdAt)}</div>
                      </td>
                      <td style={{ minWidth: 210 }}>
                        {durationSeconds == null ? (
                          <div style={{ color: 'var(--muted)' }}>Not completed yet</div>
                        ) : (
                          <div>
                            <div style={{ fontWeight: 800 }}>Completed in {formatDurationSeconds(durationSeconds)}</div>
                            <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                              {decidedAt ? `Completed at: ${formatUnix(decidedAt)}` : 'Completed time estimate (based on now)'}
                            </div>
                          </div>
                        )}
                      </td>
                      <td style={{ minWidth: 220 }}>
                        <div style={{ fontWeight: 800 }}>{j.decision || '-'}</div>
                        <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                          {j.decision_hash_hex ? `Decision hash: ${String(j.decision_hash_hex).slice(0, 14)}...` : ''}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>

      {/* Blockchain-Verified Resume Section */}
      {!isClient && (
        <motion.div className="card" style={{ marginTop: '1.5rem' }} whileHover={{ y: -2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontWeight: 800, marginBottom: '0.25rem' }}>⛓ Blockchain-Verified Resume</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
                Skills, projects, and scores verified on-chain — tamper-proof proof of work.
              </div>
            </div>
            {resume?.verification?.blockchain_committed && (
              <span className="badge badge-low" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>
                ✓ On-Chain Verified
              </span>
            )}
          </div>

          {resumeLoading && <div style={{ color: 'var(--muted)' }}>Loading resume from blockchain...</div>}

          {resume && (
            <>
              {/* Trust Score Section */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ background: 'rgba(99,102,241,0.1)', borderRadius: 8, padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#818cf8' }}>{resume.trust?.project_trust_score || 0}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Trust Score</div>
                </div>
                <div style={{ background: 'rgba(34,197,94,0.1)', borderRadius: 8, padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#22c55e' }}>{resume.trust?.confidence_score || 0}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Confidence</div>
                </div>
                <div style={{ background: 'rgba(251,191,36,0.1)', borderRadius: 8, padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fbbf24' }}>{resume.trust?.avg_quality_score || 0}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Quality Avg</div>
                </div>
                <div style={{ background: 'rgba(96,165,250,0.1)', borderRadius: 8, padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#60a5fa' }}>{resume.trust?.trust_level || 'Bronze'}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Trust Level</div>
                </div>
              </div>

              {/* Stats Row */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
                <div><span style={{ color: 'var(--muted)' }}>Jobs:</span> <strong>{resume.stats?.total_jobs_completed || 0}</strong></div>
                <div><span style={{ color: 'var(--muted)' }}>Milestones:</span> <strong>{resume.stats?.total_milestones_passed || 0}</strong></div>
                <div><span style={{ color: 'var(--muted)' }}>Earnings:</span> <strong>${resume.stats?.total_earnings || 0}</strong></div>
                <div><span style={{ color: 'var(--muted)' }}>Rating:</span> <strong>{resume.stats?.avg_client_rating || 0}/5</strong></div>
                <div><span style={{ color: 'var(--muted)' }}>On-time streak:</span> <strong>{resume.trust?.on_time_streak || 0}</strong></div>
              </div>

              {/* Verified Skills */}
              {resume.verified_skills?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Verified Skills (from completed projects)</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {resume.verified_skills.map((sk) => (
                      <div
                        key={sk.skill}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                          padding: '0.3rem 0.7rem', borderRadius: 999,
                          border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.08)',
                        }}
                      >
                        <span style={{ fontWeight: 700, color: '#a5b4fc' }}>{sk.skill}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                          {sk.projects_count} proj · {sk.avg_score}%
                        </span>
                        {sk.verified && <span style={{ color: '#22c55e', fontSize: '0.7rem' }}>✓</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Projects */}
              {resume.projects?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Completed Projects</div>
                  {resume.projects.map((p) => (
                    <div
                      key={p.job_id}
                      style={{
                        padding: '0.6rem 0.8rem', marginBottom: '0.4rem', borderRadius: 8,
                        border: '1px solid var(--border)', background: 'rgba(10,10,15,0.3)',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 700 }}>{p.title}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                          {p.milestones_completed}/{p.total_milestones} milestones · AI avg: {p.avg_ai_score}%
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>${p.budget}</span>
                        {p.blockchain_verified && (
                          <span style={{ fontSize: '0.7rem', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)', padding: '0.15rem 0.4rem', borderRadius: 4 }}>
                            ⛓ Verified
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Reviews */}
              {resume.reviews?.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Client Reviews</div>
                  {resume.reviews.map((r, i) => (
                    <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border)', fontSize: '0.9rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span style={{ color: '#fbbf24' }}>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
                        <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{r.from} · {r.project}</span>
                      </div>
                      {r.comment && <div style={{ color: 'var(--muted)', marginTop: '0.2rem' }}>{r.comment}</div>}
                    </div>
                  ))}
                </div>
              )}

              {/* Blockchain Verification Hash */}
              {resume.verification && (
                <div style={{
                  padding: '0.6rem 0.8rem', borderRadius: 8, fontSize: '0.8rem',
                  background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.2)',
                }}>
                  <div style={{ fontWeight: 700, color: '#818cf8', marginBottom: '0.3rem' }}>⛓ Blockchain Verification</div>
                  <div style={{ color: 'var(--muted)', wordBreak: 'break-all' }}>
                    Resume Hash: {resume.verification.resume_hash}
                  </div>
                  {resume.verification.blockchain_tx && (
                    <div style={{ color: 'var(--muted)', marginTop: '0.15rem' }}>
                      TX: {resume.verification.blockchain_tx}
                    </div>
                  )}
                  <div style={{ color: '#64748b', marginTop: '0.3rem', fontStyle: 'italic' }}>
                    {resume.verification.message}
                  </div>
                </div>
              )}
            </>
          )}

          {!resumeLoading && !resume && (
            <div style={{ color: 'var(--muted)' }}>
              Complete milestones to build your verified resume. Each project and skill gets recorded on the blockchain.
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  )
}
