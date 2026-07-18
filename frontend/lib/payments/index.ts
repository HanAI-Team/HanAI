import { PaymentProvider } from "./types";
import { tossProvider } from "./providers/toss";
import { paddleProvider } from "./providers/paddle";

export function getPaymentProvider(): PaymentProvider {
  const provider = process.env.NEXT_PUBLIC_PAYMENT_PROVIDER;
  return provider === "toss" ? tossProvider : paddleProvider;
}

export * from "./types";
