'use client'
import { login, staffLogin } from '@/lib/api/auth'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LoginForm() {
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
      router.push('/membership')
    } catch (e: any) {
      setError(e.message || '로그인에 실패했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full">
      <h2 className="text-xl font-medium text-text mb-1">로그인</h2>
      <p className="text-sm text-subtext mb-7">
        면허 한의사 전용 서비스입니다
      </p>

      {/* 의사/간호사 탭 */}
      <div className="flex bg-fill border border-border rounded-md p-1 mb-5">
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
                ? 'bg-card text-text shadow-sm'
                : 'text-subtext'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}
      <form onSubmit={handleLogin} className="flex flex-col gap-4">
        {userType === 'doctor' ? (
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wider mb-1.5">
              면허번호
            </label>
            <input
              type="text"
              value={licenseNumber}
              onChange={(e) => setLicenseNumber(e.target.value)}
              className="w-full bg-card border border-border-strong rounded-md px-4 py-3 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
              placeholder="면허번호를 입력하세요"
              required
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wider mb-1.5">
              아이디
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-card border border-border-strong rounded-md px-4 py-3 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
              placeholder="아이디를 입력하세요"
              required
            />
          </div>
        )}
        <div>
          <label className="block text-xs text-subtext uppercase tracking-wider mb-1.5">
            비밀번호
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-card border border-border-strong rounded-md px-4 py-3 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
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
        <hr className="flex-1 border-border" />
        <span className="text-xs text-muted">또는</span>
        <hr className="flex-1 border-border" />
      </div>
      <button
        onClick={() => router.push('/register')}
        className="w-full border border-border-strong rounded-md py-3 text-sm text-subtext hover:border-text hover:text-text transition-all"
      >
        회원가입
      </button>
    </div>
  )
}
