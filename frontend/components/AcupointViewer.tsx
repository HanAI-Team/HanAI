"use client";

import { useMemo, useState, useEffect } from "react";
import { X } from "lucide-react";
import type { AcupointRecord, AcupointsFile, AcupointRegion, AcupointView } from "@/lib/acupoints";

export interface AcupointSelection {
  code: string;
  name: string;
}

type View = AcupointView;
type RegionKey = AcupointRegion;
type Side = "left" | "right";
/** 손/발처럼 좌우 구분이 있는 부위 */
type SidedRegion = "hand" | "foot";

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
  front: "/body-front.png",
  back: "/body-back.png",
};

const REGION_LABELS: Record<RegionKey, string> = {
  head: "머리",
  hand: "손",
  foot: "발",
  leg: "다리",
  back: "등",
  abdomen: "복부",
};

const SIDE_LABELS: Record<SidedRegion, Record<Side, string>> = {
  hand: { right: "오른손", left: "왼손" },
  foot: { right: "오른발", left: "왼발" },
};

function isSidedRegion(key: RegionKey): key is SidedRegion {
  return key === "hand" || key === "foot";
}

// 클릭 시 해당 부위가 존재하는 면으로 강제 전환 (등=뒷면, 복부=앞면). 나머지는 현재 탭 유지
const REGION_FORCED_VIEW: Partial<Record<RegionKey, View>> = {
  back: "back",
  abdomen: "front",
};

// 부위 확대 시 중심으로 삼을 좌표와 배율 (손/발 제외). transform은 이 중심을 뷰박스 정중앙으로 이동시키며 확대한다
const REGION_ZOOM: Record<Exclude<RegionKey, SidedRegion>, { cx: number; cy: number; scale: number }> = {
  head: { cx: 190, cy: 64, scale: 3.0 },
  leg: { cx: 190, cy: 531, scale: 1.6 },
  back: { cx: 190, cy: 265, scale: 1.6 },
  abdomen: { cx: 190, cy: 290, scale: 2.0 },
};

// 손/발은 좌우 서브탭에 따라 확대 중심이 달라진다 (한쪽 손·발만 크게 확대)
const SIDED_ZOOM: Record<SidedRegion, Record<Side, { cx: number; cy: number; scale: number }>> = {
  hand: {
    right: { cx: 314, cy: 278, scale: 2.6 },
    left: { cx: 67, cy: 278, scale: 2.6 },
  },
  foot: {
    right: { cx: 285, cy: 700, scale: 3.4 },
    left: { cx: 95, cy: 700, scale: 3.4 },
  },
};

// 361개 혈위 좌표는 public/acupoints.json에서 fetch로 불러온다 (WHO 표준 비율 기반 생성,
// 실제 취혈 위치와 정확히 일치하지 않는 시각적 참고용 근사치). 실측 데이터로 교체할 때는
// 이 파일만 같은 shape(lib/acupoints.ts의 AcupointsFile)로 바꿔치기하면 된다.

export function AcupointViewer({
  highlightedPoints = [],
  readOnly = false,
  onSelectionChange,
  className = "",
}: AcupointViewerProps) {
  const [view, setView] = useState<View>("front");
  const [region, setRegion] = useState<RegionKey | null>(null);
  const [subSide, setSubSide] = useState<Side>("right");
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

  const highlightedSet = useMemo(() => new Set(highlightedPoints), [highlightedPoints]);

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

  function handleRegionClick(key: RegionKey) {
    if (region === key) {
      setRegion(null);
      return;
    }
    setRegion(key);
    setSubSide("right");
    const forced = REGION_FORCED_VIEW[key];
    if (forced) setView(forced);
  }

  const sidedRegion = region && isSidedRegion(region) ? region : null;
  const zoom = !region
    ? { cx: VIEW_W / 2, cy: VIEW_H / 2, scale: 1 }
    : isSidedRegion(region)
      ? SIDED_ZOOM[region][subSide]
      : REGION_ZOOM[region];
  // translate는 %로 계산해 이미지의 실제 렌더링 픽셀 크기와 무관하게 동일한 확대/이동 효과를 낸다
  const txPct = ((VIEW_W / 2 - zoom.scale * zoom.cx) / VIEW_W) * 100;
  const tyPct = ((VIEW_H / 2 - zoom.scale * zoom.cy) / VIEW_H) * 100;
  const transform = `translate(${txPct}%, ${tyPct}%) scale(${zoom.scale})`;

  const visiblePoints = acupoints.filter((p) => {
    if (p.view !== view) return false;
    if (sidedRegion && p.region === sidedRegion) return p.side === subSide;
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

      <div className="flex flex-wrap gap-1.5">
        {(Object.keys(REGION_LABELS) as RegionKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => handleRegionClick(key)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              region === key
                ? "border-[#EF6600] text-[#EF6600] bg-[#EF6600]/10"
                : "border-border text-subtext hover:text-text"
            }`}
          >
            {REGION_LABELS[key]}
          </button>
        ))}
        {region && (
          <button
            type="button"
            onClick={() => setRegion(null)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-full border border-border text-subtext hover:text-text"
          >
            <X className="w-3 h-3" /> 초기화
          </button>
        )}
      </div>

      {sidedRegion && (
        <div className="flex gap-1 bg-fill border border-border rounded-md p-1 w-fit">
          {(["right", "left"] as Side[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSubSide(s)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                subSide === s ? "bg-[#EF6600] text-white" : "text-subtext hover:text-text"
              }`}
            >
              {SIDE_LABELS[sidedRegion][s]}
            </button>
          ))}
        </div>
      )}

      <div className="relative bg-bg border border-border rounded-lg overflow-hidden mx-auto w-full max-w-[460px] min-h-[500px]" style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}` }}>
        <div
          className="absolute inset-0"
          style={{ transform, transformOrigin: "0 0", transition: "transform 300ms ease-out" }}
        >
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
    .map((entry) => entry.match(/\(([^)]+)\)/)?.[1]?.trim())
    .filter((code): code is string => !!code);
}
