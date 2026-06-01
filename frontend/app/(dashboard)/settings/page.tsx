'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function SettingsPage() {
  const router = useRouter()
  const [saved, setSaved] = useState(false)

  function handleSave() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <div className="p-6 md:p-8 max-w-[480px]">
      <div className="mb-6">
        <h1 className="font-serif text-2xl text-[#232323]">설정</h1>
        <p className="text-xs text-[#8A8480] mt-1">계정 및 환경 설정</p>
      </div>
      <div className="flex flex-col gap-4">
        <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
          <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-4">프로필</div>
          {[
            { label: '이름', placeholder: '이름을 입력해주세요', type: 'text' },
            { label: '한의원명', placeholder: '한의원명을 입력해주세요', type: 'text' },
            { label: '이메일', placeholder: '이메일을 입력해주세요', type: 'email' },
          ].map((field, i) => (
            <div key={i} className="mb-3">
              <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">{field.label}</label>
              <input
                type={field.type}
                placeholder={field.placeholder}
                className="w-full bg-[#F5F2EE] border border-[#D4CCC4] rounded-md px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
              />
            </div>
          ))}
          <button
            onClick={handleSave}
            className={`w-full rounded-md py-2.5 text-sm font-medium transition-all mt-2 ${
              saved
                ? 'bg-green-600 text-white'
                : 'bg-[#EF6600] text-white hover:opacity-90'
            }`}
          >
            {saved ? '✓ 저장되었습니다' : '저장'}
          </button>
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
