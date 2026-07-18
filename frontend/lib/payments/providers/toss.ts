"use client";
import { loadTossPayments } from "@tosspayments/tosspayments-sdk";
import { preparePayment } from "@/lib/api/payments";
import { PaymentProvider } from "../types";

export const tossProvider: PaymentProvider = {
  async checkout({ tier, billingPeriod, onSuccess, onError }) {
    try {
      const data = await preparePayment(`${tier}_beta`, billingPeriod);

      const tossPayments = await loadTossPayments(
        process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY as string
      );
      const payment = tossPayments.payment({ customerKey: "ANONYMOUS" });
      await payment.requestPayment({
        method: "CARD",
        amount: { currency: "KRW", value: data.amount },
        orderId: data.order_id,
        orderName: data.order_name,
        successUrl: `${window.location.origin}/payment/success`,
        failUrl: `${window.location.origin}/payment/fail`,
      });
      onSuccess();
    } catch (error) {
      onError(error);
    }
  },
};
