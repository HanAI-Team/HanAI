'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {updateHospital}  from '@/lib/api/hospitals'
import { updateMyProfile } from '@/lib/api/auth'

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

  const [agencyCode, setAgencyCode] = useState('')
  const [acLoading, setAcLoading] = useState(false)
  const [acError, setAcError] = useState<string | null>(null)
  const [acSuccess, setAcSuccess] = useState(false)

  const [birthDate, setBirthDate] = useState('')
  const [bdLoading, setBdLoading] = useState(false)
  const [bdError, setBdError] = useState<string | null>(null)
  const [bdSuccess, setBdSuccess] = useState(false)

  const [chunaCertified, setChunaCertified] = useState(false)
  const [ccLoading, setCcLoading] = useState(false)
  const [ccError, setCcError] = useState<string | null>(null)

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

  const handleSaveAgencyCode = async () => {
    if (!hospitalId) return
    setAcLoading(true)
    setAcError(null)
    try {
      await updateHospital(hospitalId, { agency_code: agencyCode })
      setAcSuccess(true)
      setTimeout(() => setAcSuccess(false), 3000)
    } catch (e: any) {
      setAcError(e.message || '대행청구단체기호 저장에 실패했습니다.')
    } finally {
      setAcLoading(false)
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
        setAgencyCode(me.agency_code || '')
        setBirthDate(me.birth_date || '')
        setChunaCertified(!!me.chuna_training_certified)
      })
      .catch(() => {})
  }, [])

  const handleSaveBirthDate = async () => {
    if (!birthDate) {
      setBdError('생년월일을 입력해주세요.')
      return
    }
    setBdLoading(true)
    setBdError(null)
    try {
      await updateMyProfile({ birth_date: birthDate })
      setBdSuccess(true)
      setTimeout(() => setBdSuccess(false), 3000)
    } catch (e: any) {
      setBdError(e.message || '생년월일 저장에 실패했습니다.')
    } finally {
      setBdLoading(false)
    }
  }

  const handleToggleChunaCertified = async (checked: boolean) => {
    setChunaCertified(checked)
    setCcLoading(true)
    setCcError(null)
    try {
      await updateMyProfile({ chuna_training_certified: checked })
    } catch (e: any) {
      setChunaCertified(!checked)
      setCcError(e.message || '저장에 실패했습니다.')
    } finally {
      setCcLoading(false)
    }
  }

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

              <div>
                <label className="block text-xs text-subtext mb-1.5">대행청구단체기호</label>
                <input
                  type="text"
                  maxLength={5}
                  value={agencyCode}
                  onChange={(e) => setAgencyCode(e.target.value.slice(0, 5))}
                  className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              {acError && <div className="text-red-500 text-sm">{acError}</div>}
              <button
                onClick={handleSaveAgencyCode}
                disabled={acLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
              >
                {acSuccess ? '✓ 저장 완료' : acLoading ? '저장중...' : '저장'}
              </button>
            </div>
          </div>

          {/* 원장 프로필 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">원장 프로필</div>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs text-subtext mb-1.5">생년월일</label>
                <input
                  type="date"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              {bdError && <div className="text-red-500 text-sm">{bdError}</div>}
              <button
                onClick={handleSaveBirthDate}
                disabled={bdLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
              >
                {bdSuccess ? '✓ 저장 완료' : bdLoading ? '저장중...' : '저장'}
              </button>

              <label className="flex items-start gap-3 pt-2 border-t border-border cursor-pointer">
                <input
                  type="checkbox"
                  checked={chunaCertified}
                  disabled={ccLoading}
                  onChange={(e) => handleToggleChunaCertified(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-[#EF6600]"
                />
                <span>
                  <span className="block text-sm text-text">추나요법 사전교육 이수</span>
                  <span className="block text-xs text-subtext mt-0.5">
                    온라인 9시간 + 오프라인 6시간 (총 15시간) 이수 시 체크하세요
                  </span>
                </span>
              </label>
              {ccError && <div className="text-red-500 text-sm">{ccError}</div>}
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