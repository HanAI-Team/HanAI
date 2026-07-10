'use client'

import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE_TIMEOUT_MS = 30 * 60 * 1000
const WARNING_BEFORE_MS = 60 * 1000

export function useIdleTimeout() {
  const router = useRouter()
  const [showWarning, setShowWarning] = useState(false)
  const showWarningRef = useRef(false)
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    router.push('/login')
  }, [router])

  const resetTimers = useCallback(() => {
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current)
    showWarningRef.current = false
    setShowWarning(false)
    warningTimerRef.current = setTimeout(() => {
      showWarningRef.current = true
      setShowWarning(true)
    }, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS)
    logoutTimerRef.current = setTimeout(logout, IDLE_TIMEOUT_MS)
  }, [logout])

  useEffect(() => {
    if (!localStorage.getItem('token')) return

    const handleActivity = () => {
      if (showWarningRef.current) return
      resetTimers()
    }

    const events = ['mousemove', 'keydown', 'click', 'scroll'] as const
    events.forEach((e) => window.addEventListener(e, handleActivity, { passive: true }))
    resetTimers()

    return () => {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current)
      events.forEach((e) => window.removeEventListener(e, handleActivity))
    }
  }, [resetTimers])

  const extendSession = useCallback(() => {
    resetTimers()
  }, [resetTimers])

  return { showWarning, extendSession }
}
