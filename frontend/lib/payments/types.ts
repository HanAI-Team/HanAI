export type PlanTier = "basic" | "premium";
export type BillingPeriod = "monthly" | "yearly";

export interface PaymentCheckoutParams {
  tier: string;
  billingPeriod: BillingPeriod;
  onSuccess: () => void;
  onError: (e: unknown) => void;
}

export interface PaymentProvider {
  checkout(params: PaymentCheckoutParams): Promise<void>;
}
