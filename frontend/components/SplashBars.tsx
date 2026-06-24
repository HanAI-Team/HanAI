"use client";

import type { CSSProperties } from "react";

// 로고를 이루는 7개 막대의 x좌표 구간 (원본 500x500 PNG 기준 %)
// 순서: 왼쪽 짧은 막대 → 왼쪽 긴 막대 → M 왼쪽 → M 가운데 → M 오른쪽 → 오른쪽 긴 막대 → 오른쪽 짧은 막대
const BAR_CLIPS = [
  { left: 15, right: 79.2 },
  { left: 26.2, right: 66.8 },
  { left: 38.2, right: 54 },
  { left: 46, right: 46.2 },
  { left: 53.8, right: 38.4 },
  { left: 66.6, right: 26.4 },
  { left: 78.8, right: 15.4 },
];

export default function SplashBars({
  visible,
  className = "",
}: {
  visible: boolean;
  className?: string;
}) {
  return (
    <div
      role="img"
      aria-label="Zinmac"
      className={`relative ${className}`}
    >
      {BAR_CLIPS.map((clip, i) => {
        const style: CSSProperties = {
          clipPath: `inset(0 ${clip.right}% 0 ${clip.left}%)`,
          opacity: visible ? 1 : 0,
          transform: visible ? "translateY(0)" : "translateY(36px)",
          transition: "transform 0.4s ease-out, opacity 0.4s ease-out",
          transitionDelay: `${i * 100}ms`,
        };
        return (
          <div key={i}>
            <img
              src="/images/logo-light.png"
              alt=""
              className="absolute inset-0 w-full h-full object-contain dark:hidden"
              style={style}
            />
            <img
              src="/images/logo-dark.png"
              alt=""
              className="absolute inset-0 w-full h-full object-contain hidden dark:block"
              style={style}
            />
          </div>
        );
      })}
    </div>
  );
}
