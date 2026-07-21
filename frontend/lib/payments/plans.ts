import { Crown, Zap, type LucideIcon } from "lucide-react";
import { PlanTier } from "./types";

export interface MembershipPlan {
  tier: PlanTier;
  title: string;
  description: string;
  monthlyPrice: number;
  annualMonthlyPrice: number;
  annualTotalPrice: number;
  features: string[];
  icon: LucideIcon;
  iconClassName: string;
  popular?: boolean;
}

export const plans: MembershipPlan[] = [
  {
    tier: "basic",
    title: "Basic",
    description: "한의원 AI 진료 보조 + HIRA 청구 자동화 핵심 기능",
    monthlyPrice: 39000,
    annualMonthlyPrice: 32400,
    annualTotalPrice: 389000,
    features: [
      "STT 오토차팅",
      "AI 진료 기록 보조",
      "환자 기록 저장/조회",
      "HIRA 청구 파일 생성 (월 50건)",
      "직원 계정 1개",
    ],
    icon: Zap,
    iconClassName: "w-5 h-5 text-blue-500",
  },
  {
    tier: "premium",
    title: "Premium",
    description: "무제한 청구 + 다인 의사 + 우선 지원까지 모든 기능",
    monthlyPrice: 99000,
    annualMonthlyPrice: 82200,
    annualTotalPrice: 986400,
    features: [
      "Basic 모든 기능",
      "HIRA 청구 무제한",
      "직원 계정 무제한",
      "데이터 내보내기 (CSV)",
      "우선 고객 지원",
    ],
    icon: Crown,
    iconClassName: "w-5 h-5 text-amber-500",
    popular: true,
  },
];
