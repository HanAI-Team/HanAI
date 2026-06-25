"use client";

import { useEffect, useMemo, useState } from "react";
import { getBillableCatalog, submitLineItems } from "@/lib/api/billing";
import type { BillableItem, ClaimSummary, SelectedBillableItem } from "@/types/billing";

interface BillableItemPickerProps {
  medicalRecordId: string;
  onConfirmed?: (claim: ClaimSummary) => void;
}

const CATEGORY_ORDER = ["진찰료", "침술", "뜸", "부항", "전기/온열", "추나/도수", "검사", "한약", "비급여"];

export function BillableItemPicker({ medicalRecordId, onConfirmed }: BillableItemPickerProps) {
  const [catalog, setCatalog] = useState<BillableItem[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("진찰료");
  const [selected, setSelected] = useState<Map<string, { item: BillableItem; hyeolmyeong: string[] }>>(new Map());
  const [submitting, setSubmitting] = useState(false);
  const [confirmedClaim, setConfirmedClaim] = useState<ClaimSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBillableCatalog()
      .then(setCatalog)
      .catch(() => setError("항목을 불러오지 못했습니다"));
  }, []);

  const categories = useMemo(() => {
    const present = new Set(catalog.map((i) => i.category));
    return CATEGORY_ORDER.filter((c) => present.has(c));
  }, [catalog]);

  const visibleItems = useMemo(
    () => catalog.filter((i) => i.category === activeCategory),
    [catalog, activeCategory]
  );

  const totalAmount = useMemo(
    () => Array.from(selected.values()).reduce((sum, { item }) => sum + item.unitPrice, 0),
    [selected]
  );

  function toggleItem(item: BillableItem) {
    setSelected((prev) => {
      const next = new Map(prev);
      next.has(item.id) ? next.delete(item.id) : next.set(item.id, { item, hyeolmyeong: [] });
      return next;
    });
  }

  function setHyeolmyeong(itemId: string, raw: string) {
    setSelected((prev) => {
      const entry = prev.get(itemId);
      if (!entry) return prev;
      const next = new Map(prev);
      next.set(itemId, { ...entry, hyeolmyeong: raw.split(",").map((s) => s.trim()).filter(Boolean) });
      return next;
    });
  }

  async function handleConfirm() {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: SelectedBillableItem[] = Array.from(selected.entries()).map(
        ([itemId, { hyeolmyeong }]) => ({ itemId, hyeolmyeongNames: hyeolmyeong })
      );
      const claim = await submitLineItems(medicalRecordId, payload);
      setConfirmedClaim(claim);
      onConfirmed?.(claim);
    } catch {
      setError("청구 처리에 실패했습니다. 다시 시도해주세요");
    } finally {
      setSubmitting(false);
    }
  }

  if (confirmedClaim) {
    return (
      <div className="rounded-lg border border-border bg-card p-5 text-center">
        <p className="text-sm font-medium text-text">
          {confirmedClaim.lineItems.length}건 청구 완료 —{" "}
          {confirmedClaim.status === "draft" ? "작성중 상태로 저장됨" : confirmedClaim.status}
        </p>
        <p className="mt-1 text-xs text-subtext">
          {confirmedClaim.billingMonth} 명세서에 누적 · 합계{" "}
          {confirmedClaim.totalAmount.toLocaleString()}원
        </p>
        <button
          onClick={() => { setConfirmedClaim(null); setSelected(new Map()); }}
          className="mt-3 rounded-md border border-border px-3 py-1.5 text-xs text-subtext hover:text-text"
        >
          새 항목 추가
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* 카테고리 탭 */}
      <div className="flex flex-wrap gap-1">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeCategory === cat
                ? "bg-[#EF6600] text-white"
                : "bg-card border border-border text-subtext hover:text-text"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 항목 그리드 */}
      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="grid grid-cols-2 gap-2">
        {visibleItems.map((item) => {
          const isSelected = selected.has(item.id);
          return (
            <div key={item.id}>
              <button
                onClick={() => toggleItem(item)}
                className={`w-full rounded-md border p-2.5 text-left transition-colors ${
                  isSelected
                    ? "border-[#EF6600] bg-[#EF6600]/10"
                    : "border-border bg-card hover:border-text/30"
                }`}
              >
                <div className={`text-xs font-medium leading-snug ${isSelected ? "text-[#EF6600]" : "text-text"}`}>
                  {item.name}
                </div>
                <div className="mt-0.5 flex items-center justify-between">
                  {item.sub ? (
                    <span className={`text-[10px] ${isSelected ? "text-[#EF6600]/70" : "text-subtext"}`}>
                      {item.sub}
                    </span>
                  ) : (
                    <span />
                  )}
                  <span className={`text-[10px] font-semibold tabular-nums ${
                    item.isInsured ? (isSelected ? "text-[#EF6600]" : "text-text/70") : "text-subtext"
                  }`}>
                    {item.unitPrice > 0 ? `${item.unitPrice.toLocaleString()}원` : "자율"}
                  </span>
                </div>
              </button>

              {isSelected && item.requiresHyeolmyeong && (
                <input
                  type="text"
                  placeholder="경혈명 (예: 내관, 삼음교)"
                  onChange={(e) => setHyeolmyeong(item.id, e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-text placeholder:text-subtext/60"
                />
              )}
            </div>
          );
        })}
      </div>

      {/* 선택된 항목 요약 + 제출 */}
      {selected.size > 0 && (
        <div className="rounded-md border border-border bg-card/50 p-3">
          <p className="mb-1.5 text-[10px] font-medium text-subtext uppercase tracking-wide">선택된 항목</p>
          <div className="flex flex-col gap-1">
            {Array.from(selected.values()).map(({ item }) => (
              <div key={item.id} className="flex items-center justify-between text-xs">
                <span className="text-text truncate pr-2">{item.name}</span>
                <span className="shrink-0 tabular-nums text-subtext">
                  {item.unitPrice > 0 ? `${item.unitPrice.toLocaleString()}원` : "자율"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2 border-t border-border pt-2 flex items-center justify-between">
            <span className="text-xs text-subtext">합계 (급여기준)</span>
            <span className="text-sm font-semibold text-text tabular-nums">{totalAmount.toLocaleString()}원</span>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border pt-3">
        <span className="text-xs text-subtext">{selected.size}건 선택</span>
        <button
          onClick={handleConfirm}
          disabled={selected.size === 0 || submitting}
          className="rounded-md bg-[#232323] px-4 py-2 text-sm font-medium text-white disabled:opacity-40 hover:bg-black transition-colors"
        >
          {submitting ? "처리 중..." : "청구하겠습니까?"}
        </button>
      </div>
    </div>
  );
}
