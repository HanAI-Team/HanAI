"use client";
import { confirmPayment } from "@/lib/api/payments";
import { Check, Loader2, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const PaymentSuccessContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const paymentKey = searchParams.get("paymentKey");
    const orderId = searchParams.get("orderId");
    const amount = searchParams.get("amount");

    const run = async () => {
      if (!paymentKey || !orderId || !amount) {
        throw new Error("결제 정보가 올바르지 않습니다.");
      }
      await confirmPayment(paymentKey, orderId, Number(amount));
      setStatus("success");
    };

    run().catch((error: unknown) => {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "결제 확인에 실패했습니다.");
    });
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-card border border-border rounded-2xl p-8 text-center">
        {status === "loading" && (
          <>
            <Loader2 className="w-12 h-12 text-[#EF6600] mx-auto mb-4 animate-spin" />
            <div className="text-lg font-semibold text-text">결제를 확인하고 있습니다...</div>
          </>
        )}

        {status === "success" && (
          <>
            <div className="w-14 h-14 rounded-full bg-[#EF6600]/10 flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-[#EF6600]" />
            </div>
            <div className="text-lg font-semibold text-text mb-2">결제가 완료됐습니다</div>
            <p className="text-sm text-subtext mb-8">멤버십이 정상적으로 등록되었습니다.</p>
            <Link
              href="/membership"
              className="block w-full py-3 rounded-2xl text-sm font-semibold bg-[#EF6600] hover:bg-[#ff7a1f] text-white transition-all"
            >
              멤버십 페이지로 이동
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
              <X className="w-8 h-8 text-red-400" />
            </div>
            <div className="text-lg font-semibold text-text mb-2">결제 확인에 실패했습니다</div>
            <p className="text-sm text-subtext mb-8">{errorMessage}</p>
            <button
              onClick={() => router.push("/membership")}
              className="block w-full py-3 rounded-2xl text-sm font-semibold bg-zinc-700 hover:bg-zinc-600 text-white transition-all"
            >
              멤버십 페이지로 이동
            </button>
          </>
        )}
      </div>
    </div>
  );
};

const PaymentSuccessPage = () => (
  <Suspense fallback={null}>
    <PaymentSuccessContent />
  </Suspense>
);

export default PaymentSuccessPage;
