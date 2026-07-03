'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {updateHospital}  from '@/lib/api/hospitals'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function GeneralTab() {
  const router = useRouter()
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)

  const [hospitalId, setHospitalId] = useState<string | null>(null)
  const [institutionCode, setInstitutionCode] = useState('')
  const [hcLoading, setHcLoading] = useState(false)
  const [hcError, setHcError] = useState<string | null>(null)
  const [hcSuccess, setHcSuccess] = useState(false)

  const handleChangePassword = async () => {
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('새 비밀번호가 일치하지 않습니다.')
      return
    }
    if (pwForm.new_password.length < 8) {
      setPwError('비밀번호는 8자 이상이어야 합니다.')
      return
    }
    setPwLoading(true)
    setPwError(null)
    try {
      const res = await fetch(`${BASE_URL}/api/auth/password`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          current_password: pwForm.current_password,
          new_password: pwForm.new_password,
        }),
      })
      if (!res.ok) throw new Error('비밀번호 변경 실패')
      setPwSuccess(true)
      setPwForm({ current_password: '', new_password: '', confirm: '' })
      setTimeout(() => setPwSuccess(false), 3000)
    } catch (e: any) {
      setPwError(e.message)
    } finally {
      setPwLoading(false)
    }
  }

  const handleSaveInstitutionCode = async () => {
    if (!hospitalId) return
    if (!/^\d{8}$/.test(institutionCode)) {
      setHcError('요양기관기호는 8자리 숫자여야 합니다.')
      return
    }
    setHcLoading(true)
    setHcError(null)
    try {
      await updateHospital(hospitalId, { institution_code: institutionCode })
      setHcSuccess(true)
      setTimeout(() => setHcSuccess(false), 3000)
    } catch (e: any) {
      setHcError(e.message || '요양기관기호 저장에 실패했습니다.')
    } finally {
      setHcLoading(false)
    }
  }

  useEffect(() => {
    fetch(`${BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then((res) => res.json())
      .then((me) => {
        setHospitalId(me.hospital_id)
        setInstitutionCode(me.institution_code || '')
      })
      .catch(() => {})
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <div className="flex justify-center items-start min-h-[calc(100vh-180px)]">
      <div className="w-full max-w-[1100px]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* 비밀번호 변경 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">비밀번호 변경</div>
            <div className="flex flex-col gap-4">
              {[
                { label: '현재 비밀번호', key: 'current_password' },
                { label: '새 비밀번호', key: 'new_password' },
                { label: '새 비밀번호 확인', key: 'confirm' },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs text-subtext mb-1.5">{field.label}</label>
                  <input
                    type="password"
                    value={pwForm[field.key as keyof typeof pwForm]}
                    onChange={(e) => setPwForm((f) => ({ ...f, [field.key]: e.target.value }))}
                    className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                  />
                </div>
              ))}
              {pwError && <div className="text-red-500 text-sm">{pwError}</div>}
              <button
                onClick={handleChangePassword}
                disabled={pwLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
              >
                {pwSuccess ? '✓ 변경 완료' : pwLoading ? '처리중...' : '비밀번호 변경'}
              </button>
            </div>
          </div>

          {/* 병원 정보 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">병원 정보</div>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs text-subtext mb-1.5">요양기관기호</label>
                <input
                  type="text"
                  maxLength={8}
                  value={institutionCode}
                  onChange={(e) => setInstitutionCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
                  className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              {hcError && <div className="text-red-500 text-sm">{hcError}</div>}
              <button
                onClick={handleSaveInstitutionCode}
                disabled={hcLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
              >
                {hcSuccess ? '✓ 저장 완료' : hcLoading ? '저장중...' : '저장'}
              </button>
            </div>
          </div>

        </div>

        {/* 로그아웃 (하단 전체 폭) */}
        <div className="mt-6 bg-card border border-border rounded-2xl p-6">
          <button 
            onClick={handleLogout}
            className="w-full py-4 text-red-400 border border-red-500/30 rounded-2xl hover:bg-red-500/10 transition-colors cursor-pointer"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>
  )
}