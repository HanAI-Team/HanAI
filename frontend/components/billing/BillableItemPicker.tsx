"use client";

import { useEffect, useState } from "react";
import { getBillableCatalog, submitLineItems } from "@/lib/api/billing";
import type { BillableItem, ClaimSummary, SelectedBillableItem } from "@/types/billing";

interface BillableItemPickerProps {
  medicalRecordId: string;
  onConfirmed?: (claim: ClaimSummary) => void;
  onRequestAiSuggestion?: () => Promise<string[]>;
}

export function BillableItemPicker({
  medicalRecordId,
  onConfirmed,
  onRequestAiSuggestion,
}: BillableItemPickerProps) {
  const [catalog, setCatalog] = useState<BillableItem[]>([]);
  const [selected, setSelected] = useState<Map<string, string[]>>(new Map());
  const [submitting, setSubmitting] = useState(false);
  const [confirmedClaim, setConfirmedClaim] = useState<ClaimSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBillableCatalog()
      .then(setCatalog)
      .catch(() => setError("항목을 불러오지 못했습니다"));
  }, []);

  function toggleItem(item: BillableItem) {
    setSelected((prev) => {
      const next = new Map(prev);
      next.has(item.id) ? next.delete(item.id) : next.set(item.id, []);
      return next;
    });
  }

  function setHyeolmyeong(itemId: string, raw: string) {
    const names = raw.split(",").map((s) => s.trim()).filter(Boolean);
    setSelected((prev) => {
      const next = new Map(prev);
      next.set(itemId, names);
      return next;
    });
  }

  async function handleAiSuggest() {
    if (!onRequestAiSuggestion) return;
    const suggestedIds = await onRequestAiSuggestion();
    setSelected((prev) => {
      const next = new Map(prev);
      suggestedIds.forEach((id) => { if (!next.has(id)) next.set(id, []); });
      return next;
    });
  }

  async function handleConfirm() {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: SelectedBillableItem[] = Array.from(selected.entries()).map(
        ([itemId, hyeolmyeongNames]) => ({ itemId, hyeolmyeongNames })
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
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-subtext">청구 가능 항목 (클릭해서 선택)</span>
        {onRequestAiSuggestion && (
          <button
            onClick={handleAiSuggest}
            className="rounded-md border border-[#EF6600] px-2.5 py-1 text-xs font-medium text-[#EF6600] hover:bg-[#FAEEDA]"
          >
            AI 추천으로 선택
          </button>
        )}
      </div>

      {error && <p className="mb-2 text-xs text-red-500">{error}</p>}

      <div className="grid grid-cols-2 gap-2">
        {catalog.map((item) => {
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
                <div className={`text-sm font-medium ${isSelected ? "text-[#EF6600]" : "text-text"}`}>
                  {item.name}
                </div>
                {item.sub && (
                  <div className={`text-xs ${isSelected ? "text-[#EF6600]/70" : "text-subtext"}`}>
                    {item.sub}
                  </div>
                )}
              </button>

              {isSelected && item.requiresHyeolmyeong && (
                <input
                  type="text"
                  placeholder="경혈명 입력 (예: 내관, 삼음교)"
                  onChange={(e) => setHyeolmyeong(item.id, e.target.value)}
                  className="mt-1 w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-text"
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
        <span className="text-sm text-subtext">선택된 항목 {selected.size}건</span>
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
