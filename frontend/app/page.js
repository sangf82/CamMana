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
  Construction,
  DirectionsCar,
  Palette,
  TireRepair
} from '@mui/icons-material'

const API_BASE = 'http://127.0.0.1:8000/api'

export default function Home() {
  const [cameras, setCameras] = useState([])
  const [selectedCameraId, setSelectedCameraId] = useState(null)
  const [theme, setTheme] = useState('dark')
  const [config, setConfig] = useState({
    ip: '192.168.5.159',
    port: 8899,
    user: 'admin',
    password: '',
    name: 'Camera',
    tag: null,
    detection_mode: 'disabled'
  })
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [speed, setSpeed] = useState(0.5)
  
  // Detection State
  const [detecting, setDetecting] = useState(false)
  const [detectingStage, setDetectingStage] = useState(null) // 'car' | 'plate' | 'side' | null
  const [detectionResult, setDetectionResult] = useState(null)
  const [viewMode, setViewMode] = useState('live')
  const [schedule, setSchedule] = useState([])

  // Toggle Theme
  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const apiCall = async (endpoint, method = 'GET', body = null) => {
    try {
      const options = { method, headers: { 'Content-Type': 'application/json' } }
      if (body) options.body = JSON.stringify(body)
      const res = await fetch(`${API_BASE}${endpoint}`, options)
      return await res.json()
    } catch (e) {
      console.error(e)
      return { success: false, error: e.message }
    }
  }

  const fetchCameras = useCallback(async () => {
    const data = await apiCall('/cameras')
    if (Array.isArray(data)) {
      setCameras(data)
      if (data.length > 0 && !selectedCameraId) {
        setSelectedCameraId(data[0].id)
      }
    }
  }, [selectedCameraId])

  useEffect(() => {
    fetchCameras()
    const interval = setInterval(fetchCameras, 5000)
    return () => clearInterval(interval)
  }, [fetchCameras])

  // Get cameras by tag
  const frontCam = cameras.find(c => c.tag === 'front_cam')
  const sideCam = cameras.find(c => c.tag === 'side_cam')

  // Connect Handler
  const handleConnect = async () => {
    setLoading(true)
    const res = await apiCall('/cameras/connect', 'POST', config)
    setLoading(false)
    if (res.success) {
      showToast(`Đã kết nối: ${config.name}`)
      await fetchCameras()
      setSelectedCameraId(res.id)
    } else {
      showToast(res.error || 'Kết nối thất bại', 'error')
    }
  }

  const handleDisconnect = async (id) => {
    if (!confirm('Ngắt kết nối camera này?')) return
    await apiCall(`/cameras/${id}/disconnect`, 'POST')
    showToast('Đã ngắt kết nối')
    fetchCameras()
    if (selectedCameraId === id) setSelectedCameraId(null)
  }

  const handleStartStream = async (id) => {
    await apiCall(`/cameras/${id}/stream/start`, 'POST')
    fetchCameras()
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

  const handlePTZ = async (direction) => {
    if (!selectedCameraId) return
    await apiCall(`/cameras/${selectedCameraId}/ptz/${direction}`, 'POST', { speed })
  }

  // Manual Detection - Step by step
  const handleDetect = async () => {
    if (!frontCam) {
      showToast('Cần có Camera Trước (front_cam) để phát hiện xe', 'error')
      return
    }
    if (!frontCam.streaming) {
      showToast('Camera Trước chưa phát stream', 'error')
      return
    }
    
    setDetecting(true)
    setDetectionResult(null)
    
    try {
      // Stage 1: Detect car on front camera
      setDetectingStage('car')
      const detectRes = await apiCall(`/cameras/${frontCam.id}/detect`)
      
      if (!detectRes.success || !detectRes.detected) {
        setDetectionResult({ detected: false, message: 'Không phát hiện xe' })
        setDetecting(false)
        setDetectingStage(null)
        return
      }
      
      // Car detected - show intermediate result
      setDetectionResult({
        detected: true,
        class_name: detectRes.class_name,
        confidence: detectRes.confidence,
        stage: 'detected'
      })
      
      // Stage 2: Parallel detection - Plate (front) + Color/Wheels (side)
      setDetectingStage('analyzing')
      
      // Call capture_with_detection which handles both cameras
      const captureRes = await apiCall(`/cameras/${frontCam.id}/capture_with_detection`, 'POST')
      
      if (captureRes.success) {
        setDetectionResult({
          detected: true,
          class_name: captureRes.class_name,
          confidence: captureRes.confidence,
          plate: captureRes.plate,
          color: captureRes.color,
          wheel_count: captureRes.wheel_count,
          timestamp: captureRes.timestamp,
          folder: captureRes.folder_path,
          stage: 'complete'
        })
        showToast('✓ Đã phát hiện và lưu thông tin xe', 'success')
      } else if (captureRes.skipped) {
        setDetectionResult({
          detected: true,
          skipped: true,
          reason: captureRes.reason,
          class_name: detectRes.class_name,
          stage: 'skipped'
        })
        showToast(`⚠ ${captureRes.reason}`, 'warning')
      } else {
        setDetectionResult({ 
          detected: true, 
          error: captureRes.error,
          class_name: detectRes.class_name,
          stage: 'error'
        })
      }
    } catch (e) {
      setDetectionResult({ detected: false, error: e.message })
    }
    
    setDetecting(false)
    setDetectingStage(null)
  }

  // Schedule
  const fetchSchedule = async () => {
    const data = await apiCall('/schedule')
    if (Array.isArray(data)) {
      setSchedule(data.map(row => ({ ...row, displayStatus: row.verified ? 'Đã vào' : 'Chưa đến' })))
    }
  }

  useEffect(() => { fetchSchedule() }, [])

  const handleImportSchedule = async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    setToast({ message: 'Đang tải lên...', type: 'info' })
    const res = await fetch(`${API_BASE}/schedule/upload`, { method: 'POST', body: formData })
    const data = await res.json()
    if (data.success) {
      showToast('Đã nhập lịch trình mới', 'success')
      fetchSchedule()
    } else {
      showToast(data.detail || 'Lỗi tải lên', 'error')
    }
  }

  // Render Camera View
  const renderCameraView = (cam, label) => {
    if (!cam) {
      return (
        <div className="camera-panel empty" key={`empty-${label}`}>
          <div className="camera-placeholder">
            <Videocam style={{ fontSize: 48, opacity: 0.3 }} />
            <p>Chưa kết nối {label}</p>
          </div>
        </div>
      )
    }

    return (
      <div key={cam.id} className={`camera-panel ${selectedCameraId === cam.id ? 'selected' : ''}`} 
           onClick={() => setSelectedCameraId(cam.id)}>
        <div className="camera-panel-header">
          <span className={`status-dot ${cam.connected ? 'connected' : ''}`} />
          <span className="cam-name">{cam.name}</span>
          <span className="cam-ip">({cam.ip})</span>
          {cam.tag && (
            <span className={`tag-badge ${cam.tag}`}>
              {cam.tag === 'front_cam' ? '🚗 Trước' : cam.tag === 'side_cam' ? '🔍 Bên' : '📹'}
            </span>
          )}
          <button className="btn-icon danger" onClick={(e) => { e.stopPropagation(); handleDisconnect(cam.id) }}>
            <PowerSettingsNew fontSize="small" />
          </button>
        </div>
        
        <div className="camera-video">
          {cam.streaming ? (
            <>
              <img 
                src={`${API_BASE}/cameras/${cam.id}/stream?t=${Date.now()}`} 
                alt="Stream"
                className="video-feed"
              />
              {cam.stream_info && (
                <div className="stream-info">
                  📺 {cam.stream_info.resolution} | ⚡ {cam.stream_info.fps} FPS
                </div>
              )}
            </>
          ) : (
            <div className="video-placeholder">
              <span>🛑 Dừng phát</span>
              <button className="btn btn-primary" onClick={() => handleStartStream(cam.id)}>
                <PlayArrow /> Phát
              </button>
            </div>
          )}
        </div>

        {cam.streaming && (
          <div className="camera-controls">
            <button className="btn btn-secondary" onClick={(e) => { e.stopPropagation(); handleStopStream(cam.id) }}>
              <Stop fontSize="small" /> Dừng
            </button>
            <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleCapture(cam.id) }}>
              <CameraAlt fontSize="small" /> Chụp
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Construction style={{ color: 'var(--accent)' }} />
          <h1>CamMana</h1>
        </div>
        
        <div className="nav-menu">
          <button className={`nav-item ${viewMode === 'live' ? 'active' : ''}`} onClick={() => setViewMode('live')}>
            <Videocam fontSize="small" /> Xem Camera
          </button>
          <button className={`nav-item ${viewMode === 'schedule' ? 'active' : ''}`} onClick={() => setViewMode('schedule')}>
            <Assessment fontSize="small" /> Lịch trình
          </button>
        </div>

        <div className="theme-switch-wrapper">
          <div className="theme-switch-label">
            {theme === 'light' ? <><WbSunny fontSize="small" style={{color: 'var(--accent)'}} /> Sáng</> : <><DarkMode fontSize="small" /> Tối</>}
          </div>
          <label className="toggle-switch">
            <input type="checkbox" checked={theme === 'light'} onChange={toggleTheme} />
            <span className="slider"></span>
          </label>
        </div>

        {viewMode === 'live' && (
          <>
            <div className="section">
              <span className="section-title">Thêm Camera</span>
              <div className="form-group">
                <input placeholder="Tên Camera" value={config.name} onChange={e => setConfig({...config, name: e.target.value})} />
              </div>
              <div className="form-group">
                <input placeholder="Địa chỉ IP" value={config.ip} onChange={e => setConfig({...config, ip: e.target.value})} />
              </div>
              <div className="form-group">
                <input placeholder="User" value={config.user} onChange={e => setConfig({...config, user: e.target.value})} />
              </div>
              <div className="form-group">
                <input 
                  type="password" 
                  placeholder="Password" 
                  value={config.password} 
                  onChange={e => setConfig({...config, password: e.target.value})} 
                  autoComplete="new-password"
                />
              </div>
              <div className="form-group">
                <label>Vai trò Camera</label>
                <select value={config.tag || ''} onChange={e => setConfig({...config, tag: e.target.value || null})}>
                  <option value="">📹 Không gán</option>
                  <option value="front_cam">🚗 Camera Trước (Biển số)</option>
                  <option value="side_cam">🔍 Camera Bên (Màu/Bánh)</option>
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleConnect} disabled={loading}>
                {loading ? 'Đang kết nối...' : 'Thêm Camera'}
              </button>
            </div>

            <hr style={{borderColor: 'var(--border)', margin: '10px 16px'}} />

            {/* PTZ Controls */}
            {selectedCameraId && (
              <div className="section">
                <span className="section-title">
                  Điều khiển: {cameras.find(c => c.id === selectedCameraId)?.name}
                </span>
                <div className="speed-control">
                  <span>Tốc độ: {speed}</span>
                  <input type="range" min="0.1" max="1.0" step="0.1" value={speed} onChange={e => setSpeed(parseFloat(e.target.value))} />
                </div>
                <div className="ptz-grid">
                  <div />
                  <button className="ptz-btn" onClick={() => handlePTZ('up')}><KeyboardArrowUp /></button>
                  <div />
                  <button className="ptz-btn" onClick={() => handlePTZ('left')}><KeyboardArrowLeft /></button>
                  <button className="ptz-btn capture" onClick={() => handleCapture(selectedCameraId)}><Camera /></button>
                  <button className="ptz-btn" onClick={() => handlePTZ('right')}><KeyboardArrowRight /></button>
                  <div />
                  <button className="ptz-btn" onClick={() => handlePTZ('down')}><KeyboardArrowDown /></button>
                  <div />
                </div>
                <div className="zoom-controls">
                  <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-out')}><ZoomOut fontSize="small"/> Zoom</button>
                  <button className="btn btn-secondary" onClick={() => handlePTZ('zoom-in')}><ZoomIn fontSize="small"/> Zoom</button>
                </div>
              </div>
            )}
          </>
        )}
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {viewMode === 'live' ? (
          <div className="dual-camera-layout">
            {/* Camera Grid - Show ALL cameras */}
            <div className="cameras-row" style={{ 
              gridTemplateColumns: cameras.length === 1 ? '1fr' : cameras.length >= 2 ? '1fr 1fr' : '1fr 1fr' 
            }}>
              {cameras.length === 0 ? (
                <>
                  <div className="camera-panel empty">
                    <div className="camera-placeholder">
                      <Videocam style={{ fontSize: 48, opacity: 0.3 }} />
                      <p>Chưa kết nối camera</p>
                    </div>
                  </div>
                  <div className="camera-panel empty">
                    <div className="camera-placeholder">
                      <Videocam style={{ fontSize: 48, opacity: 0.3 }} />
                      <p>Thêm camera từ sidebar</p>
                    </div>
                  </div>
                </>
              ) : (
                cameras.map(cam => renderCameraView(cam, cam.name))
              )}
            </div>

            {/* Detection Panel */}
            <div className="detection-panel">
              <div className="detection-header">
                <h3><DirectionsCar /> Phát hiện xe</h3>
                <button 
                  className="btn btn-primary detect-btn" 
                  onClick={handleDetect} 
                  disabled={detecting || !frontCam?.streaming}
                >
                  {detecting ? (
                    <>
                      <span className="spinner"></span>
                      Đang xử lý...
                    </>
                  ) : (
                    <>
                      <Search /> Phát hiện
                    </>
                  )}
                </button>
              </div>

              <div className="detection-results">
                {/* Front Camera - Plate Detection */}
                <div className="result-card front">
                  <div className="result-header">
                    <span className="result-icon">🚗</span>
                    <span>Camera Trước</span>
                    {detectingStage && (
                      <span className="stage-badge">
                        {detectingStage === 'car' && '🔍 Đang phát hiện xe...'}
                        {detectingStage === 'analyzing' && '📷 Đang đọc biển số...'}
                      </span>
                    )}
                  </div>
                  <div className="result-content">
                    {detectingStage === 'car' ? (
                      <div className="loading-state">
                        <span className="spinner large"></span>
                        <span>Đang quét camera...</span>
                      </div>
                    ) : detectingStage === 'analyzing' ? (
                      <div className="loading-state">
                        <span className="spinner large"></span>
                        <span>Đang đọc biển số...</span>
                      </div>
                    ) : detectionResult?.detected ? (
                      <>
                        <div className="result-main">
                          <DirectionsCar style={{ fontSize: 28, color: 'var(--accent)' }} />
                          <span className="plate-number">
                            {detectionResult.plate || 'Không đọc được biển'}
                          </span>
                        </div>
                        <div className="result-meta">
                          {detectionResult.class_name?.toUpperCase()} 
                          {detectionResult.confidence && ` • ${(detectionResult.confidence * 100).toFixed(0)}%`}
                        </div>
                      </>
                    ) : detectionResult?.message ? (
                      <div className="result-empty warning">
                        <span>⚠️ {detectionResult.message}</span>
                      </div>
                    ) : (
                      <div className="result-empty">
                        <span>Nhấn "Phát hiện" để quét xe</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Side Camera - Color & Wheels */}
                <div className="result-card side">
                  <div className="result-header">
                    <span className="result-icon">🔍</span>
                    <span>Camera Bên</span>
                    {detectingStage === 'analyzing' && (
                      <span className="stage-badge">🎨 Đang phân tích...</span>
                    )}
                  </div>
                  <div className="result-content">
                    {detectingStage === 'car' ? (
                      <div className="result-empty">
                        <span>Đang chờ phát hiện xe...</span>
                      </div>
                    ) : detectingStage === 'analyzing' ? (
                      <div className="loading-state">
                        <span className="spinner large"></span>
                        <span>Đang phân tích đồng thời...</span>
                      </div>
                    ) : detectionResult?.detected && detectionResult.stage === 'complete' ? (
                      <div className="result-details">
                        <div className="detail-item">
                          <Palette style={{ color: detectionResult.color ? '#3b82f6' : 'var(--text-muted)' }} />
                          <span className="detail-label">Màu sắc:</span>
                          <span className="detail-value">{detectionResult.color || '—'}</span>
                        </div>
                        <div className="detail-item">
                          <TireRepair style={{ color: detectionResult.wheel_count ? '#22c55e' : 'var(--text-muted)' }} />
                          <span className="detail-label">Số bánh:</span>
                          <span className="detail-value">{detectionResult.wheel_count || '—'}</span>
                        </div>
                      </div>
                    ) : detectionResult?.skipped ? (
                      <div className="result-empty warning">
                        <span>⚠️ {detectionResult.reason}</span>
                      </div>
                    ) : !sideCam ? (
                      <div className="result-empty warning">
                        <span>⚠️ Chưa kết nối Camera Bên</span>
                      </div>
                    ) : (
                      <div className="result-empty">
                        <span>Chờ phát hiện xe từ Camera Trước</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {detectionResult?.timestamp && (
                <div className="detection-footer">
                  📁 {detectionResult.folder} • {detectionResult.timestamp}
                </div>
              )}
            </div>
          </div>
        ) : (
          <ScheduleDashboard 
            schedule={schedule} 
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
