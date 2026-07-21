'use client'
import LoginForm from '@/components/LoginForm'
import SplashBars from '@/components/SplashBars'
import { plans } from '@/lib/payments/plans'
import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'

const FEATURES = [
  {
    icon: '🎙️',
    title: '음성 녹음 자동 차팅',
    desc: '진료 중 대화를 녹음하면 자동으로 차트를 정리해줍니다.',
  },
  {
    icon: '🧭',
    title: '사상체질 분석 참고자료',
    desc: '환자 데이터를 기반으로 사상체질 분석 참고자료를 제공합니다.',
  },
  {
    icon: '🌿',
    title: '한약 처방 참고자료',
    desc: '체질과 증상에 맞는 처방 참고자료를 제공합니다.',
  },
  {
    icon: '🗂️',
    title: '환자 · 진료기록 관리',
    desc: '환자 목록과 진료기록을 체계적으로 관리합니다.',
  },
]

// 로그인 패널은 마케팅 패널과 무관하게 항상 라이트 톤으로 고정 (사이트 다크모드 토글의 영향을 받지 않음)
const LIGHT_VARS = {
  '--color-bg': '#F5F2EE',
  '--color-card': '#FFFFFF',
  '--color-fill': '#EDE8E2',
  '--color-border': '#D4CCC4',
  '--color-border-strong': '#C8BFB6',
  '--color-text': '#232323',
  '--color-subtext': '#8A8480',
  '--color-muted': '#B0AAA4',
} as CSSProperties

export default function RootPage() {
  const [barsVisible, setBarsVisible] = useState(false)
  const [textVisible, setTextVisible] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setBarsVisible(true), 50)
    const t2 = setTimeout(() => setTextVisible(true), 500)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [])

  return (
    <div className="flex flex-col md:flex-row min-h-screen">
      {/* 마케팅 패널 */}
      <main className="w-full md:w-[62%] bg-gradient-to-br from-[#2b241f] to-[#15120f] text-white">
        <section className="px-6 sm:px-10 md:px-14 py-14 md:py-16 border-b border-white/10">
          <SplashBars
            visible={barsVisible}
            className="w-20 h-20 mb-4"
          />
          <h1
            className="text-3xl font-bold tracking-tight mb-2 transition-opacity duration-500"
            style={{ opacity: textVisible ? 1 : 0 }}
          >
            Zinmac
          </h1>
          <p
            className="text-sm text-white/55 mb-5 transition-opacity duration-500"
            style={{ opacity: textVisible ? 1 : 0 }}
          >
            AI 한의 진료 보조 시스템
          </p>
          <span className="inline-block px-3 py-1.5 rounded-full bg-[#cf6a3c]/[0.18] text-[#f3a67d] text-xs font-bold mb-4">
            한의사 전용 서비스
          </span>
          <h2 className="text-[26px] leading-snug tracking-tight mb-3.5 text-white">
            진료 기록 정리부터 참고자료까지,
            <br />
            진맥이 함께합니다
          </h2>
          <p className="text-[15px] text-white/62 max-w-[480px]">
            진맥(Zinmac)은 한의사를 위한 AI 진료 기록 보조 시스템입니다.
            진료실에서의 음성을 자동으로 차팅하고, 사상체질 분석과 처방 참고자료까지
            하나의 서비스에서 확인할 수 있습니다. 최종 진단과 처방은 면허 한의사가 직접 판단합니다.
          </p>
        </section>

        <section className="px-6 sm:px-10 md:px-14 py-14 md:py-16 border-b border-white/10">
          <h2 className="text-2xl tracking-tight mb-3.5 text-white">주요 기능</h2>
          <p className="text-[15px] text-white/62 mb-8">진료 효율과 정확도를 높이는 핵심 기능</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="border border-white/10 rounded-[14px] p-5 bg-white/[0.06]">
                <div className="w-9 h-9 rounded-[9px] bg-[#cf6a3c]/[0.16] flex items-center justify-center text-[17px] mb-3">
                  {f.icon}
                </div>
                <h3 className="text-[15.5px] text-white mb-1.5">{f.title}</h3>
                <p className="text-[13px] text-white/55">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-6 sm:px-10 md:px-14 py-14 md:py-16 border-b border-white/10">
          <h2 className="text-2xl tracking-tight mb-3.5 text-white">가격</h2>
          <p className="text-[15px] text-white/62 mb-8">
            지금 가입하면 베타 특가가 2년간 고정됩니다. 언제든지 플랜을 변경할 수 있습니다.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.tier}
                className={`border rounded-[14px] p-5 bg-white/[0.06] ${
                  plan.popular ? 'border-[#cf6a3c]/60' : 'border-white/10'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <h3 className="text-[15.5px] text-white font-semibold">{plan.title}</h3>
                  {plan.popular && (
                    <span className="px-2 py-0.5 rounded-full bg-[#cf6a3c]/[0.18] text-[#f3a67d] text-[10px] font-bold">
                      인기
                    </span>
                  )}
                </div>
                <p className="text-[13px] text-white/55 mb-4">{plan.description}</p>
                <div className="text-2xl font-bold text-white mb-0.5">
                  {plan.monthlyPrice.toLocaleString('ko-KR')}원
                  <span className="text-[13px] font-normal text-white/50">/월</span>
                </div>
                <p className="text-[12px] text-white/40 mb-4">
                  연간 결제 시 월 {plan.annualMonthlyPrice.toLocaleString('ko-KR')}원 (연{' '}
                  {plan.annualTotalPrice.toLocaleString('ko-KR')}원)
                </p>
                <ul className="space-y-1.5">
                  {plan.features.map((f) => (
                    <li key={f} className="text-[12.5px] text-white/55 flex items-start gap-1.5">
                      <span className="text-[#f3a67d]">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="px-6 sm:px-10 md:px-14 py-14 md:py-16">
          <h2 className="text-2xl tracking-tight mb-3.5 text-white">문의하기</h2>
          <p className="text-[15px] text-white/62 mb-6">서비스 도입 및 제휴 관련 문의는 아래로 연락해 주세요.</p>
          <div className="inline-flex gap-3 items-center border border-white/10 rounded-xl px-5 py-3.5 bg-white/[0.06]">
            <span>✉️</span>
            <a href="mailto:sst@zinmac.kr" className="text-[#f3a67d]">
              sst@zinmac.kr
            </a>
          </div>
        </section>
      </main>

      {/* 로그인 패널 */}
      <aside
        className="w-full md:w-[38%] md:min-w-[320px] md:sticky md:top-0 md:h-screen bg-[#f5f2ee] flex items-center justify-center px-6 py-12 md:p-8"
        style={LIGHT_VARS}
      >
        <div className="w-full max-w-[320px]">
          <LoginForm />
        </div>
      </aside>
    </div>
  )
}
