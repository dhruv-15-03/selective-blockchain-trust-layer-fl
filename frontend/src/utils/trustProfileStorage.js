/** Low-level profile keys scoped by role (freelancer vs client). */

function safeJsonParse(text, fallback) {
  try {
    return JSON.parse(text)
  } catch {
    return fallback
  }
}

function bioKey(userId, role) {
  return `trust_profile_${role}_bio_${userId}`
}

function skillsKey(userId, role) {
  return `trust_profile_${role}_skills_${userId}`
}

function jobsKey(userId, role) {
  return `trust_profile_${role}_jobs_${userId}`
}

/** Legacy single-namespace keys (pre-role); read for freelancer only. */
function legacyBioKey(userId) {
  return `trust_profile_bio_${userId}`
}
function legacySkillsKey(userId) {
  return `trust_profile_skills_${userId}`
}
function legacyJobsKey(userId) {
  return `trust_profile_jobs_${userId}`
}

export function getBio(userId, role) {
  if (!userId || !role) return ''
  let v = localStorage.getItem(bioKey(userId, role)) || ''
  if (!v && role === 'freelancer') {
    v = localStorage.getItem(legacyBioKey(userId)) || ''
  }
  return v
}

export function setBio(userId, role, bio) {
  if (!userId || !role) return
  localStorage.setItem(bioKey(userId, role), String(bio ?? ''))
}

export function getSkills(userId, role) {
  if (!userId || !role) return []
  let raw = localStorage.getItem(skillsKey(userId, role))
  if (!raw && role === 'freelancer') {
    raw = localStorage.getItem(legacySkillsKey(userId))
  }
  const parsed = safeJsonParse(raw, [])
  if (!Array.isArray(parsed)) return []
  return parsed.map((s) => String(s)).filter(Boolean)
}

export function setSkills(userId, role, skills) {
  if (!userId || !role) return
  const cleaned = Array.isArray(skills) ? skills.map((s) => String(s)).filter(Boolean) : []
  localStorage.setItem(skillsKey(userId, role), JSON.stringify(cleaned))
}

export function addSkill(userId, role, skill) {
  const s = String(skill ?? '').trim()
  if (!s) return
  const skills = getSkills(userId, role)
  if (skills.some((x) => x.toLowerCase() === s.toLowerCase())) return
  skills.push(s)
  setSkills(userId, role, skills)
}

export function removeSkill(userId, role, skillToRemove) {
  const s = String(skillToRemove ?? '').trim().toLowerCase()
  if (!s) return
  const skills = getSkills(userId, role)
  const next = skills.filter((x) => x.toLowerCase() !== s)
  setSkills(userId, role, next)
}

export function getJobHistory(userId, role) {
  if (!userId || !role) return []
  let raw = localStorage.getItem(jobsKey(userId, role))
  if (!raw && role === 'freelancer') {
    raw = localStorage.getItem(legacyJobsKey(userId))
  }
  const parsed = safeJsonParse(raw, [])
  if (!Array.isArray(parsed)) return []
  return parsed.map((j) => String(j)).filter(Boolean)
}

export function addJobToHistory(userId, role, jobId) {
  if (!userId || !role || jobId == null) return
  const id = String(jobId)
  const jobs = getJobHistory(userId, role)
  if (jobs.includes(id)) return
  jobs.unshift(id)
  localStorage.setItem(jobsKey(userId, role), JSON.stringify(jobs.slice(0, 50)))
}
