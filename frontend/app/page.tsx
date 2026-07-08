'use client'
import LoginForm from '@/components/LoginForm'
import SplashBars from '@/components/SplashBars'
import ThemeToggle from '@/components/ThemeToggle'
import { useEffect, useState } from 'react'

export default function RootPage() {
  const [barsVisible, setBarsVisible] = useState(false)
  const [textVisible, setTextVisible] = useState(false)
  const [settled, setSettled] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setBarsVisible(true), 50)
    const t2 = setTimeout(() => setTextVisible(true), 1000)
    const t3 = setTimeout(() => setSettled(true), 1500)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [])

  return (
    <div className="h-screen bg-[#232323] flex flex-col md:flex-row overflow-hidden">
      {/* 브랜딩/스플래시 영역 (모바일: 위쪽 절반 / 데스크탑: 왼쪽 절반) */}
      <div
        className={`flex items-center justify-center relative overflow-hidden transition-all duration-500 ease-in-out ${
          settled ? 'w-full h-[260px] md:h-full md:w-[calc(100%-420px)]' : 'w-full h-full'
        }`}
      >
        {settled && <ThemeToggle className="absolute top-3 right-3 z-20" />}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_40%_60%,rgba(239,102,0,0.14),transparent_65%)]" />
        <div className="relative z-10 text-center">
          <SplashBars
            visible={barsVisible}
            className={`mx-auto mb-3 transition-all duration-500 ease-in-out ${
              settled ? 'w-12 h-12 md:w-16 md:h-16' : 'w-20 h-20'
            }`}
          />
          <h1
            className="text-5xl md:text-6xl tracking-tight bg-gradient-to-b from-[#FF6B00] to-[#FF9500] bg-clip-text text-transparent dark:bg-none dark:text-[#7FFFD4] transition-opacity duration-500"
            style={{ opacity: textVisible ? 1 : 0 }}
          >
            Zinmac
          </h1>
          <p
            className="text-[#A09892] mt-2 md:mt-3 text-xs md:text-sm tracking-widest transition-opacity duration-500"
            style={{ opacity: textVisible ? 1 : 0 }}
          >
            AI 한의 진료 보조 시스템
          </p>
          <div
            className="w-10 md:w-12 h-0.5 bg-[#EF6600] mx-auto mt-4 md:mt-5 transition-opacity duration-500"
            style={{ opacity: textVisible ? 1 : 0 }}
          />
        </div>
      </div>

      {/* 로그인 폼 패널 (아래/오른쪽에서 슬라이드인) */}
      <div
        className={`bg-bg overflow-hidden transition-all duration-500 ease-in-out ${
          settled ? 'w-full h-[calc(100%-260px)] md:h-full md:w-[420px]' : 'w-full h-0 md:w-0 md:h-full'
        }`}
      >
        <div
          className={`h-full flex items-start md:items-center justify-center px-7 pt-8 pb-12 md:p-12 transition-transform duration-500 ease-in-out ${
            settled
              ? 'translate-y-0 md:translate-x-0'
              : 'translate-y-full md:translate-y-0 md:translate-x-full'
          }`}
        >
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
