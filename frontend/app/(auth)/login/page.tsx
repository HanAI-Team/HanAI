'use client'
import LoginForm from '@/components/LoginForm'
import ThemeToggle from '@/components/ThemeToggle'
import Image from 'next/image'

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[#232323] flex flex-col sm:flex-row overflow-y-auto">
      {/* 브랜딩 영역 (모바일: 상단 / 데스크탑: 왼쪽 패널) */}
      <div className="flex-1 min-h-[220px] sm:min-h-0 flex items-center justify-center p-10 relative overflow-hidden">
        <ThemeToggle className="absolute top-3 right-3 z-20" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_40%_60%,rgba(239,102,0,0.14),transparent_65%)]" />
        <div className="relative z-10 text-center">
          <Image
            src="/images/logo-light.png"
            alt="Zinmac"
            width={64}
            height={64}
            className="mx-auto mb-3 w-12 h-12 sm:w-16 sm:h-16 dark:hidden"
            priority
          />
          <Image
            src="/images/logo-dark.png"
            alt="Zinmac"
            width={64}
            height={64}
            className="mx-auto mb-3 w-12 h-12 sm:w-16 sm:h-16 hidden dark:block"
            priority
          />
          <h1 className="text-5xl sm:text-6xl text-white tracking-tight">
            Zinmac
          </h1>
          <p className="text-[#A09892] mt-2 sm:mt-3 text-xs sm:text-sm tracking-widest">
            AI 한의 진료 보조 시스템
          </p>
          <div className="w-10 sm:w-12 h-0.5 bg-[#EF6600] mx-auto mt-4 sm:mt-5" />
        </div>
      </div>

      {/* 폼 패널 */}
      <div className="w-full sm:w-[420px] bg-bg rounded-t-[28px] sm:rounded-none flex-shrink-0 flex items-start sm:items-center justify-center px-7 pt-8 pb-12 sm:p-12">
        <LoginForm />
      </div>
    </div>
  )
}
