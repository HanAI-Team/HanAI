'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login } from '@/lib/api/auth'

export default function LoginPage() {
  const router = useRouter()
  const [licenseNumber, setLicenseNumber] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await login(licenseNumber)
      localStorage.setItem('token', data.access_token)
      router.push('/home')
    } catch (e: any) {
      setError(e.message || '로그인에 실패했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-[#232323]">
      <div className="flex-1 hidden md:flex items-center justify-center p-10 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_60%,rgba(239,102,0,0.15),transparent_60%)]" />
        <div className="relative z-10 text-center">
          <h1 className="font-serif text-6xl text-white tracking-tight">Zinmac</h1>
          <p className="text-[#A09892] mt-3 text-sm tracking-widest">AI 한의 진료 보조 시스템</p>
          <div className="w-12 h-0.5 bg-[#EF6600] mx-auto mt-5" />
        </div>
      </div>
      <div className="w-full md:w-[420px] bg-[#F5F2EE] flex items-center justify-center p-12">
        <div className="w-full">
          <h2 className="text-xl font-medium text-[#232323] mb-1">로그인</h2>
          <p className="text-sm text-[#8A8480] mb-7">면허 한의사 전용 서비스입니다</p>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
          )}
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs text-[#8A8480] uppercase tracking-wider mb-1.5">면허번호</label>
              <input
                type="text"
                value={licenseNumber}
                onChange={e => setLicenseNumber(e.target.value)}
                className="w-full bg-white border border-[#C8BFB6] rounded-md px-4 py-3 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                placeholder="면허번호를 입력하세요"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>
          <div className="flex items-center gap-3 my-4">
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
