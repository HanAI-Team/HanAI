'use client'
import AccessControlLogTab from '@/components/settings/AccessControlLogTab'
import AuditLogTab from '@/components/settings/AuditLogTab'
import ChangeLogTab from '@/components/settings/ChangeLogTab'
import DbExportTab from '@/components/settings/DbExportTab'
import DrugMasterTab from '@/components/settings/DrugMasterTab'
import FeeMasterTab from '@/components/settings/FeeMasterTab'
import PurchaseNotificationTab from '@/components/settings/PurchaseNotificationTab'
import PurgeTab from '@/components/settings/PurgeTab'
import RejectionCodeTab from '@/components/settings/RejectionCodeTab'
import WorkDaysTab from '@/components/settings/WorkDaysTab'
import { jwtDecode } from 'jwt-decode'
import { useEffect, useState } from 'react'

type Tab =
  | 'fees'
  | 'drugs'
  | 'rejectionCodes'
  | 'auditLogs'
  | 'changeLog'
  | 'accessControlLog'
  | 'dbExport'
  | 'workdays'
  | 'purge'
  | 'purchaseNotification'

export default function ManagePage() {
  const [tab, setTab] = useState<Tab | null>(null)
  const [isOwner, setIsOwner] = useState<boolean | null>(null)

  useEffect(() => {
    setTab('fees')
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setIsOwner(false)
      return
    }
    try {
      setIsOwner(jwtDecode<{ role: string }>(token).role === 'owner')
    } catch {
      setIsOwner(false)
    }
  }, [])

  if (isOwner === null) {
    return (
      <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
        <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
      </div>
    )
  }

  if (!isOwner) {
    return (
      <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
        <div className="bg-card border border-border rounded-2xl text-center py-16">
          <div className="text-sm font-medium text-text mb-1">권한이 없습니다</div>
          <div className="text-xs text-subtext">오너 계정만 접근할 수 있는 페이지입니다.</div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
      <div className="max-w-[1100px]">
        <h1 className="text-3xl text-text mb-1">관리</h1>
        <p className="text-subtext">청구 관련 마스터 데이터와 로그를 관리하세요</p>

        <div className="flex bg-fill border border-border rounded-2xl p-1 mt-8 mb-6 overflow-x-auto">
          {[
            { value: 'fees', label: '수가 마스터' },
            { value: 'drugs', label: '약가 마스터' },
            { value: 'rejectionCodes', label: '코드관리' },
            { value: 'auditLogs', label: '로그관리' },
            { value: 'changeLog', label: '변경일 관리' },
            { value: 'accessControlLog', label: '접근권한 이력' },
            { value: 'dbExport', label: 'DB 내역 추출' },
            { value: 'workdays', label: '진료일수' },
            { value: 'purge', label: '파기대장' },
            { value: 'purchaseNotification', label: '구입내역 신고' },
          ].map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value as Tab)}
              className={`flex-1 whitespace-nowrap rounded-xl py-3 text-sm font-medium transition-all ${
                tab === t.value ? 'bg-card text-text shadow-sm' : 'text-subtext hover:text-text'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'fees' && <FeeMasterTab />}
        {tab === 'drugs' && <DrugMasterTab />}
        {tab === 'rejectionCodes' && <RejectionCodeTab />}
        {tab === 'auditLogs' && <AuditLogTab />}
        {tab === 'changeLog' && <ChangeLogTab />}
        {tab === 'accessControlLog' && <AccessControlLogTab />}
        {tab === 'dbExport' && <DbExportTab />}
        {tab === 'workdays' && <WorkDaysTab />}
        {tab === 'purge' && <PurgeTab />}
        {tab === 'purchaseNotification' && <PurchaseNotificationTab />}
      </div>
    </div>
  )
}
