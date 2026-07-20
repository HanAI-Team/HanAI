"use client";
import { confirmPaddlePayment } from "@/lib/api/payments";
import { PaymentProvider } from "../types";
import { getPaddlePriceId, getPaddleTierKey } from "../paddlePriceIds";

declare global {
  interface Window {
    Paddle?: {
      Environment: { set: (env: "sandbox" | "production") => void };
      Initialize: (options: {
        token: string | undefined;
        eventCallback?: (event: {
          name: string;
          data?: { transaction_id?: string; [key: string]: unknown };
        }) => void;
      }) => void;
      Checkout: {
        open: (options: {
          items: { priceId: string; quantity: number }[];
          customData?: Record<string, string>;
        }) => void;
      };
    };
  }
}

const PADDLE_SCRIPT_SRC = "https://cdn.paddle.com/paddle/v2/paddle.js";

let scriptLoadingPromise: Promise<void> | null = null;
let initialized = false;
let activeOnSuccess: (() => void) | null = null;
let activeOnError: ((e: unknown) => void) | null = null;

function loadPaddleScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Paddle은 브라우저 환경에서만 사용할 수 있습니다."));
  }
  if (window.Paddle) return Promise.resolve();
  if (scriptLoadingPromise) return scriptLoadingPromise;

  scriptLoadingPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = PADDLE_SCRIPT_SRC;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Paddle.js 로드에 실패했습니다."));
    document.head.appendChild(script);
  });
  return scriptLoadingPromise;
}

function ensureInitialized() {
  if (initialized || !window.Paddle) return;
  window.Paddle.Environment.set("sandbox");
  window.Paddle.Initialize({
    token: process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN,
    eventCallback: (event) => {
      if (event.name === "checkout.completed") {
        const transactionId = event.data?.transaction_id;
        if (!transactionId) {
          activeOnError?.(new Error("Paddle 거래 ID를 확인할 수 없습니다."));
          return;
        }
        confirmPaddlePayment(transactionId)
          .then(() => activeOnSuccess?.())
          .catch((error) => activeOnError?.(error));
      } else if (event.name === "checkout.error") {
        activeOnError?.(event);
      }
    },
  });
  initialized = true;
}

export const paddleProvider: PaymentProvider = {
  async checkout({ tier, billingPeriod, onSuccess, onError }) {
    try {
      await loadPaddleScript();
      ensureInitialized();
      activeOnSuccess = onSuccess;
      activeOnError = onError;

      const planTier = tier as "basic" | "premium";
      const priceId = getPaddlePriceId(planTier, billingPeriod);
      if (!priceId) {
        throw new Error(`Paddle Price ID가 설정되지 않았습니다: ${tier} / ${billingPeriod}`);
      }

      window.Paddle!.Checkout.open({
        items: [{ priceId, quantity: 1 }],
        customData: {
          tier: getPaddleTierKey(planTier),
          billing_period: billingPeriod,
        },
      });
    } catch (error) {
      onError(error);
    }
  },
};
