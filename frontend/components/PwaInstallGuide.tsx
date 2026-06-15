"use client";
import { useEffect, useRef, useState } from "react";

type Platform = "ios" | "android" | null;

function detectPlatform(): Platform {
  const ua = navigator.userAgent;
  if (/iphone|ipad|ipod/i.test(ua)) return "ios";
  if (/android/i.test(ua)) return "android";
  return null;
}

function isInstalled(): boolean {
  return (
    ("standalone" in navigator && (navigator as { standalone?: boolean }).standalone === true) ||
    window.matchMedia("(display-mode: standalone)").matches
  );
}

export default function PwaInstallGuide() {
  const [show, setShow] = useState(false);
  const [platform, setPlatform] = useState<Platform>(null);
  const deferredPrompt = useRef<Event & { prompt: () => void; userChoice: Promise<{ outcome: string }> } | null>(null);

  useEffect(() => {
    if (isInstalled()) return;
    if (localStorage.getItem("pwa-dismissed")) return;

    const p = detectPlatform();
    setPlatform(p);

    if (p === "android") {
      const handler = (e: Event) => {
        e.preventDefault();
        deferredPrompt.current = e as typeof deferredPrompt.current;
        setShow(true);
      };
      window.addEventListener("beforeinstallprompt", handler);
      return () => window.removeEventListener("beforeinstallprompt", handler);
    }

    if (p === "ios") setShow(true);
  }, []);

  function dismiss() {
    setShow(false);
    localStorage.setItem("pwa-dismissed", "1");
  }

  async function handleAndroidInstall() {
    if (!deferredPrompt.current) return;
    deferredPrompt.current.prompt();
    await deferredPrompt.current.userChoice;
    dismiss();
  }

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-[200] flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-sm relative">
        <button
          onClick={dismiss}
          className="absolute top-4 right-4 text-gray-400 text-lg leading-none"
          aria-label="닫기"
        >
          ✕
        </button>

        {platform === "ios" ? (
          <>
            <div className="text-[11px] font-semibold text-[#EF6600] uppercase tracking-wide mb-1">
              iOS 설치 방법
            </div>
            <h2 className="text-xl font-bold text-[#232323] mb-5">
              사파리에서 홈 화면에 추가
            </h2>
            <div className="flex flex-col gap-3 mb-5">
              {[
                {
                  n: 1,
                  title: "하단 공유 버튼을 누르세요",
                  desc: "사파리 주소창 옆 또는 화면 하단의 공유 아이콘",
                },
                {
                  n: 2,
                  title: "'홈 화면에 추가' 선택",
                  desc: "목록을 아래로 내리면 보입니다.",
                },
                { n: 3, title: "우측 상단 '추가' 탭", desc: "" },
              ].map((s) => (
                <div
                  key={s.n}
                  className="flex items-start gap-3 bg-gray-50 rounded-xl p-3"
                >
                  <div className="w-7 h-7 rounded-full bg-[#232323] text-white text-xs flex items-center justify-center flex-shrink-0">
                    {s.n}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-[#232323]">
                      {s.title}
                    </div>
                    {s.desc && (
                      <div className="text-xs text-gray-500 mt-0.5">{s.desc}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400">
              ※ 사파리에서만 가능합니다. 다른 브라우저에서는 사파리로 다시
              열어주세요.
            </p>
          </>
        ) : (
          <>
            <div className="text-[11px] font-semibold text-[#EF6600] uppercase tracking-wide mb-1">
              Android 설치 방법
            </div>
            <h2 className="text-xl font-bold text-[#232323] mb-2">
              홈 화면에 앱 추가
            </h2>
            <p className="text-sm text-gray-500 mb-5">
              Zinmac을 홈 화면에 추가하면 앱처럼 빠르게 실행할 수 있습니다.
            </p>
            <button
              onClick={handleAndroidInstall}
              className="w-full bg-[#EF6600] text-white rounded-xl py-3 text-sm font-medium mb-3"
            >
              홈 화면에 추가
            </button>
          </>
        )}
      </div>
    </div>
  );
}
