"use client";
import { useEffect, useState } from "react";
import { getMe } from "@/lib/api/get-me";
import { MembershipBadge } from "@/components/MembershipBadge";
import { Check, Crown, Zap } from "lucide-react";

type User = {
  expired_at: string | null;
  name: string;
  tier: "basic" | "premium";
};

const MembershipPage = () => {
  const [me, setMe] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((data: any) => {
        if (data) setMe(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const isExpired = !me?.expired_at;
const plans = [
  {
    tier: "basic" as const,
    title: "Basic",
    price: "19,000원/월",
    features: [
      "STT 오토차팅",
      "AI 진단 보조",
      "환자 기록 저장/조회",
      "HIRA 청구 파일 생성 (월 50건)",
      "직원 계정 1개",
    ],
    icon: <Zap className="w-5 h-5 text-blue-500" />,
    
  },
  {
    tier: "premium" as const,
    title: "Premium",
    price: "39,000원/월",
    features: [
      "Basic 모든 기능",
      "HIRA 청구 무제한",
      "직원 계정 무제한",
      "데이터 내보내기 (CSV)",
      "우선 고객 지원",
    ],
    icon: <Crown className="w-5 h-5 text-amber-500 " />,
    
    popular: true,
  },
];

{/*
    환자를 제한을 둘지 
    */}

  return (
    <div className="flex flex-col bg-bg min-h-screen">
      {/* 헤더 */}
      

      <div className="flex-1 p-6">
        {/* 현재 멤버십 정보 */}
        {me && (
          <div className="max-w-3xl mx-auto mb-10 bg-card border border-border rounded-2xl p-6 text-center">
            <div className="flex items-center justify-center gap-3 mb-3">
              <span className="text-text font-medium">{me.name}님</span>
              <MembershipBadge tier={me.tier} />
            </div>
            
            {isExpired ? (
              <div className="inline-flex items-center gap-2 bg-red-500/10 text-red-400 text-sm px-4 py-2 rounded-xl">
                ⚠️ 멤버십이 만료되었습니다
              </div>
            ) : (
              <div className="text-sm text-subtext">
                만료일: {new Date(me.expired_at!).toLocaleDateString('ko-KR')}
              </div>
            )}
          </div>
        )}

        {/* 플랜 카드 - 가로 배치 */}
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-8">
            <div className="text-2xl font-bold text-text mb-2">요금제를 선택하세요</div>
            <p className="text-subtext">언제든지 변경할 수 있습니다</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {plans.map((plan) => {
              const isCurrent = me?.tier === plan.tier;

              return (
                <div
                  key={plan.tier}
                  className={`
                    bg-card border-2 rounded-3xl p-8 relative transition-all hover:-translate-y-1
                    ${plan.popular 
                      ? "border-[#EF6600] shadow-xl" 
                      : "border-border hover:border-zinc-600"
                    }
                  `}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#EF6600] text-black text-xs font-bold px-5 py-1 rounded-full">
                      MOST POPULAR
                    </div>
                  )}

                  <div className="flex justify-center mb-6">{plan.icon}</div>

                  <div className="text-center mb-8">
                    <div className="text-2xl font-bold text-text">{plan.title}</div>
                    <div className="text-3xl font-bold text-text mt-3 mb-1">
                      {plan.price}
                    </div>
                  </div>

                  <ul className="space-y-4 mb-10">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3 text-subtext">
                        <Check className="w-5 h-5 text-[#EF6600] flex-shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    className={`
                      w-full py-4 rounded-2xl text-sm font-semibold transition-all
                      ${isCurrent 
                        ? "bg-zinc-700 text-zinc-400 cursor-default" 
                        : "bg-[#EF6600] hover:bg-[#ff7a1f] text-white"
                      }
                    `}
                    disabled={isCurrent}
                  >
                    {isCurrent ? "현재 사용 중" : "이 플랜 선택하기"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MembershipPage;