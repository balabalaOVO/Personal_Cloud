/**
 * Auth API calls
 */
import api from './client'

export async function login(username: string, password: string) {
  const { data } = await api.post('/auth/login', { username, password })
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  return data
}
