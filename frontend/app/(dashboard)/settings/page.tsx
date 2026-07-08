'use client'
import AccessTab from '@/components/settings/AccessTab'
import FaqTab from '@/components/settings/FaqTab'
import GeneralTab from '@/components/settings/GeneralTab'
import StaffTab from '@/components/settings/StaffTab'
import WorkDaysTab from '@/components/settings/WorkDaysTab'
import { jwtDecode } from 'jwt-decode'
import { useEffect, useState } from 'react'

export default function SettingsPage() {
  const [tab, setTab] = useState<'general' | 'staff' | 'access' | 'workdays' | 'faq' | null>(null)

  useEffect(() => {
    setTab('general')
  }, [])

  const [isOwner, setIsOwner] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      setIsOwner(jwtDecode<{ role: string }>(token).role === 'owner')
    } catch {
      setIsOwner(false)
    }
  }, [])

  return (
    <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
      <div className="max-w-[1100px]">
        <h1 className="text-3xl text-text mb-1">설정</h1>
        <p className="text-subtext">계정과 병원 환경을 관리하세요</p>

        {isOwner && (
          <div className="flex bg-fill border border-border rounded-2xl p-1 mt-8 mb-6 overflow-x-auto">
            {[
              { value: 'general', label: '일반' },
              { value: 'staff', label: '하위 계정' },
              { value: 'access', label: '접근 기록' },
              { value: 'workdays', label: '진료일수' },
              { value: 'faq', label: 'FAQ' },
            ].map((t) => (
              <button
                key={t.value}
                onClick={() => setTab(t.value as any)}
                className={`flex-1 whitespace-nowrap rounded-xl py-3 text-sm font-medium transition-all ${
                  tab === t.value ? 'bg-card text-text shadow-sm' : 'text-subtext hover:text-text'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {tab === 'general' && <GeneralTab />}
        {tab === 'staff' && isOwner && <StaffTab />}
        {tab === 'access' && isOwner && <AccessTab />}
        {tab === 'workdays' && isOwner && <WorkDaysTab />}
        {tab === 'faq' && <FaqTab />}
      </div>
    </div>
  )
}