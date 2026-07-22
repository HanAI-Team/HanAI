"use client";
import { MembershipBadge } from "@/components/MembershipBadge";
import { getMe } from "@/lib/api/get-me";
import { getPaymentProvider } from "@/lib/payments";
import { plans } from "@/lib/payments/plans";
import { Check } from "lucide-react";
import { useEffect, useState } from "react";

type User = {
  expired_at: string | null;
  is_expired?: boolean;
  name: string;
  tier: "basic" | "premium";
};

const MembershipPage = () => {
  const [me, setMe] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const [agreed, setAgreed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getMe()
      .then((data: any) => {
        if (data) setMe(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const isExpired = !me?.expired_at;
  const isSubscriptionExpired = !!(
    me?.is_expired || (me?.expired_at && new Date(me.expired_at) < new Date())
  );

  const handleSelectPlan = async (tier: string) => {
    const billingPeriod = billingCycle === "annual" ? "yearly" : "monthly";
    const provider = getPaymentProvider();
    await provider.checkout({
      tier,
      billingPeriod,
      onSuccess: () => {},
      onError: (error) => {
        console.error(error);
        alert("결제 요청에 실패했습니다.");
      },
    });
  };

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
          <div className="flex justify-center mb-4">
            <div className="inline-flex items-center gap-2 bg-[#EF6600]/10 text-[#EF6600] text-sm font-semibold px-4 py-1.5 rounded-full border border-[#EF6600]/30">
              🎉 베타 특가 — 지금 가입하면 이 가격 2년간 고정
            </div>
          </div>

          <div className="text-center mb-8">
            <div className="text-2xl font-bold text-text mb-2">요금제를 선택하세요</div>
            <p className="text-subtext">언제든지 변경할 수 있습니다</p>
          </div>

          <div className="flex items-center justify-center gap-3 mb-8">
            <div className="inline-flex items-center bg-card border border-border rounded-full p-1">
              <button
                type="button"
                onClick={() => setBillingCycle("monthly")}
                className={`px-5 py-2 rounded-full cursor-pointer  text-sm font-semibold transition-all ${
                  billingCycle === "monthly" ? "bg-[#EF6600] text-white" : "text-subtext"
                }`}
              >
                월간
              </button>
              <button
                type="button"
                onClick={() => setBillingCycle("annual")}
                className={`px-5 cursor-pointer py-2 rounded-full text-sm font-semibold transition-all ${
                  billingCycle === "annual" ? "bg-[#EF6600] text-white" : "text-subtext"
                }`}
              >
                연간 (2개월 무료)
              </button>
            </div>
        
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {plans.map((plan) => {
              const isCurrent = me?.tier === plan.tier && !isSubscriptionExpired;

              return (
                <div role="button" tabIndex={0}
                  key={plan.tier}
                  onClick={() => {
                    setAgreed({ [plan.tier]: true });
                  }}
                  className={`
                    bg-card cursor-pointer border-2 rounded-3xl p-8 relative transition-all hover:-translate-y-1
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

                  <div className="flex justify-center mb-6">
                    <plan.icon className={plan.iconClassName} />
                  </div>

                  <div className="text-center mb-8">
                    <div className="text-2xl font-bold text-text">{plan.title}</div>
                    <p className="text-sm text-subtext mt-2">{plan.description}</p>
                    <div className="text-3xl font-bold text-text mt-3 mb-1">
                      {billingCycle === "annual"
                        ? `${plan.annualMonthlyPrice.toLocaleString("ko-KR")}원/월`
                        : `${plan.monthlyPrice.toLocaleString("ko-KR")}원/월`}
                    </div>
                    {billingCycle === "annual" && (
                      <div className="text-xs text-subtext">
                        연간 {plan.annualTotalPrice.toLocaleString("ko-KR")}원 결제
                      </div>
                    )}
                  </div>

                  <ul className="space-y-4 mb-10">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3 text-subtext">
                        <Check className="w-5 h-5 text-[#EF6600] flex-shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <label
                    className="flex items-start gap-2 mb-4 cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={!!agreed[plan.tier]}
                      onChange={(e) =>
                        setAgreed(e.target.checked ? { [plan.tier]: true } : {})
                      }
                      className="mt-1 w-4 h-4 accent-[#EF6600]"
                    />
                    <span className="text-xs text-subtext">
                      결제 즉시 서비스 이용이 개시되며 이에 동의합니다
                    </span>
                  </label>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectPlan(plan.tier);
                    }}
                    className={`
                      w-full py-4 rounded-2xl text-sm font-semibold transition-all
                      ${isCurrent
                        ? "bg-zinc-700 text-zinc-400 cursor-default"
                        : !agreed[plan.tier]
                        ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
                        : "bg-[#EF6600] hover:bg-[#ff7a1f] text-white"
                      }
                    `}
                    disabled={isCurrent || !agreed[plan.tier]}
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