'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { register } from '@/lib/api/auth'

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    name: '',
    license_number: '',
    password: '',
    clinic_name: '',
    clinic_address: '',
    clinic_phone: '',
  })

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await register(form)
      alert('회원가입이 완료됐습니다. 관리자 승인 후 로그인 가능합니다.')
      router.push('/login')
    } catch (e: any) {
      setError(e.message || '회원가입 실패')
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
      <div className="w-full md:w-[420px] bg-[#F5F2EE] flex items-center justify-center p-12 overflow-y-auto">
        <div className="w-full">
          <h2 className="text-xl font-medium text-[#232323] mb-1">회원가입</h2>
          <p className="text-sm text-[#8A8480] mb-7">한의사 정보를 입력해주세요</p>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
          )}
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {[
              { label: '이름', name: 'name', type: 'text', placeholder: '이름을 입력해주세요' },
              { label: '면허번호', name: 'license_number', type: 'text', placeholder: '면허번호를 입력해주세요' },
              { label: '비밀번호', name: 'password', type: 'password', placeholder: '비밀번호를 입력해주세요' },
              { label: '한의원명', name: 'clinic_name', type: 'text', placeholder: '한의원명을 입력해주세요' },
              { label: '한의원 주소 (선택)', name: 'clinic_address', type: 'text', placeholder: '주소를 입력해주세요' },
              { label: '한의원 전화 (선택)', name: 'clinic_phone', type: 'text', placeholder: '전화번호를 입력해주세요' },
            ].map(field => (
              <div key={field.name}>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wider mb-1.5">{field.label}</label>
                <input
                  type={field.type}
                  name={field.name}
                  value={form[field.name as keyof typeof form]}
                  onChange={handleChange}
                  placeholder={field.placeholder}
                  className="w-full bg-white border border-[#C8BFB6] rounded-md px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                  required={!field.label.includes('선택')}
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 mt-2"
            >
              {loading ? '가입 중...' : '가입 완료'}
            </button>
          </form>
          <button
            onClick={() => router.push('/login')}
            className="w-full border border-[#C8BFB6] rounded-md py-3 text-sm text-[#8A8480] hover:border-[#232323] hover:text-[#232323] transition-all mt-2"
          >
            ← 로그인으로
          </button>
        </div>
      </div>
    </div>
  )
}
