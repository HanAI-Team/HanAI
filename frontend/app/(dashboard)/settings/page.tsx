'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export default function SettingsPage() {
  const router = useRouter()
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)

  function handleLogout() {
    localStorage.removeItem('token')
    router.push('/login')
  }

  async function handleChangePassword() {
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
        headers: getHeaders(),
        body: JSON.stringify({
          current_password: pwForm.current_password,
          new_password: pwForm.new_password,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '비밀번호 변경 실패')
      }
      setPwSuccess(true)
      setPwForm({ current_password: '', new_password: '', confirm: '' })
      setTimeout(() => setPwSuccess(false), 3000)
    } catch (e: any) {
      setPwError(e.message)
    } finally {
      setPwLoading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-[480px]">
      <div className="mb-6">
        <h1 className="font-serif text-2xl text-[#232323]">설정</h1>
        <p className="text-xs text-[#8A8480] mt-1">계정 및 환경 설정</p>
      </div>
      <div className="flex flex-col gap-4">
        <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
          <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-4">비밀번호 변경</div>
          <form onSubmit={(e) => { e.preventDefault(); handleChangePassword() }} className="flex flex-col gap-3">
            {[
              { label: '현재 비밀번호', key: 'current_password' },
              { label: '새 비밀번호', key: 'new_password' },
              { label: '새 비밀번호 확인', key: 'confirm' },
            ].map((field) => (
              <div key={field.key}>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">{field.label}</label>
                <input
                  type="password"
                  value={pwForm[field.key as keyof typeof pwForm]}
                  onChange={(e) => setPwForm((f) => ({ ...f, [field.key]: e.target.value }))}
                  required
                  className="w-full bg-[#F5F2EE] border border-[#D4CCC4] rounded-md px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
            ))}
            {pwError && (
              <div className="text-xs text-red-500">{pwError}</div>
            )}
            <button
              type="submit"
              disabled={pwLoading}
              className={`w-full rounded-md py-2.5 text-sm font-medium transition-all mt-1 ${
                pwSuccess
                  ? 'bg-green-600 text-white'
                  : 'bg-[#EF6600] text-white hover:opacity-90 disabled:opacity-50'
              }`}
            >
              {pwSuccess ? '✓ 변경되었습니다' : pwLoading ? '변경 중...' : '비밀번호 변경'}
            </button>
          </form>
        </div>
        <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
          <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-4">계정</div>
          <button
            onClick={handleLogout}
            className="w-full border border-[#C8BFB6] rounded-md py-2.5 text-sm text-[#8A8480] hover:border-[#232323] hover:text-[#232323] transition-all"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>
  )
}
