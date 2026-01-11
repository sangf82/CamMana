'use client'

import React, { useEffect } from 'react'
import { Close } from '@mui/icons-material'

interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl'
}

export default function Dialog({ isOpen, onClose, title, children, maxWidth = 'md' }: DialogProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const widthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" 
        onClick={onClose}
      />

      {/* Dialog Panel */}
      <div className={`relative w-full ${widthClasses[maxWidth]} bg-card border border-border shadow-2xl rounded-lg animate-in zoom-in-95 duration-200 overflow-hidden flex flex-col max-h-[90vh]`}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
          <h3 className="font-semibold text-lg text-foreground tracking-tight">{title}</h3>
          <button 
            onClick={onClose} 
            className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-muted"
          >
            <Close fontSize="small" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  )
}
