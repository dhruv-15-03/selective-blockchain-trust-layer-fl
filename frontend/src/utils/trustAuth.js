const TOKEN_KEY = 'trust_token'
const USER_KEY = 'trust_user'

function safeJsonParse(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  const parsed = safeJsonParse(raw)
  if (!parsed || !parsed.id) return null
  return parsed
}

export function isLoggedIn() {
  return Boolean(getStoredToken()) && Boolean(getStoredUser())
}

export function getUserInitial(user) {
  const name = user?.name || user?.email || ''
  const trimmed = String(name).trim()
  if (!trimmed) return 'U'
  return trimmed[0].toUpperCase()
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

