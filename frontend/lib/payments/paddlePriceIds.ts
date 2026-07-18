import { BillingPeriod, PlanTier } from "./types";

// Paddle Price ID 매핑.
// "_beta" 접미사가 붙은 키는 현재 진행 중인 베타 특가 기간용 (toss의 `${tier}_beta` 관례와 동일).
// 베타 종료 후에는 접미사 없는 키("basic"/"premium")를 사용할 예정.
export const PADDLE_PRICE_IDS: Record<string, Record<BillingPeriod, string>> = {
  basic_beta: {
    monthly: "pri_01kxv53h04h3j5q7wn03tezw7v",
    yearly: "pri_01kxv53h91dxhjwgvvxwszy59f",
  },
  premium_beta: {
    monthly: "pri_01kxv53j3bdxefeswxn83twtj3",
    yearly: "pri_01kxv53jd30tb3hjexn8mz05ae",
  },
  basic: {
    monthly: "pri_01kxv53hhpgzm0czg4f541qyyg",
    yearly: "pri_01kxv53htqzbnykx94ybc206np",
  },
  premium: {
    monthly: "pri_01kxv53js1swwg8pwatm6v5d68",
    yearly: "pri_01kxv53k1r78s3paz6zdznd7ez",
  },
};

// 현재는 베타 특가 기간이므로 "_beta" 키를 사용. 베타 종료 시 이 함수만 고치면 됨
// (가격 조회·customData에 동일하게 쓰여야 하므로 별도 함수로 분리).
export function getPaddleTierKey(tier: PlanTier): string {
  return `${tier}_beta`;
}

export function getPaddlePriceId(tier: PlanTier, billingPeriod: BillingPeriod): string {
  const key = getPaddleTierKey(tier);
  return PADDLE_PRICE_IDS[key]?.[billingPeriod] ?? "";
}
