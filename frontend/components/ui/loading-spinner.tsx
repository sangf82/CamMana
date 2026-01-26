"use client"

import React from "react"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface LoadingSpinnerProps {
  /** Loading message to display below the icon */
  message?: string
  /** Size of the spinner icon */
  size?: "sm" | "md" | "lg"
  /** Additional className */
  className?: string
}

const sizeClasses = {
  sm: "h-6 w-6",
  md: "h-8 w-8", 
  lg: "h-12 w-12"
}

const textSizeClasses = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-base"
}

/**
 * Consistent loading spinner component.
 * Displays a yellow spinning icon with optional text below, centered in its container.
 */
export function LoadingSpinner({ 
  message = "Đang tải...", 
  size = "md",
  className 
}: LoadingSpinnerProps) {
  return (
    <div className={cn(
      "flex flex-col items-center justify-center gap-3",
      className
    )}>
      <Loader2 
        className={cn(
          "animate-spin text-[#f59e0b]",
          sizeClasses[size]
        )} 
      />
      {message && (
        <span className={cn(
          "text-foreground font-medium",
          textSizeClasses[size]
        )}>
          {message}
        </span>
      )}
    </div>
  )
}

/**
 * Full-height loading spinner for page/panel loading states.
 */
export function LoadingPanel({ 
  message = "Đang tải...",
  size = "md",
  className
}: LoadingSpinnerProps) {
  return (
    <div className={cn(
      "flex h-full w-full items-center justify-center min-h-[200px]",
      className
    )}>
      <LoadingSpinner message={message} size={size} />
    </div>
  )
}

/**
 * Video/stream loading state with connecting animation.
 */
export function StreamingLoader({ 
  message = "Đang kết nối...",
  className
}: Omit<LoadingSpinnerProps, 'size'>) {
  return (
    <div className={cn(
      "absolute inset-0 flex flex-col items-center justify-center bg-black/80",
      className
    )}>
      <div className="relative">
        <Loader2 className="h-10 w-10 animate-spin text-[#f59e0b]" />
        <div className="absolute inset-0 h-10 w-10 rounded-full border-2 border-[#f59e0b]/30 animate-ping" />
      </div>
      <span className="mt-3 text-sm text-foreground font-medium">{message}</span>
    </div>
  )
}

export default LoadingSpinner
