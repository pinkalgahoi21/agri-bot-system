export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '').replace(/\/api$/, '') + '/api'
export const storageKey = 'agribot.access'
export function signOut() {
  const token = sessionStorage.getItem(storageKey)
  if (token) fetch(API_URL + '/auth/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + token }, keepalive: true }).catch(() => {})
  sessionStorage.removeItem(storageKey)
  window.dispatchEvent(new Event('signed-out'))
}
export async function api(url, options = {}) {
  const token = sessionStorage.getItem(storageKey)
  const response = await fetch(url, { ...options, headers: { ...options.headers, Authorization: 'Bearer ' + token } })
  if (response.status === 401 && token === sessionStorage.getItem(storageKey)) signOut()
  return response
}
export async function loadProfile() {
  const result = await api(API_URL + '/profile')
  if (!result.ok) throw Error('Could not open your farm profile. Please try again.')
  return (await result.json()).profile
}
