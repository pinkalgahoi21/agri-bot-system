import { useState, useRef, useEffect } from 'react'
import { Send, Image as ImageIcon, Mic, Square } from 'lucide-react'

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const API_URL = rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api`;

function App() {
  const [user, setUser] = useState(null)
  
  if (!user) {
    return <Onboarding setUser={setUser} />
  }
  
  return <Chat user={user} />
}

function Onboarding({ setUser }) {
  const [formData, setFormData] = useState({
    user_id: Math.floor(Math.random() * 1000000), // mock ID for web
    name: '',
    city: '',
    crop: ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    const data = new FormData()
    data.append('user_id', formData.user_id)
    data.append('name', formData.name)
    data.append('city', formData.city)
    data.append('location', formData.city)
    data.append('crop', formData.crop)

    try {
      const res = await fetch(`${API_URL}/profile`, {
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
          
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? 'Creating Profile...' : 'Start Chatting'}
          </button>
        </form>
      </div>
    </div>
  )
}

function Chat({ user }) {
  const [messages, setMessages] = useState([
    { role: 'bot', text: `Hello ${user.name}! I'm ready to help you with your ${user.crop} crop in ${user.city}. How can I assist you today?` }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  
  // Voice Recording state
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const messagesEndRef = useRef(null)
  
  const fileInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendTextMessage = async (e) => {
    e?.preventDefault()
    if (!input.trim() || loading) return

    const userText = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: userText }])
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.user_id, message: userText })
      })
      const data = await res.json()
      if (res.ok) {
        setMessages(prev => [...prev, { role: 'bot', text: data.response }])
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + (data.detail || data.error) }])
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Failed to connect to backend.' }])
    }
    setLoading(false)
  }

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // Create a local preview URL for the uploaded image
    const previewUrl = URL.createObjectURL(file)
    setMessages(prev => [...prev, { role: 'user', text: `📸 Uploaded image: ${file.name}`, image: previewUrl }])
    setLoading(true)
    
    const formData = new FormData()
    formData.append('user_id', user.user_id)
    formData.append('image', file)

    // 120-second timeout for vision analysis (can be slow on free tier)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000)

    try {
      const res = await fetch(`${API_URL}/vision`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      const data = await res.json()
      if (res.ok) {
        const diag = data.response
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
    } catch (err) {
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
    formData.append('user_id', user.user_id)
    formData.append('audio', audioBlob, 'voice.webm')

    try {
      const res = await fetch(`${API_URL}/voice`, {
        method: 'POST',
        body: formData
      })
      
      if (res.ok) {
        // If it's audio, play it and show the transcription if provided in headers/etc
        const contentType = res.headers.get("content-type") || ""
        if (contentType.includes("audio")) {
          const blob = await res.blob()
          const audioUrl = URL.createObjectURL(blob)
          const audio = new Audio(audioUrl)
          audio.play()
          setMessages(prev => [...prev, { role: 'bot', text: '🔊 Audio response received (playing...)' }])
        } else {
          const data = await res.json()
          setMessages(prev => [...prev, { role: 'bot', text: data.response || data.transcribed }])
        }
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: 'Failed to process voice.' }])
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Error connecting to backend for voice.' }])
    }
    setLoading(false)
  }

  return (
    <div className="app-container">
      <div className="chat-container">
        <header className="chat-header">
          <div className="header-info">
            <div className="avatar">🌱</div>
            <div className="header-text">
              <h2>Agri-Bot</h2>
              <p>Active</p>
            </div>
          </div>
          <div className="header-info" style={{ flexDirection: 'row-reverse' }}>
            <div className="avatar" style={{ background: 'rgba(255,255,255,0.1)' }}>{user.name.charAt(0)}</div>
            <div className="header-text" style={{ textAlign: 'right' }}>
              <h2>{user.name}</h2>
              <p style={{ color: '#cbd5e1', justifyContent: 'flex-end' }}>{user.crop} • {user.city}</p>
            </div>
          </div>
        </header>
        
        <main className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.image && (
                <img 
                  src={msg.image} 
                  alt="Uploaded crop" 
                  className="message-image"
                />
              )}
              {msg.text}
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

        <form className="chat-input-area" onSubmit={sendTextMessage}>
          <input 
            type="file" 
            accept="image/*" 
            style={{display: 'none'}} 
            ref={fileInputRef}
            onChange={handleImageUpload}
          />
          <button type="button" className="icon-btn" onClick={() => fileInputRef.current?.click()} title="Upload Crop Image">
            <ImageIcon size={20} />
          </button>
          
          <input 
            className="chat-input" 
            placeholder="Type your question..." 
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading || isRecording}
          />
          
          {isRecording ? (
            <button type="button" className="icon-btn recording" onClick={stopRecording} title="Stop Recording">
              <Square size={20} />
            </button>
          ) : (
            <button type="button" className="icon-btn" onClick={startRecording} title="Record Voice Note" disabled={loading}>
              <Mic size={20} />
            </button>
          )}

          <button type="submit" className="icon-btn send" disabled={!input.trim() || loading || isRecording}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
