"use client";

import { useEffect, useMemo, useState } from "react";
import {
  type AcupuncturePointSearchResult,
  getBillableCatalog,
  searchAcupuncturePoints,
  submitLineItems,
  updateClaimSupportFund,
} from "@/lib/api/billing";
import type { BillableItem, ClaimSummary, SelectedBillableItem } from "@/types/billing";

interface BillableItemPickerProps {
  medicalRecordId: string;
  visitType?: "외래" | "입원";
  onConfirmed?: (claim: ClaimSummary) => void;
}

const CATEGORY_ORDER = ["진찰료", "침술", "뜸", "부항", "전기/온열", "추나", "검사", "한약", "비급여"];

type SelectedAcupoint = { code: string; koreanName: string };
type SelectedEntry = { item: BillableItem; acupoints: SelectedAcupoint[]; isNonBenefit: boolean };

function AcupointPicker({
  selected,
  onAdd,
  onRemove,
}: {
  selected: SelectedAcupoint[];
  onAdd: (point: AcupuncturePointSearchResult) => void;
  onRemove: (code: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AcupuncturePointSearchResult[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchAcupuncturePoints(query)
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const selectedCodes = new Set(selected.map((s) => s.code));

  return (
    <div className="mt-1">
      {selected.length > 0 && (
        <div className="mb-1 flex flex-wrap gap-1">
          {selected.map((a) => (
            <span
              key={a.code}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-[10px] text-text"
            >
              {a.koreanName}
              <button
                type="button"
                onClick={() => onRemove(a.code)}
                className="text-subtext hover:text-text"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="경혈명 검색 (예: 내관, 삼음교)"
          className="w-full rounded-md border border-border bg-card px-2 py-1 text-xs text-text placeholder:text-subtext/60"
        />
        {open && results.length > 0 && (
          <div className="absolute z-10 mt-1 w-full max-h-40 overflow-y-auto rounded-md border border-border bg-card">
            {results.map((r) => (
              <button
                key={r.code}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  if (!selectedCodes.has(r.code)) onAdd(r);
                  setQuery("");
                  setResults([]);
                }}
                disabled={selectedCodes.has(r.code)}
                className="block w-full px-2 py-1 text-left text-xs text-text hover:bg-border/40 disabled:opacity-40"
              >
                {r.korean_name} <span className="text-[10px] text-subtext">({r.code})</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function BillableItemPicker({ medicalRecordId, visitType = "외래", onConfirmed }: BillableItemPickerProps) {
  const [catalog, setCatalog] = useState<BillableItem[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("진찰료");
  const [selected, setSelected] = useState<Map<string, SelectedEntry>>(new Map());
  const [submitting, setSubmitting] = useState(false);
  const [confirmedClaim, setConfirmedClaim] = useState<ClaimSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [supportFundInput, setSupportFundInput] = useState("");
  const [savingFund, setSavingFund] = useState(false);

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

  const nonBenefitTotal = useMemo(
    () => Array.from(selected.values())
      .filter(({ isNonBenefit }) => isNonBenefit)
      .reduce((sum, { item }) => sum + item.unitPrice, 0),
    [selected]
  );

  function toggleItem(item: BillableItem) {
    setSelected((prev) => {
      const next = new Map(prev);
      next.has(item.id)
        ? next.delete(item.id)
        : next.set(item.id, { item, acupoints: [], isNonBenefit: !item.isInsured });
      return next;
    });
  }

  function addAcupoint(itemId: string, point: AcupuncturePointSearchResult) {
    setSelected((prev) => {
      const entry = prev.get(itemId);
      if (!entry) return prev;
      const next = new Map(prev);
      next.set(itemId, {
        ...entry,
        acupoints: [...entry.acupoints, { code: point.code, koreanName: point.korean_name }],
      });
      return next;
    });
  }

  function removeAcupoint(itemId: string, code: string) {
    setSelected((prev) => {
      const entry = prev.get(itemId);
      if (!entry) return prev;
      const next = new Map(prev);
      next.set(itemId, { ...entry, acupoints: entry.acupoints.filter((a) => a.code !== code) });
      return next;
    });
  }

  function toggleNonBenefit(itemId: string) {
    setSelected((prev) => {
      const entry = prev.get(itemId);
      if (!entry) return prev;
      const next = new Map(prev);
      next.set(itemId, { ...entry, isNonBenefit: !entry.isNonBenefit });
      return next;
    });
  }

  async function handleConfirm() {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: SelectedBillableItem[] = Array.from(selected.entries()).map(
        ([itemId, entry]) => ({ itemId, acupointCodes: entry.acupoints.map((a) => a.code), isNonBenefit: entry.isNonBenefit })
      );
      const claim = await submitLineItems(medicalRecordId, payload, visitType);
      setConfirmedClaim(claim);
      onConfirmed?.(claim);
    } catch {
      setError("청구 처리에 실패했습니다. 다시 시도해주세요");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveSupportFund() {
    if (!confirmedClaim) return;
    const val = parseInt(supportFundInput.replace(/,/g, ""), 10);
    if (isNaN(val) || val < 0) return;
    setSavingFund(true);
    try {
      const updated = await updateClaimSupportFund(confirmedClaim.id, val);
      setConfirmedClaim(updated);
    } catch {
      setError("지원금 저장에 실패했습니다.");
    } finally {
      setSavingFund(false);
    }
  }

  if (confirmedClaim) {
    return (
      <div className="rounded-lg border border-border bg-card p-5">
        <p className="text-sm font-medium text-text">
          {confirmedClaim.lineItems.length}건 청구 완료 —{" "}
          {confirmedClaim.status === "draft" ? "작성중 상태로 저장됨" : confirmedClaim.status}
        </p>
        <p className="mt-1 text-xs text-subtext">
          {confirmedClaim.billingMonth} 명세서에 누적 · 합계{" "}
          {confirmedClaim.totalAmount.toLocaleString()}원
        </p>

        {/* 지원금 입력 */}
        <div className="mt-4 border-t border-border pt-4">
          <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
            지원금 (본인부담 경감액)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={supportFundInput}
              onChange={(e) => setSupportFundInput(e.target.value.replace(/[^0-9]/g, ""))}
              placeholder="0"
              className="flex-1 border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600]"
            />
            <button
              onClick={handleSaveSupportFund}
              disabled={savingFund || !supportFundInput}
              className="rounded-md bg-[#EF6600] px-3 py-2 text-xs font-medium text-white disabled:opacity-40 hover:opacity-90"
            >
              {savingFund ? "저장 중..." : "저장"}
            </button>
          </div>
          {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
        </div>

        <button
          onClick={() => { setConfirmedClaim(null); setSelected(new Map()); setSupportFundInput(""); }}
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
          const entry = selected.get(item.id);
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
                <AcupointPicker
                  selected={entry?.acupoints ?? []}
                  onAdd={(point) => addAcupoint(item.id, point)}
                  onRemove={(code) => removeAcupoint(item.id, code)}
                />
              )}

              {isSelected && (
                <button
                  onClick={() => toggleNonBenefit(item.id)}
                  className={`mt-1 w-full rounded border px-2 py-1 text-[10px] font-medium transition-colors ${
                    entry?.isNonBenefit
                      ? "border-amber-400 bg-amber-50 text-amber-700"
                      : "border-border bg-card text-subtext hover:text-text"
                  }`}
                >
                  {entry?.isNonBenefit ? "비급여 ✓" : "비급여로 변경"}
                </button>
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
            {Array.from(selected.values()).map(({ item, isNonBenefit }) => (
              <div key={item.id} className="flex items-center justify-between text-xs">
                <span className="text-text truncate pr-2">
                  {item.name}
                  {isNonBenefit && (
                    <span className="ml-1 text-[10px] text-amber-600 font-medium">비급여</span>
                  )}
                </span>
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
          {nonBenefitTotal > 0 && (
            <div className="mt-1 flex items-center justify-between">
              <span className="text-xs text-amber-600">비급여 합계</span>
              <span className="text-xs font-medium text-amber-600 tabular-nums">{nonBenefitTotal.toLocaleString()}원</span>
            </div>
          )}
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
