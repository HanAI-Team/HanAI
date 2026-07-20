import { apiCall } from "./client";

export interface PaymentPrepareResponse {
  order_id: string;
  amount: number;
  order_name: string;
}

export interface PaymentConfirmResponse {
  success: boolean;
  tier: string;
  billing_period: string;
  expired_at: string;
  message: string;
}

export async function preparePayment(
  tier: string,
  billingPeriod: "monthly" | "yearly"
): Promise<PaymentPrepareResponse> {
  return apiCall("/api/payments/prepare", {
    method: "POST",
    body: JSON.stringify({ tier, billing_period: billingPeriod }),
  });
}

export async function confirmPayment(
  paymentKey: string,
  orderId: string,
  amount: number
): Promise<PaymentConfirmResponse> {
  return apiCall("/api/payments/confirm", {
    method: "POST",
    body: JSON.stringify({ payment_key: paymentKey, order_id: orderId, amount }),
  });
}

export async function confirmPaddlePayment(
  transactionId: string
): Promise<PaymentConfirmResponse> {
  return apiCall("/api/payments/paddle/confirm", {
    method: "POST",
    body: JSON.stringify({ transaction_id: transactionId }),
  });
}
