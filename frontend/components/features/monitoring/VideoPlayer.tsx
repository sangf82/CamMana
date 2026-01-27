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

  // Consolidating polling into the parent page to prevent connection flooding
  // Stream info is now passed down or fetched centrally


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
          className={`w-full h-full object-cover transition-opacity duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
          onLoad={() => setIsLoading(false)}
          onError={() => { setHasError(true); setIsLoading(false); }}
        />
      )}

      {/* Label Overlay */}
      <div className="absolute top-0 left-0 right-0 p-2 bg-gradient-to-b from-black/70 to-transparent z-20 pointer-events-none">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${src && !hasError && !isLoading ? 'bg-green-500 animate-pulse' : 'bg-zinc-500'}`} />
          <span className="text-[10px] font-bold text-white uppercase tracking-wider drop-shadow-md">
            {displayLabel}
          </span>
        </div>
      </div>

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
