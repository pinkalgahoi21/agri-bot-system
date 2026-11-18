import { useEffect, useState } from 'react'
import './workspace.css'

import { API_URL, storageKey, loadProfile } from './session.js'
export function Access({ onReady }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [sent, setSent] = useState(false)
  const [code, setCode] = useState('')
  const [ticket, setTicket] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(() => Boolean(sessionStorage.getItem(storageKey)))
  useEffect(() => {
    let active = true
    if (sessionStorage.getItem(storageKey)) {
      loadProfile().then(profile => active && onReady(profile)).catch(err => active && setError(err.message)).finally(() => active && setBusy(false))
    }
    return () => { active = false }
  }, [onReady])
  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const endpoint = sent ? 'verify' : mode
      const result = await fetch(API_URL + '/auth/' + endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sent ? { email: email.trim(), token: code.trim(), ticket } : { email: email.trim(), password })
      })
      if (!result.ok) throw Error(result.status === 429 ? 'Too many requests. Wait before trying again.' : sent ? 'Invalid or expired confirmation code.' : mode === 'login' ? 'Sign-in failed. Check your email, password and email verification.' : 'Account creation failed. Check your email and password.')
      const { access_token, ticket: signupTicket } = await result.json()
      if (signupTicket) setTicket(signupTicket)
      if (!access_token && !sent && mode === 'signup') { setPassword(''); setSent(true); return }
      if (!access_token) throw Error('No session received. Please sign in again.')
      sessionStorage.setItem(storageKey, access_token)
      onReady(await loadProfile())
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <main className="access-card"><span className="eyebrow">AGRI-BOT / FIELD DESK</span>
    <h1>{sent ? 'Check your inbox' : mode === 'login' ? 'Welcome back' : 'Create your farm account'}</h1>
    <p>{sent ? 'Enter the signup confirmation code sent to ' + email : mode === 'login' ? 'Sign in with your email and password.' : 'Choose a password and verify your email once.'}</p>
    <form onSubmit={submit}><label>{sent ? 'One-time code' : 'Email address'}
    {sent ? <input autoFocus required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]+" value={code} onChange={event => setCode(event.target.value)} /> : <input required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} />}</label>
    {!sent && <label>Password<input required type="password" minLength={mode === 'signup' ? 8 : 1} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={event => setPassword(event.target.value)} /></label>}
    {error && <p role="alert">{error}</p>}
    <button disabled={busy} className="primary-btn">{busy ? 'Please wait...' : sent ? 'Verify email' : mode === 'login' ? 'Sign in' : 'Create account'}</button></form>
    <button disabled={busy} className="access-link" onClick={() => { if (sent) {setSent(false); setCode('')} else setMode(mode === 'login' ? 'signup' : 'login'); setError('') }}>{sent ? 'Change email or request another code' : mode === 'login' ? 'New here? Create an account' : 'Already registered? Sign in'}</button>
  </main>
}
