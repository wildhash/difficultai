import { useState, useEffect, useRef } from 'react'
import { Room } from 'livekit-client'
import './App.css'

function App() {
  // UI State
  const [connectionState, setConnectionState] = useState('disconnected')
  const [transcripts, setTranscripts] = useState([])
  
  // Room Configuration
  const [roomName, setRoomName] = useState('')
  const [livekitUrl, setLivekitUrl] = useState('')
  const [accessToken, setAccessToken] = useState('')
  
  // Scenario Configuration
  const [persona, setPersona] = useState('ELITE_INTERVIEWER')
  const [company, setCompany] = useState('TechCorp')
  const [role, setRole] = useState('Senior Software Engineer')
  const [stakes, setStakes] = useState('Final round interview for $250k position')
  const [userGoal, setUserGoal] = useState('Demonstrate technical expertise and secure job offer')
  const [difficulty, setDifficulty] = useState(0.5)
  
  // LiveKit Room
  const roomRef = useRef(null)
  const audioElementRef = useRef(null)
  const mountedRef = useRef(false)
  
  // Generate scenario JSON
  const getScenarioJSON = () => {
    return JSON.stringify({
      persona_type: persona,
      company,
      role,
      stakes,
      user_goal: userGoal,
      difficulty: parseFloat(difficulty),
    }, null, 2)
  }

  const normalizeRole = (rawRole, participantIdentity) => {
    if (typeof rawRole === 'string' && rawRole.trim()) {
      const roleValue = rawRole.trim().toLowerCase()
      if (roleValue === 'agent' || roleValue === 'assistant') return 'Agent'
      if (roleValue === 'user' || roleValue === 'participant') return 'User'
      if (roleValue === 'system') return 'System'
      return 'User'
    }

    const identity = typeof participantIdentity === 'string' ? participantIdentity.toLowerCase() : ''
    if (identity.startsWith('agent-') || identity.endsWith('-agent')) return 'Agent'
    return 'User'
  }
  
  // Connect to room
  const connectToRoom = async () => {
    if (roomRef.current) return
    if (!livekitUrl.trim() || !accessToken.trim() || !roomName.trim()) {
      alert('Please fill in all connection fields: LiveKit URL, Access Token, and Room Name')
      return
    }
    
    const room = new Room()
    roomRef.current = room
    try {
      setConnectionState('connecting')
      setTranscripts([])
      
      // Set up event listeners
      room.on('trackSubscribed', (track, publication, participant) => {
        if (roomRef.current !== room) return
        console.log('Track subscribed:', track.kind, 'from', participant.identity)
        
        if (track.kind === 'audio' && audioElementRef.current) {
          track.attach(audioElementRef.current)
        }
      })
      
      room.on('trackUnsubscribed', (track) => {
        console.log('Track unsubscribed:', track.kind)
        track.detach()
      })
      
      room.on('disconnected', () => {
        if (roomRef.current !== room) return
        roomRef.current = null
        console.log('Disconnected from room')
        setConnectionState('disconnected')
      })
      
      room.on('dataReceived', (payload, participant) => {
        if (roomRef.current !== room) return
        // Handle transcripts or other data
        const decoder = new TextDecoder()
        const data = decoder.decode(payload)
        
        try {
          const parsed = JSON.parse(data)
          if (parsed?.type === 'transcript' && typeof parsed.text === 'string') {
            const role = normalizeRole(parsed.role, participant?.identity)

            setTranscripts(prev => [...prev, {
              role,
              text: parsed.text,
              timestamp: new Date().toLocaleTimeString(),
            }])
          }
        } catch {
          // Other room data is not necessarily a transcript or valid JSON.
        }
      })
      
      // Connect to room
      await room.connect(livekitUrl.trim(), accessToken.trim())
      if (roomRef.current !== room) {
        await room.disconnect()
        return
      }
      if (room.name !== roomName.trim()) {
        throw new Error('The token room does not match the entered Room Name')
      }
      console.log('Connected to room:', room.name)
      
      // Publish microphone audio
      await room.localParticipant.setMicrophoneEnabled(true)
      if (roomRef.current !== room) {
        await room.disconnect()
        return
      }
      console.log('Microphone enabled')
      
      setConnectionState('connected')
      
      // Add initial transcript entry
      setTranscripts(prev => [...prev, {
        role: 'System',
        text: `Connected to room: ${room.name}. Speak to start your training session.`,
        timestamp: new Date().toLocaleTimeString(),
      }])
      
    } catch (error) {
      const isCurrent = roomRef.current === room
      if (isCurrent) roomRef.current = null
      try {
        await room.disconnect()
      } catch (cleanupError) {
        console.error('Room cleanup failed:', cleanupError)
      }
      if (!isCurrent || !mountedRef.current || roomRef.current) return
      console.error('Failed to connect:', error)
      setConnectionState('disconnected')
      alert(`Connection failed: ${error.message}`)
    }
  }
  
  // Disconnect from room
  const disconnectFromRoom = async () => {
    const room = roomRef.current
    if (!room) return
    // Invalidate pending connect/microphone work before awaiting the SDK.
    roomRef.current = null
    setConnectionState('disconnecting')
    try {
      await room.disconnect()
    } catch (error) {
      console.error('Failed to disconnect:', error)
    } finally {
      if (mountedRef.current && !roomRef.current) {
        setConnectionState('disconnected')
        setTranscripts(prev => [...prev, {
          role: 'System',
          text: 'Disconnected from room.',
          timestamp: new Date().toLocaleTimeString(),
        }])
      }
    }
  }
  
  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      const room = roomRef.current
      roomRef.current = null
      if (room) {
        room.disconnect().catch(error => console.error('Room cleanup failed:', error))
      }
    }
  }, [])
  
  return (
    <div className="app-container">
      <div className="header">
        <h1>DifficultAI</h1>
        <p className="subtitle">Voice-First Adversarial Training</p>
      </div>
      
      {connectionState === 'disconnected' && (
        <div className="setup-panel">
          <div className="instructions">
            <h3>🎯 Quick Start</h3>
            <ul>
              <li><strong>Option 1:</strong> Use LiveKit Cloud Agents Playground - Copy scenario JSON and paste in room metadata</li>
              <li><strong>Option 2:</strong> Enter your LiveKit credentials below and connect directly</li>
            </ul>
          </div>
          
          <div className="section">
            <h3>Scenario Configuration</h3>
            
            <div className="form-group">
              <label>Persona Type:</label>
              <select value={persona} onChange={(e) => setPersona(e.target.value)}>
                <option value="ELITE_INTERVIEWER">Elite Interviewer</option>
                <option value="ANGRY_CUSTOMER">Angry Customer</option>
                <option value="TOUGH_NEGOTIATOR">Tough Negotiator</option>
                <option value="SKEPTICAL_INVESTOR">Skeptical Investor</option>
                <option value="DEMANDING_CLIENT">Demanding Client</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Company:</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g., TechCorp"
              />
            </div>
            
            <div className="form-group">
              <label>Role:</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g., Senior Software Engineer"
              />
            </div>
            
            <div className="form-group">
              <label>Stakes:</label>
              <textarea
                value={stakes}
                onChange={(e) => setStakes(e.target.value)}
                placeholder="What's at stake in this conversation?"
                rows={2}
              />
            </div>
            
            <div className="form-group">
              <label>Your Goal:</label>
              <textarea
                value={userGoal}
                onChange={(e) => setUserGoal(e.target.value)}
                placeholder="What are you trying to achieve?"
                rows={2}
              />
            </div>
            
            <div className="form-group">
              <label>Difficulty (0-1): {difficulty}</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              />
              <small>0 = easy, 0.5 = moderate, 1 = maximum pressure</small>
            </div>
            
            <button className="btn-primary" onClick={() => {
              const json = getScenarioJSON()
              navigator.clipboard.writeText(json)
              alert('Scenario JSON copied to clipboard!\n\nPaste this into LiveKit Agents Playground as room metadata.\n\nNote: This is not sent automatically when connecting directly.')
            }}>
              📋 Copy Scenario JSON
            </button>
          </div>
          
          <div className="section">
            <h3>Connection Settings</h3>
            <p className="note">
              <strong>Note:</strong> To connect directly, you need a LiveKit access token.
              See README for token generation instructions.
              Scenario JSON is only used if it was set as room metadata when the room was created.
            </p>
            
            <div className="form-group">
              <label>LiveKit URL:</label>
              <input
                type="text"
                value={livekitUrl}
                onChange={(e) => setLivekitUrl(e.target.value)}
                placeholder="wss://your-project.livekit.cloud"
              />
            </div>
            
            <div className="form-group">
              <label>Room Name:</label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="my-training-room"
              />
            </div>
            
            <div className="form-group">
              <label>Access Token:</label>
              <textarea
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                placeholder="Paste your LiveKit access token here"
                rows={3}
              />
            </div>
            
            <button 
              className="btn-success" 
              onClick={connectToRoom}
              disabled={!livekitUrl || !accessToken || !roomName}
            >
              🎙️ Connect & Start Session
            </button>
          </div>
        </div>
      )}
      
      {connectionState === 'connecting' && (
        <div className="status-panel">
          <div className="spinner"></div>
          <p>Connecting to room...</p>
          <button className="btn-danger" onClick={disconnectFromRoom}>Cancel</button>
        </div>
      )}

      {connectionState === 'disconnecting' && (
        <div className="status-panel"><p>Disconnecting from room...</p></div>
      )}
      
      {connectionState === 'connected' && (
        <div className="session-panel">
          <div className="session-header">
            <h3>🎙️ Session Active</h3>
            <button className="btn-danger" onClick={disconnectFromRoom}>
              ⏹️ End Session
            </button>
          </div>
          
          <div className="instructions-live">
            <p><strong>Speak naturally.</strong> The agent will respond with voice. You can interrupt anytime (barge-in supported).</p>
          </div>
          
          <div className="transcript-panel">
            <h4>Live Transcript</h4>
            <div className="transcript-container">
              {transcripts.length === 0 ? (
                <p className="no-transcripts">Waiting for conversation to start...</p>
              ) : (
                transcripts.map((entry, idx) => (
                  <div key={idx} className={`transcript-entry ${entry.role.toLowerCase()}`}>
                    <div className="transcript-header">
                      <strong>{entry.role}</strong>
                      <span className="timestamp">{entry.timestamp}</span>
                    </div>
                    <p>{entry.text}</p>
                  </div>
                ))
              )}
            </div>
          </div>
          
        </div>
      )}

      {/* Tracks can arrive before connect/microphone setup has finished. */}
      <audio ref={audioElementRef} autoPlay />
      
      <div className="footer">
        <p>DifficultAI - High-Pressure Voice Training • <a href="https://github.com/wildhash/difficultai" target="_blank" rel="noopener noreferrer">GitHub</a></p>
      </div>
    </div>
  )
}

export default App
