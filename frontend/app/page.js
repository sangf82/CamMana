'use client'

import { useState, useEffect, useCallback } from 'react'
import ScheduleDashboard from './components/ScheduleDashboard'
import {
  Videocam,
  Assessment,
  WbSunny,
  DarkMode,
  KeyboardArrowUp,
  KeyboardArrowDown,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  Camera,
  ZoomIn,
  ZoomOut,
  Search,
  PowerSettingsNew,
  PlayArrow,
  Stop,
  CameraAlt,
  Construction
} from '@mui/icons-material'

// API base URL
const API_BASE = 'http://127.0.0.1:8000/api'

export default function Home() {
  const [cameras, setCameras] = useState([])
  const [selectedCameraId, setSelectedCameraId] = useState(null)
  
  // Theme State
  const [theme, setTheme] = useState('dark')

  // Toggle Theme
  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  // Apply Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // Connection Form State
  const [config, setConfig] = useState({
    ip: '192.168.5.159',
    port: 8899,
    user: 'admin',
    password: '',
    name: 'Camera Chính'
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
      showToast(`Đã kết nối: ${config.name}`)
      await fetchCameras()
      setSelectedCameraId(res.id)
    } else {
      showToast(res.error || 'Kết nối thất bại', 'error')
    }
  }

  // Camera Actions
  const handleDisconnect = async (id) => {
    if (!confirm('Ngắt kết nối camera này?')) return
    await apiCall(`/cameras/${id}/disconnect`, 'POST')
    showToast('Đã ngắt kết nối')
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
      showToast(`Đã lưu ảnh: ${res.filename}`)
    } else {
      showToast('Chụp ảnh thất bại', 'error')
    }
  }

  // PTZ Handler
  const handlePTZ = async (direction) => {
    if (!selectedCameraId) return
    await apiCall(`/cameras/${selectedCameraId}/ptz/${direction}`, 'POST', { speed })
  }

  // Dashboard State
  const [schedule, setSchedule] = useState([])
  const [viewMode, setViewMode] = useState('live') // 'live' | 'schedule'
  const [verificationResult, setVerificationResult] = useState(null)
  const [processing, setProcessing] = useState(false)

  // Fetch Schedule
  const fetchSchedule = async () => {
    const data = await apiCall('/schedule')
    if (Array.isArray(data)) {
        // Add default status and normalized plate for matching
        const enrichedData = data.map(row => ({
            ...row,
            displayStatus: row.verified ? 'Đã vào' : 'Chưa đến', 
        }))
      setSchedule(enrichedData)
    }
  }

  useEffect(() => {
    fetchSchedule()
  }, [])

  // Verify Vehicle Handler
  const handleVerify = async (cameraId) => {
    if (!cameraId) return
    setProcessing(true)
    setToast({ message: 'Đang phân tích...', type: 'info' })

    try {
      // 1. Get snapshot from local backend
      const snapshotRes = await fetch(`${API_BASE}/cameras/${cameraId}/snapshot`)
      if (!snapshotRes.ok) throw new Error('Failed to get snapshot')
      const blob = await snapshotRes.blob()

      // 2. Call external ALPR API
      const formData = new FormData()
      formData.append('file', blob, 'capture.jpg')

      const alprRes = await fetch('https://thpttl12t1--truck-api-fastapi-app.modal.run/alpr', {
        method: 'POST',
        body: formData
      })
      const alprData = await alprRes.json()

      // 3. Match against schedule
      if (alprData.plates && alprData.plates.length > 0) {
        const detectedPlate = alprData.plates[0].toUpperCase().replace(/[^A-Z0-9]/g, '')
        
        const match = schedule.find(row => {
            const rowPlate = (row.plate || '').toString().toUpperCase().replace(/[^A-Z0-9]/g, '')
            return rowPlate.includes(detectedPlate) || detectedPlate.includes(rowPlate)
        })

        if (match) {
            setVerificationResult({
                matchedRow: match,
                detectedPlate,
                timestamp: new Date()
            })
            // Mark as verified locally for demo and update status
            setSchedule(prev => prev.map(r => 
                r.stt === match.stt ? {...r, verified: true, displayStatus: 'Đã vào'} : r
            ))
            showToast(`KHỚP LỊCH TRÌNH: ${match.plate}`, 'success')
            setViewMode('schedule') // Auto switch to dashboard to show match
        } else {
            showToast(`Xe ${alprData.plates[0]} không có trong lịch trình`, 'warning')
        }
      } else {
        showToast('Không tìm thấy biển số xe', 'error')
      }
      
    } catch (e) {
      console.error(e)
      showToast('Lỗi xác thực: ' + e.message, 'error')
    } finally {
      setProcessing(false)
    }
  }

  // Import Schedule Handler
  const handleImportSchedule = async (file) => {
    try {
        const formData = new FormData()
        formData.append('file', file)
        
        setToast({ message: 'Đang tải lên...', type: 'info' })
        
        const res = await fetch(`${API_BASE}/schedule/upload`, {
            method: 'POST',
            body: formData
        })
        const data = await res.json()
        
        if (data.success) {
            showToast('Đã nhập lịch trình mới', 'success')
            fetchSchedule()
        } else {
             showToast(data.detail || 'Lỗi tải lên', 'error')
        }
    } catch (e) {
        console.error(e)
        showToast('Lỗi tải file: ' + e.message, 'error')
    }
  }

  return (
    <div className="app">
      {/* Sidebar Controls */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Construction style={{ color: 'var(--accent)' }} />
          <h1>CamMana</h1>
        </div>
        
        {/* Navigation */}
        <div className="nav-menu">
            <button 
                className={`nav-item ${viewMode === 'live' ? 'active' : ''}`}
                onClick={() => setViewMode('live')}
            >
                <Videocam fontSize="small" /> Xem Camera
            </button>
            <button 
                className={`nav-item ${viewMode === 'schedule' ? 'active' : ''}`}
                onClick={() => setViewMode('schedule')}
            >
                <Assessment fontSize="small" /> Lịch trình
            </button>
            
        </div>

        {/* Theme Toggle Switch */}
        <div className="theme-switch-wrapper">
             <div className="theme-switch-label">
                {theme === 'light' ? 
                  <><WbSunny fontSize="small" style={{color: 'var(--accent)'}} /> Chế độ Sáng</> : 
                  <><DarkMode fontSize="small" /> Chế độ Tối</>
                }
             </div>
             <label className="toggle-switch">
                <input 
                    type="checkbox" 
                    checked={theme === 'light'}
                    onChange={toggleTheme}
                />
                <span className="slider"></span>
            </label>
        </div>

        {/* Add Camera Form */}
        {viewMode === 'live' && (
        <div className="section">
          <span className="section-title">Thêm Camera</span>
          <div className="form-group">
            <input 
              placeholder="Tên Camera" 
              value={config.name}
              onChange={e => setConfig({...config, name: e.target.value})}
            />
          </div>
          <div className="form-group">
            <input 
              placeholder="Địa chỉ IP" 
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
            {loading ? 'Đang kết nối...' : 'Thêm Camera'}
          </button>
        </div>
        )}
        
        <hr style={{borderColor: 'var(--border)', margin: '10px 0'}} />

        {/* Selected Camera PTZ */}
        {viewMode === 'live' && (
        <div className="section">
          <span className="section-title">
            {selectedCameraId ? `Điều khiển: ${cameras.find(c => c.id === selectedCameraId)?.name || 'Unknown'}` : 'Chọn Camera'}
          </span>
          
          {selectedCameraId && (
            <>
              <div className="speed-control">
                <div className="speed-label" style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                  Tốc độ: {speed}
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
                <button className="ptz-btn" onClick={() => handlePTZ('up')}><KeyboardArrowUp /></button>
                <div />
                
                <button className="ptz-btn" onClick={() => handlePTZ('left')}><KeyboardArrowLeft /></button>
                <div className="ptz-center-group">
                     <button className="ptz-btn capture" onClick={() => handleCapture(selectedCameraId)}>
                        <Camera fontSize="small" />
                     </button>
                </div>
                <button className="ptz-btn" onClick={() => handlePTZ('right')}><KeyboardArrowRight /></button>
                
                <div />
                <button className="ptz-btn" onClick={() => handlePTZ('down')}><KeyboardArrowDown /></button>
                <div />
              </div>

              <button 
                className="btn btn-primary" 
                style={{marginTop: '15px', background: 'var(--primary)', color: 'black'}}
                onClick={() => handleVerify(selectedCameraId)}
                disabled={processing}
              >
                {processing ? 'Đang phân tích...' : <><Search fontSize="small" /> Kiểm tra xe</>}
              </button>

              <div className="zoom-controls">
                <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-out')}><ZoomOut fontSize="small"/> Zoom</button>
                <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-in')}><ZoomIn fontSize="small"/> Zoom</button>
              </div>
            </>
          )}
        </div>
        )}
      </aside>

      {/* Main Grid View */}
      <main className="main-content">
        {viewMode === 'live' ? (
        <div className="camera-grid">
          {cameras.length === 0 && (
             <div style={{
               display: 'flex', 
               alignItems: 'center', 
               justifyContent: 'center', 
               height: '100%', 
               color: 'var(--text-muted)'
             }}>
               <h2>Chưa có camera kết nối</h2>
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
                   ><PowerSettingsNew fontSize="small" style={{marginRight:0}} /></button>
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
                    <span>🛑 Dừng phát</span>
                    <button className="btn btn-primary" onClick={() => handleStartStream(cam.id)}>
                      <PlayArrow /> Phát
                    </button>
                  </div>
                )}
                
                {cam.streaming && (
                  <div className="overlay-controls">
                    <button 
                      className="btn btn-overlay" 
                      onClick={(e) => { e.stopPropagation(); handleStopStream(cam.id); }}
                    ><Stop /> Dừng</button>
                    <button 
                      className="btn btn-primary" 
                      onClick={(e) => { e.stopPropagation(); handleCapture(cam.id); }}
                    ><CameraAlt /> Chụp</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        ) : (
            <ScheduleDashboard 
                schedule={schedule} 
                verificationResult={verificationResult} 
                onReload={fetchSchedule}
                onImport={handleImportSchedule}
            />
        )}
      </main>

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
