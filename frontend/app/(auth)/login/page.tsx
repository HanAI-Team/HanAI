'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login, staffLogin } from '@/lib/api/auth'

export default function LoginPage() {
  const router = useRouter()
  const [userType, setUserType] = useState<'doctor' | 'nurse'>('doctor')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data =
        userType === 'doctor'
          ? await login(licenseNumber, password)
          : await staffLogin(username, password)
      localStorage.setItem('token', data.access_token)
      router.push('/home')
    } catch (e: any) {
      setError(e.message || '로그인에 실패했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#232323] flex flex-col sm:flex-row overflow-y-auto">
      {/* 브랜딩 영역 (모바일: 상단 / 데스크탑: 왼쪽 패널) */}
      <div className="flex-1 min-h-[220px] sm:min-h-0 flex items-center justify-center p-10 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_40%_60%,rgba(239,102,0,0.14),transparent_65%)]" />
        <div className="relative z-10 text-center">
          <h1 className="font-serif text-5xl sm:text-6xl text-white tracking-tight">
            Zinmac
          </h1>
          <p className="text-[#A09892] mt-2 sm:mt-3 text-xs sm:text-sm tracking-widest">
            AI 한의 진료 보조 시스템
          </p>
          <div className="w-10 sm:w-12 h-0.5 bg-[#EF6600] mx-auto mt-4 sm:mt-5" />
        </div>
      </div>

      {/* 폼 패널 */}
      <div className="w-full sm:w-[420px] bg-[#F5F2EE] rounded-t-[28px] sm:rounded-none flex-shrink-0 flex items-start sm:items-center justify-center px-7 pt-8 pb-12 sm:p-12">
        <div className="w-full">
          <h2 className="text-xl font-medium text-[#232323] mb-1">로그인</h2>
          <p className="text-sm text-[#8A8480] mb-7">
            면허 한의사 전용 서비스입니다
          </p>

          {/* 의사/간호사 탭 */}
          <div className="flex bg-[#EDE8E2] border border-[#D4CCC4] rounded-md p-1 mb-5">
            {[
              { value: 'doctor', label: '의사' },
              { value: 'nurse', label: '직원' },
            ].map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => {
                  setUserType(tab.value as 'doctor' | 'nurse')
                  setError('')
                }}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  userType === tab.value
                    ? 'bg-white text-[#232323] shadow-sm'
                    : 'text-[#8A8480]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            {userType === 'doctor' ? (
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wider mb-1.5">
                  면허번호
                </label>
                <input
                  type="text"
                  value={licenseNumber}
                  onChange={(e) => setLicenseNumber(e.target.value)}
                  className="w-full bg-white border border-[#C8BFB6] rounded-md px-4 py-3 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                  placeholder="면허번호를 입력하세요"
                  required
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wider mb-1.5">
                  아이디
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-white border border-[#C8BFB6] rounded-md px-4 py-3 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                  placeholder="아이디를 입력하세요"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-[#8A8480] uppercase tracking-wider mb-1.5">
                비밀번호
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white border border-[#C8BFB6] rounded-md px-4 py-3 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                placeholder="비밀번호를 입력하세요"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 mt-1"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>
          <div className="flex items-center gap-3 my-5">
            <hr className="flex-1 border-[#D4CCC4]" />
            <span className="text-xs text-[#B0AAA4]">또는</span>
            <hr className="flex-1 border-[#D4CCC4]" />
          </div>
          <button
            onClick={() => router.push('/register')}
            className="w-full border border-[#C8BFB6] rounded-md py-3 text-sm text-[#8A8480] hover:border-[#232323] hover:text-[#232323] transition-all"
          >
            회원가입
          </button>
        </div>
      </div>
    </div>
  )
}
