import * as freelancer from './freelancerProfileStorage'
import * as client from './clientProfileStorage'

/** Resolve profile storage module from logged-in user (default: freelancer). */
export function getProfileStore(user) {
  return user?.role === 'client' ? client : freelancer
}
