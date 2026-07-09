"use client";
import { X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

const PaymentFailContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const message = searchParams.get("message") || "결제가 취소되었거나 실패했습니다.";
  const code = searchParams.get("code");

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-card border border-border rounded-2xl p-8 text-center">
        <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
          <X className="w-8 h-8 text-red-400" />
        </div>
        <div className="text-lg font-semibold text-text mb-2">결제에 실패했습니다</div>
        <p className="text-sm text-subtext mb-2">{message}</p>
        {code && <p className="text-xs text-subtext mb-8">오류 코드: {code}</p>}
        <button
          onClick={() => router.push("/membership")}
          className="block w-full py-3 rounded-2xl text-sm font-semibold bg-[#EF6600] hover:bg-[#ff7a1f] text-white transition-all mt-6"
        >
          다시 시도하기
        </button>
      </div>
    </div>
  );
};

const PaymentFailPage = () => (
  <Suspense fallback={null}>
    <PaymentFailContent />
  </Suspense>
);

export default PaymentFailPage;
