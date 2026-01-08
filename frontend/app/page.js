'use client'

import { useState, useEffect, useCallback } from 'react'

// API base URL
const API_BASE = 'http://127.0.0.1:8000/api'

export default function Home() {
  const [cameras, setCameras] = useState([])
  const [selectedCameraId, setSelectedCameraId] = useState(null)
  
  // Connection Form State
  const [config, setConfig] = useState({
    ip: '192.168.5.159',
    port: 8899,
    user: 'admin',
    password: '',
    name: 'Main Camera'
  })
  
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  
  // PTZ State
  const [speed, setSpeed] = useState(0.5)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const apiCall = async (endpoint, method = 'GET', body = null) => {
    try {
      const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
      }
      if (body) options.body = JSON.stringify(body)
      const res = await fetch(`${API_BASE}${endpoint}`, options)
      return await res.json()
    } catch (e) {
      console.error(e)
      return { success: false, error: e.message }
    }
  }

  // Refresh camera list
  const fetchCameras = useCallback(async () => {
    const data = await apiCall('/cameras')
    if (Array.isArray(data)) {
      setCameras(data)
      if (data.length > 0 && !selectedCameraId) {
        setSelectedCameraId(data[0].id)
      }
    }
  }, [selectedCameraId])

  // Initial load
  useEffect(() => {
    fetchCameras()
    const interval = setInterval(fetchCameras, 5000)
    return () => clearInterval(interval)
  }, [fetchCameras])

  // Connect Handler
  const handleConnect = async () => {
    setLoading(true)
    const res = await apiCall('/connect', 'POST', config)
    setLoading(false)
    if (res.success) {
      showToast(`Connected to ${config.name}`)
      await fetchCameras()
      setSelectedCameraId(res.id)
    } else {
      showToast(res.error || 'Connection Failed', 'error')
    }
  }

  // Camera Actions
  const handleDisconnect = async (id) => {
    if (!confirm('Disconnect this camera?')) return
    await apiCall(`/cameras/${id}/disconnect`, 'POST')
    showToast('Disconnected')
    fetchCameras()
    if (selectedCameraId === id) setSelectedCameraId(null)
  }

  const handleStartStream = async (id) => {
    await apiCall(`/cameras/${id}/stream/start`, 'POST')
    fetchCameras() // Refresh status
  }

  const handleStopStream = async (id) => {
    await apiCall(`/cameras/${id}/stream/stop`, 'POST')
    fetchCameras()
  }

  const handleCapture = async (id) => {
    const res = await apiCall(`/cameras/${id}/capture`, 'POST')
    if (res.success) {
      showToast(`Saved: ${res.filename}`)
    } else {
      showToast('Capture failed', 'error')
    }
  }

  // PTZ Handler
  const handlePTZ = async (direction) => {
    if (!selectedCameraId) return
    await apiCall(`/cameras/${selectedCameraId}/ptz/${direction}`, 'POST', { speed })
  }

  return (
    <div className="app">
      {/* Sidebar Controls */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <svg className="icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
          <h1>CamMana</h1>
        </div>

        {/* Add Camera Form */}
        <div className="section">
          <span className="section-title">Add Camera</span>
          <div className="form-group">
            <input 
              placeholder="Camera Name" 
              value={config.name}
              onChange={e => setConfig({...config, name: e.target.value})}
            />
          </div>
          <div className="form-group">
            <input 
              placeholder="IP Address" 
              value={config.ip}
              onChange={e => setConfig({...config, ip: e.target.value})}
            />
          </div>
          <div className="btn-row">
            <div className="form-group" style={{flex:1}}>
              <input 
                placeholder="User" 
                value={config.user}
                onChange={e => setConfig({...config, user: e.target.value})}
              />
            </div>
            <div className="form-group" style={{flex:1}}>
               <input 
                type="password"
                placeholder="Pass" 
                value={config.password}
                onChange={e => setConfig({...config, password: e.target.value})}
              />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleConnect} disabled={loading}>
            {loading ? 'Connecting...' : 'Add Camera'}
          </button>
        </div>
        
        <hr style={{borderColor: 'var(--border)', margin: '10px 0'}} />

        {/* Selected Camera PTZ */}
        <div className="section">
          <span className="section-title">
            {selectedCameraId ? `Control: ${cameras.find(c => c.id === selectedCameraId)?.name || 'Unknown'}` : 'Select a Camera'}
          </span>
          
          {selectedCameraId && (
            <>
              <div className="speed-control">
                <div className="speed-label" style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                  Speed: {speed}
                </div>
                <input 
                  type="range" 
                  min="0.1" 
                  max="1.0" 
                  step="0.1" 
                  value={speed}
                  className="speed-slider"
                  onChange={e => setSpeed(parseFloat(e.target.value))}
                />
              </div>

              <div className="ptz-grid">
                <div />
                <button className="ptz-btn" onClick={() => handlePTZ('up')}>▲</button>
                <div />
                
                <button className="ptz-btn" onClick={() => handlePTZ('left')}>◀</button>
                <button className="ptz-btn capture" onClick={() => handleCapture(selectedCameraId)}>◉</button>
                <button className="ptz-btn" onClick={() => handlePTZ('right')}>▶</button>
                
                <div />
                <button className="ptz-btn" onClick={() => handlePTZ('down')}>▼</button>
                <div />
              </div>

              <div className="zoom-controls">
                <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-out')}>- Zoom</button>
                <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-in')}>+ Zoom</button>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Main Grid View */}
      <main className="main-content">
        <div className="camera-grid">
          {cameras.length === 0 && (
             <div style={{
               display: 'flex', 
               alignItems: 'center', 
               justifyContent: 'center', 
               height: '100%', 
               color: 'var(--text-muted)'
             }}>
               <h2>No cameras connected</h2>
             </div>
          )}

          {cameras.map(cam => (
            <div 
              key={cam.id} 
              className={`camera-card ${selectedCameraId === cam.id ? 'selected' : ''}`}
              onClick={() => setSelectedCameraId(cam.id)}
            >
              <div className="camera-header">
                <div className="camera-name">
                  <span className={`status-badge ${cam.connected ? 'connected' : 'disconnected'}`} />
                  {cam.name} <span style={{opacity:0.5, fontSize:'0.8em'}}>({cam.ip})</span>
                </div>
                <div className="btn-row">
                   <button 
                    className="btn btn-danger" 
                    style={{padding: '4px 8px', fontSize: '0.75rem'}}
                    onClick={(e) => { e.stopPropagation(); handleDisconnect(cam.id); }}
                   >Disconnect</button>
                </div>
              </div>

              <div className="camera-view">
                {cam.streaming ? (
                  <img 
                    className="video-feed" 
                    src={`${API_BASE}/cameras/${cam.id}/stream?t=${Date.now()}`} 
                    alt="Stream"
                  />
                ) : (
                  <div className="empty-state">
                    <span>🛑 Stream Stopped</span>
                    <button className="btn btn-primary" onClick={() => handleStartStream(cam.id)}>
                      Start Stream
                    </button>
                  </div>
                )}
                
                {cam.streaming && (
                  <div className="overlay-controls">
                    <button 
                      className="btn btn-secondary" 
                      style={{background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)'}}
                      onClick={(e) => { e.stopPropagation(); handleStopStream(cam.id); }}
                    >Stop</button>
                    <button 
                      className="btn btn-primary" 
                      onClick={(e) => { e.stopPropagation(); handleCapture(cam.id); }}
                    >Capture</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
