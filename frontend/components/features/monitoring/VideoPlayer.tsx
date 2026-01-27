'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { VideocamOff, Refresh } from '@mui/icons-material'

interface VideoPlayerProps {
  src?: string
  label?: string
  camCode?: string
  activeId?: string // Active camera ID for fetching stream info
  isLive?: boolean
  className?: string
  onClick?: () => void
}

export default function VideoPlayer({ 
  src, 
  label = 'Camera',
  camCode,
  activeId,
  isLive = true,
  className = '',
  onClick
}: VideoPlayerProps) {
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [streamInfo, setStreamInfo] = useState<{resolution: string, fps: number} | null>(null)

  // Fetch stream info periodically
  useEffect(() => {
    if (!activeId || !src) return

    const fetchStreamInfo = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return
        
        const res = await fetch(`/api/cameras`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
          const cameras = await res.json()
          const cam = cameras.find((c: { id: string }) => c.id === activeId)
          if (cam?.stream_info) {
            setStreamInfo({
              resolution: cam.stream_info.resolution || 'N/A',
              fps: cam.stream_info.fps || 0
            })
          }
        }
      } catch (e) {
        // Ignore errors
      }
    }

    fetchStreamInfo()
    const interval = setInterval(fetchStreamInfo, 2000) // Update every 2s
    return () => clearInterval(interval)
  }, [activeId, src])


  const handleRetry = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setHasError(false)
    setIsLoading(true)
  }, [])

  const displayLabel = camCode || label

  return (
    <div 
      className={`relative w-full h-full bg-black rounded-lg overflow-hidden border border-border shadow-sm group ${className}`}
      onClick={onClick}
    >
      {/* Video Content */}
      {!hasError && src && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img 
          src={src}
          alt={displayLabel}
          className={`w-full h-full object-contain transition-opacity duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
          onLoad={() => setIsLoading(false)}
          onError={() => { setHasError(true); setIsLoading(false); }}
        />
      )}

      {/* Loading State */}
      {isLoading && !hasError && src && (
        <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm z-10">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error State */}
      {(hasError || !src) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-900 text-muted-foreground z-10 gap-2">
          <VideocamOff fontSize="large" />
          <span className="text-sm">Không có tín hiệu</span>
          {hasError && (
            <button 
              onClick={handleRetry}
              className="px-3 py-1 bg-secondary hover:bg-muted text-xs rounded-md flex items-center gap-1 transition-colors"
            >
              <Refresh fontSize="small" /> Thử lại
            </button>
          )}
        </div>
      )}


    </div>
  )
}
