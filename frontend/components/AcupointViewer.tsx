"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import { X } from "lucide-react";

export interface AcupointSelection {
  code: string;
  name: string;
}

type View = "front" | "back";
type RegionKey = "head" | "hand" | "foot" | "leg" | "back" | "abdomen";
type Side = "left" | "right";
/** 손/발처럼 좌우 구분이 있는 부위 */
type SidedRegion = "hand" | "foot";

interface AcupointData {
  code: string;
  name: string;
  view: View;
  region: RegionKey;
  /** hand/foot 부위에서만 사용하는 좌우 구분 (좌/우 서브탭 필터링용) */
  side?: Side;
  x: number;
  y: number;
}

interface AcupointViewerProps {
  /** 자동 하이라이트할 혈위 코드 (진단 결과 연동용). 클릭 선택과 별개로 항상 빨간 점으로 표시됨 */
  highlightedPoints?: string[];
  /** true면 클릭으로 선택/해제할 수 없고 highlightedPoints만 보여주는 뷰어로 동작 */
  readOnly?: boolean;
  /** 선택된 혈위 목록이 바뀔 때마다 호출 (기존 침술 입력과 연동) */
  onSelectionChange?: (points: AcupointSelection[]) => void;
  className?: string;
}

// 앞면/뒷면이 동일한 인체 윤곽선을 공유하므로 viewBox도 하나로 고정해 혈위 좌표를 그대로 재사용한다
const VIEW_W = 200;
const VIEW_H = 460;

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
  head: { cx: 100, cy: 40, scale: 3.0 },
  leg: { cx: 100, cy: 330, scale: 1.6 },
  back: { cx: 100, cy: 165, scale: 1.6 },
  abdomen: { cx: 100, cy: 180, scale: 2.0 },
};

// 손/발은 좌우 서브탭에 따라 확대 중심이 달라진다 (한쪽 손·발만 크게 확대)
const SIDED_ZOOM: Record<SidedRegion, Record<Side, { cx: number; cy: number; scale: number }>> = {
  hand: {
    right: { cx: 165, cy: 173, scale: 2.6 },
    left: { cx: 35, cy: 173, scale: 2.6 },
  },
  foot: {
    right: { cx: 150, cy: 435, scale: 3.4 },
    left: { cx: 50, cy: 435, scale: 3.4 },
  },
};

// 30개 경혈의 임시 좌표 (200x460 인체 윤곽선 기준, 실제 취혈 위치와 정확히 일치하지 않음)
const ACUPOINTS: AcupointData[] = [
  { code: "LI4", name: "합곡", view: "front", region: "hand", side: "right", x: 180, y: 236 },
  { code: "ST36", name: "족삼리", view: "front", region: "leg", x: 148, y: 360 },
  { code: "BL40", name: "위중", view: "back", region: "leg", x: 140, y: 345 },
  { code: "PC6", name: "내관", view: "front", region: "hand", side: "right", x: 170, y: 190 },
  { code: "LV3", name: "태충", view: "front", region: "foot", side: "left", x: 48, y: 432 },
  { code: "GV20", name: "백회", view: "back", region: "head", x: 100, y: 10 },
  { code: "CV4", name: "관원", view: "front", region: "abdomen", x: 100, y: 222 },
  { code: "CV12", name: "중완", view: "front", region: "abdomen", x: 100, y: 172 },
  { code: "SP6", name: "삼음교", view: "front", region: "leg", x: 60, y: 400 },
  { code: "HT7", name: "신문", view: "front", region: "hand", side: "left", x: 18, y: 236 },
  { code: "LU9", name: "태연", view: "front", region: "hand", side: "right", x: 184, y: 230 },
  { code: "LI11", name: "곡지", view: "front", region: "hand", side: "right", x: 178, y: 168 },
  { code: "ST25", name: "천추", view: "front", region: "abdomen", x: 118, y: 195 },
  { code: "SP9", name: "음릉천", view: "front", region: "leg", x: 62, y: 360 },
  { code: "HT3", name: "소해", view: "front", region: "hand", side: "left", x: 27, y: 168 },
  { code: "SI3", name: "후계", view: "back", region: "hand", side: "right", x: 182, y: 236 },
  { code: "BL23", name: "신유", view: "back", region: "back", x: 120, y: 200 },
  { code: "BL60", name: "곤륜", view: "back", region: "foot", side: "right", x: 152, y: 420 },
  { code: "KI3", name: "태계", view: "front", region: "foot", side: "left", x: 60, y: 420 },
  { code: "PC3", name: "곡택", view: "front", region: "hand", side: "right", x: 173, y: 168 },
  { code: "TE5", name: "외관", view: "back", region: "hand", side: "left", x: 19, y: 190 },
  { code: "GB34", name: "양릉천", view: "back", region: "leg", x: 150, y: 362 },
  { code: "GB20", name: "풍지", view: "back", region: "head", x: 112, y: 76 },
  { code: "LV2", name: "행간", view: "front", region: "foot", side: "right", x: 152, y: 432 },
  { code: "LI20", name: "영향", view: "front", region: "head", x: 110, y: 58 },
  { code: "ST6", name: "협거", view: "front", region: "head", x: 116, y: 64 },
  { code: "GV14", name: "대추", view: "back", region: "back", x: 100, y: 88 },
  { code: "CV17", name: "전중", view: "front", region: "abdomen", x: 100, y: 135 },
  { code: "SP10", name: "혈해", view: "front", region: "leg", x: 72, y: 280 },
  { code: "BL57", name: "승산", view: "back", region: "leg", x: 144, y: 392 },
];

// 인체 윤곽선은 public/body-front.svg, public/body-back.svg 파일로 분리되어 있다.
// fetch로 SVG 텍스트를 가져와 DOM에 인라인 삽입하므로, 파일 안의 var(--color-border-strong)이
// 호스트 페이지의 다크모드 토글에 그대로 반응한다. 파일만 교체해도 혈위 좌표(ACUPOINTS)와 기능은 유지된다.
const VIEW_SVG_URL: Record<View, string> = {
  front: "/body-front.svg",
  back: "/body-back.svg",
};

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
  const [svgHtml, setSvgHtml] = useState("");
  const svgCacheRef = useRef<Partial<Record<View, string>>>({});

  const highlightedSet = useMemo(() => new Set(highlightedPoints), [highlightedPoints]);

  useEffect(() => {
    const cached = svgCacheRef.current[view];
    if (cached) {
      setSvgHtml(cached);
      return;
    }
    let cancelled = false;
    fetch(VIEW_SVG_URL[view])
      .then((res) => res.text())
      .then((text) => {
        svgCacheRef.current[view] = text;
        if (!cancelled) setSvgHtml(text);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [view]);

  useEffect(() => {
    if (!onSelectionChange) return;
    onSelectionChange(
      ACUPOINTS.filter((p) => selected.has(p.code)).map((p) => ({ code: p.code, name: p.name })),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  function togglePoint(point: AcupointData) {
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
    ? { cx: 100, cy: VIEW_H / 2, scale: 1 }
    : isSidedRegion(region)
      ? SIDED_ZOOM[region][subSide]
      : REGION_ZOOM[region];
  // translate는 %로 계산해 이미지의 실제 렌더링 픽셀 크기와 무관하게 동일한 확대/이동 효과를 낸다
  const txPct = ((VIEW_W / 2 - zoom.scale * zoom.cx) / VIEW_W) * 100;
  const tyPct = ((VIEW_H / 2 - zoom.scale * zoom.cy) / VIEW_H) * 100;
  const transform = `translate(${txPct}%, ${tyPct}%) scale(${zoom.scale})`;

  const visiblePoints = ACUPOINTS.filter((p) => {
    if (p.view !== view) return false;
    if (sidedRegion && p.region === sidedRegion) return p.side === subSide;
    return true;
  });
  const selectedPoints = ACUPOINTS.filter((p) => selected.has(p.code));

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

      <div className="relative bg-bg border border-border rounded-lg overflow-hidden mx-auto w-full max-w-[240px]" style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}` }}>
        <div
          className="absolute inset-0"
          style={{ transform, transformOrigin: "0 0", transition: "transform 300ms ease-out" }}
        >
          <div
            role="img"
            aria-label={view === "front" ? "인체 앞면" : "인체 뒷면"}
            className="absolute inset-0 pointer-events-none select-none [&>svg]:w-full [&>svg]:h-full [&>svg]:block"
            dangerouslySetInnerHTML={{ __html: svgHtml }}
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
                style={{ left: `${(p.x / VIEW_W) * 100}%`, top: `${(p.y / VIEW_H) * 100}%` }}
              >
                <div
                  className={`relative -translate-x-1/2 -translate-y-1/2 p-1.5 -m-1.5 ${readOnly ? "" : "cursor-pointer"}`}
                  onMouseEnter={() => setHovered(p.code)}
                  onMouseLeave={() => setHovered((h) => (h === p.code ? null : h))}
                  onClick={() => togglePoint(p)}
                >
                  <span
                    className="block rounded-full border border-white"
                    style={{
                      width: isActive ? 9 : 6,
                      height: isActive ? 9 : 6,
                      backgroundColor: isActive ? "#DC2626" : "var(--color-muted)",
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
