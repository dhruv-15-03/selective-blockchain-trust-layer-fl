/**
 * Profile + job history for client accounts (separate localStorage namespace).
 */
import * as t from './trustProfileStorage'

const R = 'client'

export const getBio = (userId) => t.getBio(userId, R)
export const setBio = (userId, bio) => t.setBio(userId, R, bio)
export const getSkills = (userId) => t.getSkills(userId, R)
export const setSkills = (userId, skills) => t.setSkills(userId, R, skills)
export const addSkill = (userId, skill) => t.addSkill(userId, R, skill)
export const removeSkill = (userId, skill) => t.removeSkill(userId, R, skill)
export const getJobHistory = (userId) => t.getJobHistory(userId, R)
export const addJobToHistory = (userId, jobId) => t.addJobToHistory(userId, R, jobId)
