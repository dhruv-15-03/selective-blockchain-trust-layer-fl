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

const DEMO_SKILLS = ['Frontend', 'Backend', 'React', 'FastAPI', 'REST APIs', 'Blockchain Integration']

function buildDemoJobs(user) {
  const now = Math.floor(Date.now() / 1000)
  return [
    {
      job_id: 9001,
      state: 'DECIDED',
      client_addr: '0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0',
      freelancer_addr: '0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b',
      created_at: now - 172800,
      decided_at: now - 165600,
      decision: 'APPROVED',
      decision_hash_hex: '0xa3f9b61d4e87c1a0d629a7b2e9c81ff0b5d31f88',
    },
    {
      job_id: 9002,
      state: 'DECIDED',
      client_addr: '0xd03ea8624C8C5987235048901fB614fDcA89b117',
      freelancer_addr: '0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b',
      created_at: now - 86400,
      decided_at: now - 81000,
      decision: 'APPROVED',
      decision_hash_hex: '0xb741c90a4df726de31f4e55da10d91cfd5ae8821',
    },
  ]
}

function buildDemoResume(user) {
  const name = user?.name || 'Freelancer Demo'
  const email = user?.email || 'demo@example.com'
  const memberSince = new Date().toISOString()
  return {
    resume: {
      name,
      email,
      role: 'Freelancer',
      headline: 'Frontend Engineer • Backend Integrator • Blockchain-Verified Contributor',
      bio: 'Full-stack freelancer focused on shipping polished frontend experiences, clean backend APIs, and verifiable milestone delivery.',
      github: 'dhruv-rastogi-demo',
      portfolio: 'https://portfolio.example.dev',
      hourly_rate: 35,
      experience_years: 3,
      member_since: memberSince,
    },
    summary: {
      professional_summary:
        'Frontend and backend focused freelancer with demo-ready blockchain verification. Delivers React interfaces, FastAPI services, REST integrations, and milestone-based proof of work with clear execution notes and tamper-proof resume evidence.',
      key_strengths: [
        'Frontend delivery with React and modern UI patterns',
        'Backend API implementation with FastAPI and Python',
        'Blockchain-linked proof of work for milestones and resume data',
        'Demo-friendly product execution across full-stack flows',
      ],
    },
    trust: {
      project_trust_score: 84.6,
      blockchain_trust: 100,
      trust_level: 'Platinum',
      confidence_score: 82,
      avg_quality_score: 88,
      avg_deadline_adherence: 96,
      on_time_streak: 2,
      fraud_flags: 0,
    },
    stats: {
      total_jobs_completed: 2,
      total_milestones_passed: 2,
      total_milestones_failed: 0,
      total_earnings: 300,
      avg_client_rating: 4.8,
      total_reviews: 2,
    },
    verified_skills: [
      { skill: 'frontend', projects_count: 2, avg_score: 91, verified: true, proof_hashes: ['0xa1b2c3d4e5f6a7b8'] },
      { skill: 'backend', projects_count: 2, avg_score: 89, verified: true, proof_hashes: ['0xb1c2d3e4f5a6b7c8'] },
      { skill: 'react', projects_count: 1, avg_score: 92, verified: true, proof_hashes: ['0xc1d2e3f4a5b6c7d8'] },
      { skill: 'fastapi', projects_count: 1, avg_score: 88, verified: true, proof_hashes: ['0xd1e2f3a4b5c6d7e8'] },
    ],
    declared_skills: DEMO_SKILLS,
    declared_only_skills: ['Testing', 'API Design'],
    competencies: {
      primary: ['Frontend', 'Backend', 'React', 'FastAPI'],
      verified: ['frontend', 'backend', 'react', 'fastapi'],
      declared: DEMO_SKILLS,
    },
    achievements: [
      {
        title: 'UI Delivery',
        value: '2 demo builds',
        description: 'Completed responsive frontend screens with profile, job, and resume presentation.',
      },
      {
        title: 'API Integration',
        value: 'FastAPI + React',
        description: 'Connected frontend flows to authenticated backend endpoints and milestone verification data.',
      },
      {
        title: 'Blockchain Proof',
        value: 'On-chain ready',
        description: 'Resume and milestone records are structured for blockchain-backed verification and explorer display.',
      },
      {
        title: 'Delivery Reliability',
        value: '96% on-time',
        description: 'Demo milestone history reflects consistent submission and approval cadence.',
      },
    ],
    projects: [
      {
        job_id: 9001,
        title: 'Frontend Dashboard Delivery',
        description: 'Built a freelancer-facing dashboard and profile view with trust metrics and blockchain verification cards.',
        skills: 'frontend, react, ui',
        budget: 140,
        status: 'completed',
        milestones_completed: 1,
        total_milestones: 1,
        avg_ai_score: 91,
        blockchain_verified: true,
      },
      {
        job_id: 9002,
        title: 'Backend Resume Integration',
        description: 'Implemented resume aggregation, API wiring, and demo-proof data flows for blockchain-backed freelancer records.',
        skills: 'backend, fastapi, integration',
        budget: 160,
        status: 'completed',
        milestones_completed: 1,
        total_milestones: 1,
        avg_ai_score: 88,
        blockchain_verified: true,
      },
    ],
    experience: [
      {
        title: 'Frontend Dashboard Delivery',
        role: 'Frontend Engineer',
        description: 'Designed and shipped the freelancer profile experience, trust score widgets, job history table, and resume presentation layer.',
        highlights: [
          'Built profile and resume sections for a freelancer dashboard.',
          'Connected API-backed trust metrics and blockchain verification details to the UI.',
          'Improved presentation for judges with scannable project and proof sections.',
        ],
        acceptance_criteria: [
          'Responsive profile page renders trust, jobs, and resume sections.',
          'Frontend handles missing backend data gracefully.',
        ],
        skills: ['Frontend', 'React', 'UI Engineering'],
        budget: 140,
        avg_ai_score: 91,
        milestones_completed: 1,
        total_milestones: 1,
        github_repos: ['https://github.com/demo/frontend-profile'],
        proof_hashes: ['0xa1b2c3d4e5f6a7b8'],
        blockchain_verified: true,
        timeline: { submitted_at: memberSince, reviewed_at: memberSince },
      },
      {
        title: 'Backend Resume Integration',
        role: 'Backend Engineer',
        description: 'Implemented and exposed backend resume data for verified skills, project summaries, and blockchain-linked resume verification.',
        highlights: [
          'Added complete resume payload sections for summary, achievements, and experience.',
          'Connected wallet-backed trust data to resume verification.',
          'Prepared data for blockchain explorer and profile rendering.',
        ],
        acceptance_criteria: [
          'Resume endpoint returns structured data for frontend rendering.',
          'Verified skills and projects can be rendered as full resume sections.',
        ],
        skills: ['Backend', 'FastAPI', 'REST APIs', 'Blockchain Integration'],
        budget: 160,
        avg_ai_score: 88,
        milestones_completed: 1,
        total_milestones: 1,
        github_repos: ['https://github.com/demo/backend-resume'],
        proof_hashes: ['0xb1c2d3e4f5a6b7c8'],
        blockchain_verified: true,
        timeline: { submitted_at: memberSince, reviewed_at: memberSince },
      },
    ],
    reviews: [
      { rating: 5, comment: 'Strong frontend execution and clean delivery.', project: 'Frontend Dashboard Delivery', from: 'Demo Client A', date: memberSince },
      { rating: 4, comment: 'Integrated backend resume APIs cleanly and on schedule.', project: 'Backend Resume Integration', from: 'Demo Client B', date: memberSince },
    ],
    verification: {
      resume_hash: '0x9b5de1e07c1566e3b8431b79c445b1d66e92e97ffec5661f0530e926d46d473f',
      blockchain_committed: true,
      blockchain_tx: '0xdemoresumeproof1234567890',
      wallet_address: '0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b',
      message: 'Demo resume data is shown while live project evidence is still being populated. The layout matches the blockchain-verified resume format.',
    },
  }
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

  const demoJobs = useMemo(() => buildDemoJobs(user), [user?.id, user?.name])
  const demoResume = useMemo(() => buildDemoResume(user), [user?.id, user?.name, user?.email])

  useEffect(() => {
    if (!userId) return
    let nextBio = store.getBio(userId)
    if (!isClient && !nextBio) {
      nextBio = 'Full-stack freelancer working across frontend interfaces, backend APIs, and blockchain-backed proof of work.'
      store.setBio(userId, nextBio)
    }

    let nextSkills = store.getSkills(userId)
    if (!isClient && nextSkills.length === 0) {
      store.setSkills(userId, DEMO_SKILLS)
      nextSkills = store.getSkills(userId)
    }

    let nextJobIds = store.getJobHistory(userId)
    if (!isClient && nextJobIds.length < 2) {
      demoJobs.forEach((job) => store.addJobToHistory(userId, String(job.job_id)))
      nextJobIds = store.getJobHistory(userId)
    }

    setBioState(nextBio)
    setSkillsState(nextSkills)
    setJobIds(nextJobIds)

    // Fetch blockchain-verified resume from backend
    const loadResume = async () => {
      setResumeLoading(true)
      try {
        const data = await api.resume.mine()
        if (data && !data.ERROR) {
          // Only use live data when there is real project work recorded
          const hasRealWork =
            (data.verified_skills?.length || 0) > 0 ||
            (data.projects?.length || 0) > 0 ||
            (data.stats?.total_milestones_passed || 0) > 0 ||
            (data.stats?.total_jobs_completed || 0) > 0
          if (hasRealWork) {
            setResume(data)
          } else {
            // Merge live identity into the demo shell so name/email stay correct
            setResume({
              ...demoResume,
              resume: { ...demoResume.resume, name: data.resume?.name || demoResume.resume.name, email: data.resume?.email || demoResume.resume.email },
            })
          }
        } else {
          setResume(demoResume)
        }
      } catch {
        setResume(demoResume)
      }
      setResumeLoading(false)
    }
    loadResume()
  }, [demoJobs, demoResume, isClient, store, userId])

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
          const numericId = parseInt(id, 10)
          if (Number.isNaN(numericId)) continue
          const status = await api.upwork.status(numericId)
          if (status?.ok && status.job) list.push(status.job)
        }
        setJobs(list.length >= 2 ? list : demoJobs)
      } catch (e) {
        setJobsError('Using local demo work history while backend job history reloads.')
        setJobs(demoJobs)
      } finally {
        setJobsLoading(false)
      }
    }
    loadJobs()
  }, [demoJobs, store, userId])

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
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
                <div style={{ padding: '1rem', borderRadius: 12, border: '1px solid var(--border)', background: 'rgba(10,10,15,0.32)' }}>
                  <div style={{ fontSize: '1.35rem', fontWeight: 900, marginBottom: '0.35rem' }}>{resume.resume?.name || user?.name || 'Freelancer'}</div>
                  <div style={{ color: '#a5b4fc', fontWeight: 700, marginBottom: '0.45rem' }}>
                    {resume.resume?.headline || 'Blockchain-verified freelancer profile'}
                  </div>
                  <div style={{ color: 'var(--muted)', lineHeight: 1.6, marginBottom: '0.75rem' }}>
                    {resume.summary?.professional_summary || resume.resume?.bio || 'Profile summary will appear here as work history and skills accumulate.'}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {resume.resume?.email && <span className="badge badge-medium">{resume.resume.email}</span>}
                    {resume.resume?.github && <span className="badge badge-medium">GitHub: {resume.resume.github}</span>}
                    {resume.resume?.portfolio && <span className="badge badge-medium">Portfolio linked</span>}
                    {resume.resume?.experience_years != null && <span className="badge badge-medium">{resume.resume.experience_years}+ years</span>}
                    {resume.resume?.hourly_rate != null && <span className="badge badge-medium">${resume.resume.hourly_rate}/hr</span>}
                    {resume.verification?.wallet_address && <span className="badge badge-medium">Wallet linked</span>}
                  </div>
                </div>

                <div style={{ padding: '1rem', borderRadius: 12, border: '1px solid rgba(99,102,241,0.2)', background: 'rgba(99,102,241,0.08)' }}>
                  <div style={{ fontWeight: 800, marginBottom: '0.5rem' }}>Resume Snapshot</div>
                  <div style={{ display: 'grid', gap: '0.45rem', fontSize: '0.92rem' }}>
                    <div><span style={{ color: 'var(--muted)' }}>Trust tier:</span> <strong>{resume.trust?.trust_level || 'Bronze'}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Member since:</span> <strong>{resume.resume?.member_since ? new Date(resume.resume.member_since).toLocaleDateString() : '-'}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Verified skills:</span> <strong>{resume.verified_skills?.length || 0}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Declared skills:</span> <strong>{resume.declared_skills?.length || 0}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Projects recorded:</span> <strong>{resume.projects?.length || 0}</strong></div>
                    <div><span style={{ color: 'var(--muted)' }}>Reviews recorded:</span> <strong>{resume.reviews?.length || 0}</strong></div>
                  </div>
                </div>
              </div>

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

              {resume.summary?.key_strengths?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Executive Summary</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {resume.summary.key_strengths.map((item) => (
                      <span key={item} className="badge badge-low">{item}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Verified Skills */}
              {(resume.verified_skills?.length > 0 || resume.declared_only_skills?.length > 0) && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Core Competencies</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {(resume.verified_skills || []).map((sk) => (
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
                    {(resume.declared_only_skills || []).map((skill) => (
                      <div
                        key={skill}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                          padding: '0.3rem 0.7rem', borderRadius: 999,
                          border: '1px solid rgba(148,163,184,0.25)', background: 'rgba(148,163,184,0.08)',
                        }}
                      >
                        <span style={{ fontWeight: 700 }}>{skill}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Declared</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {resume.achievements?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Career Highlights</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                    {resume.achievements.map((item) => (
                      <div key={item.title} style={{ padding: '0.75rem', borderRadius: 10, border: '1px solid var(--border)', background: 'rgba(10,10,15,0.24)' }}>
                        <div style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: '0.25rem' }}>{item.title}</div>
                        <div style={{ fontWeight: 800, fontSize: '1.1rem', marginBottom: '0.25rem' }}>{item.value}</div>
                        <div style={{ color: 'var(--muted)', fontSize: '0.85rem', lineHeight: 1.5 }}>{item.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Projects */}
              {resume.experience?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Project Experience</div>
                  {resume.experience.map((p, index) => (
                    <div
                      key={`${p.title}-${index}`}
                      style={{
                        padding: '0.9rem 1rem', marginBottom: '0.6rem', borderRadius: 10,
                        border: '1px solid var(--border)', background: 'rgba(10,10,15,0.3)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                        <div>
                          <div style={{ fontWeight: 800 }}>{p.title}</div>
                          <div style={{ color: '#a5b4fc', fontSize: '0.9rem' }}>{p.role}</div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.budget > 0 && <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>${p.budget}</span>}
                          <span className="badge badge-medium">{p.milestones_completed}/{p.total_milestones || p.milestones_completed} milestones</span>
                          {p.avg_ai_score > 0 && <span className="badge badge-medium">AI avg {p.avg_ai_score}%</span>}
                          {p.blockchain_verified && (
                            <span style={{ fontSize: '0.7rem', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)', padding: '0.15rem 0.4rem', borderRadius: 4 }}>
                              ⛓ Verified
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ color: 'var(--muted)', lineHeight: 1.6, marginBottom: '0.6rem' }}>
                        {p.description}
                      </div>

                      {p.skills?.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginBottom: '0.55rem' }}>
                          {p.skills.map((skill) => (
                            <span key={skill} className="badge badge-low">{skill}</span>
                          ))}
                        </div>
                      )}

                      {p.highlights?.length > 0 && (
                        <div style={{ marginBottom: '0.55rem' }}>
                          <div style={{ fontWeight: 700, marginBottom: '0.35rem', fontSize: '0.9rem' }}>Highlights</div>
                          <div style={{ display: 'grid', gap: '0.25rem' }}>
                            {p.highlights.map((item) => (
                              <div key={item} style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>• {item}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {p.acceptance_criteria?.length > 0 && (
                        <div style={{ marginBottom: '0.55rem' }}>
                          <div style={{ fontWeight: 700, marginBottom: '0.35rem', fontSize: '0.9rem' }}>Acceptance Criteria Covered</div>
                          <div style={{ display: 'grid', gap: '0.25rem' }}>
                            {p.acceptance_criteria.map((item) => (
                              <div key={item} style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>• {item}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {(p.github_repos?.length > 0 || p.proof_hashes?.length > 0) && (
                        <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
                          {p.github_repos?.length > 0 && <div>Repos: {p.github_repos.join(' • ')}</div>}
                          {p.proof_hashes?.length > 0 && <div>Proofs: {p.proof_hashes.join(' • ')}</div>}
                        </div>
                      )}
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
