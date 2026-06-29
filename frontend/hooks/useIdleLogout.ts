'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'

const IDLE_TIMEOUT_MS = 30 * 60 * 1000

export function useIdleLogout() {
  const router = useRouter()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!localStorage.getItem('token')) return

    const logout = () => {
      localStorage.removeItem('token')
      router.push('/login')
    }

    const reset = () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(logout, IDLE_TIMEOUT_MS)
    }

    const events = ['mousemove', 'keydown', 'mousedown', 'touchstart'] as const
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }))
    reset()

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      events.forEach((e) => window.removeEventListener(e, reset))
    }
  }, [router])
}
