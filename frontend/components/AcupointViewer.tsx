"use client";

import { useMemo, useState, useEffect } from "react";
import { X } from "lucide-react";
import type { AcupointRecord, AcupointsFile, AcupointView } from "@/lib/acupoints";

export interface AcupointSelection {
  code: string;
  name: string;
}

type View = AcupointView;

interface AcupointViewerProps {
  /** 자동 하이라이트할 혈위 코드 (진단 결과 연동용). 클릭 선택과 별개로 항상 빨간 점+pulse로 표시됨 */
  highlightedPoints?: string[];
  /** true면 클릭으로 선택/해제할 수 없고 highlightedPoints만 보여주는 뷰어로 동작 */
  readOnly?: boolean;
  /** 선택된 혈위 목록이 바뀔 때마다 호출 (기존 침술 입력과 연동) */
  onSelectionChange?: (points: AcupointSelection[]) => void;
  className?: string;
}

// 앞면/뒷면 모두 public/body-front.png, public/body-back.png의 실제 크기(380x740)를 좌표계로 사용
const VIEW_W = 380;
const VIEW_H = 740;

const VIEW_IMAGE_URL: Record<View, string> = {
  front: "/front.svg",
  back: "/back.svg",
};

// 361개 혈위 좌표는 public/acupoints.json에서 fetch로 불러온다 (WHO 표준 비율 기반 생성,
// 실제 취혈 위치와 정확히 일치하지 않는 시각적 참고용 근사치). 실측 데이터로 교체할 때는
// 이 파일만 같은 shape(lib/acupoints.ts의 AcupointsFile)로 바꿔치기하면 된다.

// AI 진단 결과의 point_code 표기 관례(LV=간경, REN=임맥)를 acupoints.json 코드 체계로 변환
const CODE_PREFIX_ALIASES: Record<string, string> = {
  LV: "LR",
  REN: "CV",
};

// 한자 혈명 -> acupoints.json 한글명. 兪/俞처럼 뜻이 같은 이체자는 NFC로 통일되지 않으므로 각각 등록
const HANJA_NAME_ALIASES: Record<string, string> = {
  "三陰交": "삼음교",
  "合谷": "합곡",
  "足三里": "족삼리",
  "氣海": "기해",
  "關元": "관원",
  "命門": "명문",
  "太溪": "태계",
  "曲池": "곡지",
  "內關": "내관",
  "太衝": "태충",
  "中渚": "중저",
  "翳風": "예풍",
  "風池": "풍지",
  "陽陵泉": "양릉천",
  "委中": "위중",
  "腎俞": "신유",
  "腎兪": "신유",
  "膀胱俞": "방광유",
  "陰陵泉": "음릉천",
  "氣海俞": "기해유",
  "崑崙": "곤륜",
  "孔最": "공최",
  "百會": "백회",
  "中脘": "중완",
  "陽池": "양지",
  "外關": "외관",
  "地倉": "지창",
  "頰車": "협거",
  "人中": "인중",
  "陰谷": "음곡",
};

// 한글 이표기(背兪穴의 유/수 혼용 등) -> acupoints.json 정식 한글명
const HANGUL_NAME_ALIASES: Record<string, string> = {
  "비수": "비유",
  "위수": "위유",
  "신수": "신유",
  "격수": "격유",
  "견외수": "견외유",
};

const SUFFIX_STRIP_RE = /[穴혈]$/;

/**
 * highlightedPoints 원문 하나를 acupoints.json의 code로 정규화한다.
 * 순서: (a) code 완전일치 -> (b) 한글명 완전일치 -> (c) 별칭 테이블(한자/한글 이표기)
 * -> (d) 접두어 별칭(LV/REN) -> (e) 접미사(穴/혈) 제거 후 재시도.
 * (e)는 (a)~(d)가 모두 실패한 뒤에만 실행되어 "氣海俞"가 "氣海"로 오인되는 것을 막는다.
 * 최종 실패 시 null을 반환하며, 호출부에서 console.warn으로 원문을 남긴다.
 */
function resolveAcupointCode(
  rawInput: string,
  codeSet: Set<string>,
  nameToCode: Map<string, string>,
): string | null {
  const raw = rawInput.normalize("NFC").trim();

  if (codeSet.has(raw)) return raw;
  if (nameToCode.has(raw)) return nameToCode.get(raw)!;

  const aliasName = HANJA_NAME_ALIASES[raw] ?? HANGUL_NAME_ALIASES[raw];
  if (aliasName && nameToCode.has(aliasName)) return nameToCode.get(aliasName)!;

  const prefixMatch = raw.match(/^([A-Za-z]+)(\d+)$/);
  if (prefixMatch) {
    const aliasPrefix = CODE_PREFIX_ALIASES[prefixMatch[1].toUpperCase()];
    if (aliasPrefix) {
      const aliasCode = `${aliasPrefix}${prefixMatch[2]}`;
      if (codeSet.has(aliasCode)) return aliasCode;
    }
  }

  if (SUFFIX_STRIP_RE.test(raw)) {
    const stripped = raw.replace(SUFFIX_STRIP_RE, "");
    if (stripped && stripped !== raw) {
      return resolveAcupointCode(stripped, codeSet, nameToCode);
    }
  }

  return null;
}

export function AcupointViewer({
  highlightedPoints = [],
  readOnly = false,
  onSelectionChange,
  className = "",
}: AcupointViewerProps) {
  const [view, setView] = useState<View>("front");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hovered, setHovered] = useState<string | null>(null);
  const [acupointsFile, setAcupointsFile] = useState<AcupointsFile | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/acupoints.json")
      .then((res) => res.json())
      .then((data: AcupointsFile) => {
        if (!cancelled) setAcupointsFile(data);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const acupoints = acupointsFile?.points ?? [];
  const viewBoxW = acupointsFile?.viewBox.width ?? VIEW_W;
  const viewBoxH = acupointsFile?.viewBox.height ?? VIEW_H;

  const codeSet = useMemo(() => new Set(acupoints.map((p) => p.code)), [acupoints]);
  const nameToCode = useMemo(() => {
    // acupoints.json에는 같은 한글명을 쓰는 서로 다른 혈이 있다(예: 견정=SI9/GB21).
    // 이런 이름은 임의로 하나를 고르지 않고 매핑에서 제외해 미해결(null)로 남긴다.
    const map = new Map<string, string>();
    const ambiguous = new Set<string>();
    for (const p of acupoints) {
      if (ambiguous.has(p.name)) continue;
      if (map.has(p.name)) {
        map.delete(p.name);
        ambiguous.add(p.name);
        continue;
      }
      map.set(p.name, p.code);
    }
    return map;
  }, [acupoints]);

  const highlightedSet = useMemo(() => {
    const resolved = new Set<string>();
    for (const raw of highlightedPoints) {
      const code = resolveAcupointCode(raw, codeSet, nameToCode);
      if (code) {
        resolved.add(code);
      } else {
        console.warn(`[AcupointViewer] 혈위 코드 매칭 실패: "${raw}"`);
      }
    }
    return resolved;
  }, [highlightedPoints, codeSet, nameToCode]);

  useEffect(() => {
    if (!onSelectionChange) return;
    onSelectionChange(
      acupoints.filter((p) => selected.has(p.code)).map((p) => ({ code: p.code, name: p.name })),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, acupointsFile]);

  function togglePoint(point: AcupointRecord) {
    if (readOnly) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(point.code)) next.delete(point.code);
      else next.add(point.code);
      return next;
    });
  }

  const visiblePoints = acupoints.filter((p) => {
    if (p.view !== view) return false;
    if (readOnly) return highlightedSet.has(p.code);
    return true;
  });
  const selectedPoints = acupoints.filter((p) => selected.has(p.code));

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex gap-1 bg-fill border border-border rounded-md p-1 w-fit">
        {(["front", "back"] as View[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              view === v ? "bg-[#EF6600] text-white" : "text-subtext hover:text-text"
            }`}
          >
            {v === "front" ? "앞면" : "뒷면"}
          </button>
        ))}
      </div>

      <div className="relative bg-bg border border-border rounded-lg overflow-hidden mx-auto w-full max-w-[460px] min-h-[500px]" style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}` }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={VIEW_IMAGE_URL[view]}
          alt={view === "front" ? "인체 앞면" : "인체 뒷면"}
          draggable={false}
          className="absolute inset-0 w-full h-full object-contain pointer-events-none select-none dark:[filter:invert(0.85)]"
        />
        {visiblePoints.map((p) => {
          const isSelected = selected.has(p.code);
          const isHighlighted = highlightedSet.has(p.code);
          const isActive = isSelected || isHighlighted;
          const showLabel = isActive || hovered === p.code;
          const label = `${p.name}(${p.code})`;
          return (
            <div
              key={p.code}
              className="absolute"
              style={{ left: `${(p.x / viewBoxW) * 100}%`, top: `${(p.y / viewBoxH) * 100}%` }}
            >
              <div
                className={`relative -translate-x-1/2 -translate-y-1/2 p-1.5 -m-1.5 ${readOnly ? "" : "cursor-pointer"}`}
                onMouseEnter={() => setHovered(p.code)}
                onMouseLeave={() => setHovered((h) => (h === p.code ? null : h))}
                onClick={() => togglePoint(p)}
              >
                <span
                  className={`block rounded-full border border-white ${isHighlighted ? "animate-pulse" : ""}`}
                  style={{
                    width: isActive ? 11 : 5,
                    height: isActive ? 11 : 5,
                    backgroundColor: isActive ? "#DC2626" : "var(--color-muted)",
                    opacity: isActive ? 1 : 0.5,
                  }}
                />
                {showLabel && (
                  <span className="absolute left-1/2 bottom-full mb-1 -translate-x-1/2 whitespace-nowrap rounded bg-[#1f2937] px-1.5 py-0.5 text-[9px] text-white opacity-95">
                    {label}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!readOnly && (
        <div className="flex flex-wrap gap-1.5">
          {selectedPoints.length === 0 ? (
            <span className="text-xs text-muted">선택된 혈위 없음</span>
          ) : (
            selectedPoints.map((p) => (
              <span
                key={p.code}
                className="inline-flex items-center gap-1 bg-fill border border-border rounded px-2 py-0.5 text-xs text-text"
              >
                {p.name}({p.code})
                <button type="button" onClick={() => togglePoint(p)}>
                  <X className="w-3 h-3 text-subtext hover:text-text" />
                </button>
              </span>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/** "합곡(LI4)" 형태의 침 처방 문자열 목록에서 혈위 코드만 추출 (진단 결과 자동 하이라이트 연동용) */
export function parseAcupointCodes(entries: string[]): string[] {
  return entries
    .map((entry) => entry.match(/\(([^)]+)\)/)?.[1]?.normalize("NFC").trim())
    .filter((code): code is string => !!code);
}
