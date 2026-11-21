import { useState, useRef, useEffect } from 'react'
import { Send, Image as ImageIcon, Mic, Square } from 'lucide-react'

import { Access } from './Access.jsx'
import { api, API_URL, signOut } from './session.js'

function App() {
  const [profile, setProfile] = useState(undefined)
  const [generation, reset] = useState(0)
  useEffect(() => {
    const expired = () => { setProfile(undefined); reset(value => value + 1) }
    window.addEventListener('signed-out', expired)
    return () => window.removeEventListener('signed-out', expired)
  }, [])
  if (profile === undefined) return <Access key={generation} onReady={setProfile} />
  if (!profile) return <Onboarding setUser={setProfile} />
  return <Chat user={profile} />
}

function Onboarding({ setUser }) {
  const [formData, setFormData] = useState({
    name: '',
    city: '',
    crop: ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    const data = new FormData()
    data.append('name', formData.name)
    data.append('city', formData.city)
    data.append('location', formData.city)
    data.append('crop', formData.crop)
    for (const key of ['state', 'stage', 'language', 'land_size']) data.append(key, formData[key] || '')

    try {
      const res = await api(`${API_URL}/profile`, {
        method: 'POST',
        body: data
      })
      if (res.ok) {
        setUser(formData)
      } else {
        alert('Failed to create profile')
      }
    } catch (err) {
      console.error(err)
      alert('Error connecting to backend')
    }
    setLoading(false)
  }

  return (
    <div className="app-container">
      <div className="onboarding-screen">
        <h1>🌱 Agri-Bot</h1>
        <p>Your AI assistant for crop diseases, weather, and schemes.</p>
        
        <form className="onboarding-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Full Name</label>
            <input 
              required
              className="glass-input" 
              placeholder="e.g. Ramesh Singh"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
            />
          </div>
          <div className="input-group">
            <label>City / Location</label>
            <input 
              required
              className="glass-input" 
              placeholder="e.g. Pune, Maharashtra"
              value={formData.city}
              onChange={e => setFormData({...formData, city: e.target.value})}
            />
          </div>
          <div className="input-group">
            <label>Main Crop</label>
            <input 
              required
              className="glass-input" 
              placeholder="e.g. Tomato"
              value={formData.crop}
              onChange={e => setFormData({...formData, crop: e.target.value})}
            />
          </div>
          
          {Object.entries({state:'State', language:'Preferred language', land_size:'Land size (optional)'}).map(([key,label]) =>
            <label key={key}>{label}<input className="glass-input" value={formData[key] || ''} onChange={event => setFormData({...formData,[key]:event.target.value})} /></label>)}
          <label>Crop stage<select value={formData.stage || ''} onChange={event => setFormData({...formData,stage:event.target.value})}>
            <option value="">Not sure</option>{['land preparation','sowing','germination','vegetative','flowering','fruiting','harvesting','post-harvest'].map(stage => <option key={stage}>{stage}</option>)}
          </select></label>
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? 'Creating Profile...' : 'Start Chatting'}
          </button>
        </form>
      </div>
    </div>
  )
}

function Chat({ user }) {
  const [photoLanguage, setPhotoLanguage] = useState('en')
  const [messages, setMessages] = useState([
    { role: 'bot', text: `Hello ${user.name}! I'm ready to help you with your ${user.crop} crop in ${user.city}. How can I assist you today?` }
  ])
  const [input, setInput] = useState('')
  useEffect(() => {
    const abort = new AbortController()
    api(API_URL + '/chat/history', {signal: abort.signal}).then(async response => {
      if (!response.ok) return
      const data = await response.json()
      if (!abort.signal.aborted && data.messages.length) setMessages(previous => [...previous.slice(0, 1), ...data.messages, ...previous.slice(1)])
    }).catch(() => {})
    return () => abort.abort()
  }, [])
  const [photo, setPhoto] = useState(null)
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo.url) }, [photo])
  const [loading, setLoading] = useState(false)
  
  // Voice Recording state
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const messagesEndRef = useRef(null)
  
  const fileInputRef = useRef(null)
  const composerRef = useRef(null)
  const topics = [
    ['Weather', 'How is the weather for ' + user.crop + '?'],
    ['Crop health', 'My ' + user.crop + ' has these symptoms: '],
    ['Schemes', 'Which farm schemes should I check for ' + user.crop + ' in ' + user.city + '?'],
    ['Plan my week', 'What should I check in my ' + user.crop + ' field this week?']
  ]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendTextMessage = async (e) => {
    e?.preventDefault()
    if (loading || isRecording) return
    if (photo) return sendPhoto(photo.file, input.trim())
    if (!input.trim() || loading) return

    const userText = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: userText }])
    setLoading(true)

    try {
      const res = await api(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      })
      const data = await res.json()
      if (res.ok) {
        setMessages(prev => [...prev, { role: 'bot', report: data.advisory, text: data.response }])
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + (data.detail || data.error) }])
      }
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Failed to connect to backend.' }])
    }
    setLoading(false)
  }

  const sendPhoto = async (file, caption) => {
    setPhoto(null)
    setInput('')
    
    // Read file as base64 data URL for persistent preview
    const reader = new FileReader()
    reader.onload = (event) => {
      setMessages(prev => [...prev, { role: 'user', text: caption, image: event.target.result }])
    }
    reader.readAsDataURL(file)
    
    setLoading(true)
    
    const formData = new FormData()
    formData.append('image', file)
    formData.append('language', photoLanguage)
    formData.append('caption', caption)

    // 120-second timeout for vision analysis (can be slow on free tier)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000)

    try {
      const res = await api(`${API_URL}/vision`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      const data = await res.json()
      if (res.ok) {
        const diag = data.response
        if (diag.kind === 'crop_notice') {
          setMessages(prev => [...prev, { role: 'bot', text: diag.message }])
          setLoading(false)
          if (fileInputRef.current) fileInputRef.current.value = ''
          return
        }
        const parts = [
          `🌿 Identified Crop: ${diag.identified_crop || 'Unknown'}`,
          `🦠 Disease: ${diag.disease || 'Unknown'} (${diag.confidence || 'Low'} confidence)`,
          `📊 Severity: ${diag.severity || 'Unknown'}`,
          `🔍 Cause: ${diag.cause || 'Unknown'}`,
          ``,
          `🛡️ Prevention:`,
          ...(diag.prevention || []).map(p => '• ' + p),
          ``,
          `⏰ Urgency: ${diag.urgency || 'Monitor'}`
        ]
        if (diag.treatment) parts.push('', diag.treatment)
        setMessages(prev => [...prev, { role: 'bot', text: parts.join('\n') }])
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: '❌ Error analyzing image: ' + (data.detail || 'Unknown error. Please try again.') }])
      }
    } catch (err) {
      clearTimeout(timeoutId)
      if (err.name === 'AbortError') {
        setMessages(prev => [...prev, { role: 'bot', text: '⏱️ Image analysis timed out. The server may be starting up — please try again in a minute.' }])
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: '❌ Failed to connect to backend for image analysis.' }])
      }
    }
    setLoading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' }) // browser standard
        sendAudioMessage(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch {
      alert("Could not access microphone.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const sendAudioMessage = async (audioBlob) => {
    setMessages(prev => [...prev, { role: 'user', text: '🎤 Voice message sent' }])
    setLoading(true)

    const formData = new FormData()
    formData.append('audio', audioBlob, 'voice.webm')

    try {
      const res = await api(`${API_URL}/voice`, {
        method: 'POST',
        body: formData
      })
      
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'bot', report: data.advisory, text: data.response, transcript: data.transcribed, audio: data.audio_base64 }])
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: 'Failed to process voice.' }])
      }
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Error connecting to backend for voice.' }])
    }
    setLoading(false)
  }

  return (
    <div className="app-container field-desk">
      <aside className="farm-rail">
        <div><span className="desk-kicker">AGRI-BOT</span><h2>My field desk</h2><p>{user.name} · {user.city}</p></div>
        <div className="crop-badge">Growing <strong>{user.crop}</strong></div>
        <nav aria-label="Question starters"><span className="desk-kicker">START A QUESTION</span>
          {topics.map(([label, prompt]) => <button key={label} type="button" disabled={loading || isRecording || Boolean(photo) || Boolean(input.trim())}
            onClick={() => {setInput(prompt); composerRef.current?.focus()}}>{label}<span aria-hidden="true">↗</span></button>)}
        </nav>
      </aside>
      <div className="chat-container">
        <header className="chat-header"><div><span className="desk-kicker">FIELD ADVISORY</span><h1>Farm conversation</h1></div>
          <button className="access-link" onClick={signOut}>Sign out</button>
        </header>
        <label className="photo-language">Photo advice language <select value={photoLanguage} onChange={event => setPhotoLanguage(event.target.value)}>
          {Object.entries({en:'English', hi:'हिन्दी', mr:'मराठी', ta:'தமிழ்', te:'తెలుగు', bn:'বাংলা', kn:'ಕನ್ನಡ', gu:'ગુજરાતી', ml:'മലയാളം', pa:'ਪੰਜਾਬੀ', ur:'اردو'}).map(([code,label]) => <option key={code} value={code}>{label}</option>)}
        </select></label>
        
        <main className="chat-messages" aria-label="Conversation">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.image && (
                <img 
                  src={msg.image} 
                  alt="Uploaded crop" 
                  className="message-image"
                />
              )}
              {msg.transcript && <p><strong>Heard:</strong> {msg.transcript}</p>}
              {msg.report ? <article><h3>{msg.report.title}</h3>{msg.report.sections.map((part, index) => <section key={index}><h4>{part.heading}</h4><p>{part.body}</p></section>)}</article> : msg.text}
              {msg.audio && <audio controls preload="none" src={'data:audio/mpeg;base64,' + msg.audio} />}
            </div>
          ))}
          {loading && (
            <div className="message bot">
              <div className="thinking-dots">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        {photo && <div className="photo-draft">
          <img src={photo.url} width="48" height="48" style={{ objectFit: "cover", verticalAlign: "middle", margin: ".5rem" }} alt="Photo ready to send" />
          <span>Photo attached · not sent</span>
          <button type="button" className="access-link" onClick={() => setPhoto(null)}>Remove</button>
        </div>}
        <form className="chat-input-area" onSubmit={sendTextMessage}>
          <input 
            type="file" 
            accept="image/*" 
            style={{display: 'none'}} 
            ref={fileInputRef}
            onChange={event => {
              const selected = event.target.files?.[0]
              if (selected) setPhoto({ file: selected, url: URL.createObjectURL(selected) })
              event.target.value = ''
            }}
          />
          <button type="button" className="icon-btn" disabled={loading || isRecording} onClick={() => fileInputRef.current?.click()} title="Attach crop photo">
            <ImageIcon size={20} />
          </button>
          
          <input 
            className="chat-input" ref={composerRef} aria-label="Your message or photo caption"
            placeholder={photo ? "Add a caption (optional)..." : "Ask a question or attach a crop photo..."}
            maxLength={photo ? 1024 : undefined}
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading || isRecording}
          />
          
          {isRecording ? (
            <button type="button" className="icon-btn recording" onClick={stopRecording} title="Stop Recording">
              <Square size={20} />
            </button>
          ) : (
            <button type="button" className="icon-btn" onClick={startRecording} title="Record Voice Note" disabled={loading || Boolean(photo)}>
              <Mic size={20} />
            </button>
          )}

          <button type="submit" aria-label="Send message" className="icon-btn send" disabled={(!input.trim() && !photo) || (photo && input.trim().length > 1024) || loading || isRecording}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
