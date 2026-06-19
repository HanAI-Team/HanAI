"use client";
import { useEffect, useState } from "react";
import { MessageCircle, X } from "lucide-react";

const FORM_URL = "https://forms.gle/6HANKvSxdvfwKXFP9";
const DISMISS_KEY = "beta-feedback-banner-dismissed";

export default function BetaFeedbackBanner() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(localStorage.getItem(DISMISS_KEY) === "1");
  }, []);

  function dismiss() {
    setDismissed(true);
    localStorage.setItem(DISMISS_KEY, "1");
  }

  if (dismissed) return null;

  return (
    <div className="mb-3 flex items-center gap-2 bg-fill border border-border rounded-lg px-4 py-2.5">
      <MessageCircle className="w-3.5 h-3.5 text-subtext flex-shrink-0" />
      <div className="flex-1 text-xs text-subtext">
        사용해보신 소감을 들려주세요{" "}
        <a
          href={FORM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#EF6600] hover:underline font-medium"
        >
          의견 남기기
        </a>
      </div>
      <button
        onClick={dismiss}
        aria-label="닫기"
        className="text-muted hover:text-subtext flex-shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
