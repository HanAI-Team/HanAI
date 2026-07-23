'use client'
import { updateMyProfile } from '@/lib/api/auth'
import { updateHospital } from '@/lib/api/hospitals'
import { parseErrorDetail } from '@/lib/errorMessage'
import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function GeneralTab() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [showForceBanner, setShowForceBanner] = useState(false)
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

  const [approvalNo, setApprovalNo] = useState('')
  const [anLoading, setAnLoading] = useState(false)
  const [anError, setAnError] = useState<string | null>(null)
  const [anSuccess, setAnSuccess] = useState(false)

  const [isOwner, setIsOwner] = useState(false)
  const [sessionTimeoutMinutes, setSessionTimeoutMinutes] = useState('')
  const [stLoading, setStLoading] = useState(false)
  const [stError, setStError] = useState<string | null>(null)
  const [stSuccess, setStSuccess] = useState(false)

  const [birthDate, setBirthDate] = useState('')
  const [bdLoading, setBdLoading] = useState(false)
  const [bdError, setBdError] = useState<string | null>(null)
  const [bdSuccess, setBdSuccess] = useState(false)

  const [chunaCertified, setChunaCertified] = useState(false)
  const [ccLoading, setCcLoading] = useState(false)
  const [ccError, setCcError] = useState<string | null>(null)

  const [lastLoginIp, setLastLoginIp] = useState<string | null>(null)
  const [lastLoginAt, setLastLoginAt] = useState<string | null>(null)

  useEffect(() => {
    setShowForceBanner(searchParams.get('force') === 'true')
  }, [searchParams])

  const handleChangePassword = async () => {
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('새 비밀번호가 일치하지 않습니다.')
      return
    }
    if (pwForm.new_password.length < 8) {
      setPwError('비밀번호는 영대문자/영소문자/숫자/특수문자 중 3종류 이상 조합 시 8자리 이상, 2종류 이상 조합 시 10자리 이상이어야 합니다.')
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
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(parseErrorDetail(err?.detail) || '비밀번호 변경 실패')
      }
      setPwSuccess(true)
      setPwForm({ current_password: '', new_password: '', confirm: '' })
      if (showForceBanner) {
        setShowForceBanner(false)
        router.replace('/settings')
      }
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

  const handleSaveApprovalNo = async () => {
    if (!hospitalId) return
    setAnLoading(true)
    setAnError(null)
    try {
      await updateHospital(hospitalId, { approval_no: approvalNo })
      setAnSuccess(true)
      setTimeout(() => setAnSuccess(false), 3000)
    } catch (e: any) {
      setAnError(e.message || '소프트웨어 승인번호 저장에 실패했습니다.')
    } finally {
      setAnLoading(false)
    }
  }

  const handleSaveSessionTimeout = async () => {
    if (!hospitalId) return
    setStLoading(true)
    setStError(null)
    try {
      const res = await fetch(`${BASE_URL}/api/hospitals/${hospitalId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ session_timeout_minutes: Number(sessionTimeoutMinutes) }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(parseErrorDetail(err?.detail) || '세션 타임아웃 저장에 실패했습니다.')
      }
      setStSuccess(true)
      window.dispatchEvent(new Event('hanai:session-timeout-updated'))
      setTimeout(() => setStSuccess(false), 3000)
    } catch (e: any) {
      setStError(e.message)
    } finally {
      setStLoading(false)
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
        setApprovalNo(me.approval_no || '')
        setBirthDate(me.birth_date || '')
        setChunaCertified(!!me.chuna_training_certified)
        setLastLoginIp(me.last_login_ip || null)
        setLastLoginAt(me.last_login_at || null)
        setIsOwner(me.role === 'owner')
        setSessionTimeoutMinutes(String(me.session_timeout_minutes ?? 30))
      })
      .catch(() => {})
  }, [])

  const formatLastLoginAt = (raw: string | null) => {
    if (!raw || raw.length !== 14) return '-'
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)} ${raw.slice(8, 10)}:${raw.slice(10, 12)}:${raw.slice(12, 14)}`
  }

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
        {showForceBanner && (
          <div className="bg-amber-50 border border-amber-300 text-amber-800 rounded-md p-3 text-sm mb-6">
            관리자에 의해 비밀번호가 초기화되었습니다. 아래에서 새 비밀번호로 변경해 주세요.
          </div>
        )}
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

          {/* 최종 로그인 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">최종 로그인</div>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs text-subtext mb-1.5">마지막 로그인 IP</label>
                <div className="text-sm text-text">{lastLoginIp || '-'}</div>
              </div>
              <div>
                <label className="block text-xs text-subtext mb-1.5">마지막 로그인 일시</label>
                <div className="text-sm text-text">{formatLastLoginAt(lastLoginAt)}</div>
              </div>
            </div>
          </div>

          {/* 병원 정보 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">병원 정보</div>
            <div className="flex flex-col gap-4">
              {hospitalId !== null && !institutionCode && (
                <div className="text-amber-600 text-sm bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                  요양기관기호가 설정되지 않았습니다. 입력하지 않으면 EDI/SAM 청구파일 및
                  처방전 생성이 불가능합니다.
                </div>
              )}
              <div>
                <label className="block text-xs text-subtext mb-1.5">
                  요양기관기호 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  maxLength={8}
                  required
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

              <div>
                <label className="block text-xs text-subtext mb-1.5">소프트웨어 승인번호</label>
                <p className="text-xs text-subtext mb-1.5">HIRA 기능검사 통과 후 발급되는 승인번호</p>
                <input
                  type="text"
                  value={approvalNo}
                  onChange={(e) => setApprovalNo(e.target.value)}
                  className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              {anError && <div className="text-red-500 text-sm">{anError}</div>}
              <button
                onClick={handleSaveApprovalNo}
                disabled={anLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
              >
                {anSuccess ? '✓ 저장 완료' : anLoading ? '저장중...' : '저장'}
              </button>

              {isOwner && (
                <>
                  <div>
                    <label className="block text-xs text-subtext mb-1.5">세션 타임아웃(분)</label>
                    <p className="text-xs text-subtext mb-1.5">
                      일정 시간 미사용 시 자동 로그아웃되는 시간입니다. 5~30분 사이로 설정할 수 있습니다.
                    </p>
                    <input
                      type="number"
                      min={5}
                      max={30}
                      value={sessionTimeoutMinutes}
                      onChange={(e) => setSessionTimeoutMinutes(e.target.value)}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-[#EF6600]"
                    />
                  </div>
                  {stError && <div className="text-red-500 text-sm">{stError}</div>}
                  <button
                    onClick={handleSaveSessionTimeout}
                    disabled={stLoading}
                    className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
                  >
                    {stSuccess ? '✓ 저장 완료' : stLoading ? '저장중...' : '저장'}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* 원장 프로필 */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="text-sm font-medium text-text mb-5">원장 프로필</div>
            <div className="flex flex-col gap-4">
              {hospitalId !== null && !birthDate && (
                <div className="text-amber-600 text-sm bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                  생년월일이 설정되지 않았습니다. 입력하지 않으면 EDI/SAM 청구파일의
                  작성자생년월일란이 비어 청구가 반려될 수 있습니다.
                </div>
              )}
              <div>
                <label className="block text-xs text-subtext mb-1.5">
                  생년월일 <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  required
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  min="1900-01-01"
                  max={new Date().toISOString().slice(0, 10)}
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
              <span className="block text-xs text-red-600 mt-1 text-center">
              * 허위 입력 시 부당청구에 해당할 수 있으며, 이에 대한 법적 책임은 본인에게 있습니다.
            </span>
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