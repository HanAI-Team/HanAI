"use client";
import { useEffect, useState } from "react";
import { X, Trash2 } from "lucide-react";
import { QueueItem, checkoutQueueItem } from "@/lib/api/queue";
import { KcdSearchResult, searchKcd } from "@/lib/api/kcd";
import {
  getQuickFeeItems,
  previewCheckoutBilling,
  CheckoutPreviewResult,
  QuickFeeItem,
  QuickFeeItems,
} from "@/lib/api/billing";

interface BillingModalProps {
  queueItem: QueueItem;
  onClose: () => void;
  onComplete: (updated: QueueItem) => void;
}

interface LineItemRow {
  code: string;
  name: string;
  unit_price: number;
  qty: number;
  days: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  침술: "bg-blue-500/10 text-blue-600 border-blue-500/30 hover:bg-blue-500/20",
  뜸: "bg-amber-500/10 text-amber-600 border-amber-500/30 hover:bg-amber-500/20",
  부항: "bg-purple-500/10 text-purple-600 border-purple-500/30 hover:bg-purple-500/20",
  추나: "bg-rose-500/10 text-rose-600 border-rose-500/30 hover:bg-rose-500/20",
};
const DEFAULT_COLOR = "bg-gray-400/10 text-gray-600 border-gray-400/30 hover:bg-gray-400/20";

const EMPTY_PREVIEW: CheckoutPreviewResult = {
  total_amount: 0,
  patient_copay: 0,
  claim_amount: 0,
  special_code: null,
};

function calcAge(birthDate?: string | null): number | null {
  if (!birthDate) return null;
  return new Date().getFullYear() - new Date(birthDate).getFullYear();
}

function genderLabel(g?: string | null): string {
  return g === "M" ? "남" : g === "F" ? "여" : "";
}

function SummaryCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-md border px-3 py-2 ${highlight ? "border-[#EF6600] bg-[#EF6600]/5" : "border-border bg-fill/40"}`}>
      <div className="text-[10px] text-subtext mb-0.5">{label}</div>
      <div className={`text-sm font-semibold ${highlight ? "text-[#EF6600]" : "text-text"}`}>{value}</div>
    </div>
  );
}

export default function BillingModal({ queueItem, onClose, onComplete }: BillingModalProps) {
  const [kcdQuery, setKcdQuery] = useState("");
  const [kcdResults, setKcdResults] = useState<KcdSearchResult[]>([]);
  const [kcdDropdownOpen, setKcdDropdownOpen] = useState(false);
  const [kcdCode, setKcdCode] = useState<KcdSearchResult | null>(null);

  const [quickItems, setQuickItems] = useState<QuickFeeItems | null>(null);
  const [activeTab, setActiveTab] = useState("자주");

  const [lineItems, setLineItems] = useState<LineItemRow[]>([]);
  const [preview, setPreview] = useState<CheckoutPreviewResult>(EMPTY_PREVIEW);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getQuickFeeItems().then(setQuickItems).catch(() => setQuickItems(null));
  }, []);

  useEffect(() => {
    if (!kcdQuery.trim()) {
      setKcdResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchKcd(kcdQuery).then(setKcdResults).catch(() => setKcdResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [kcdQuery]);

  useEffect(() => {
    if (lineItems.length === 0) {
      setPreview(EMPTY_PREVIEW);
      return;
    }
    const timer = setTimeout(() => {
      previewCheckoutBilling(
        queueItem.patient_id,
        lineItems.map((li) => ({ code: li.code, qty: li.qty, days: li.days }))
      )
        .then(setPreview)
        .catch(() => {});
    }, 200);
    return () => clearTimeout(timer);
  }, [lineItems, queueItem.patient_id]);

  function addQuickItem(item: QuickFeeItem) {
    setLineItems((prev) => {
      const existing = prev.find((li) => li.code === item.code);
      if (existing) {
        return prev.map((li) => (li.code === item.code ? { ...li, qty: li.qty + 1 } : li));
      }
      return [...prev, { code: item.code, name: item.name, unit_price: item.unit_price, qty: 1, days: 1 }];
    });
  }

  function updateLineItem(code: string, patch: Partial<LineItemRow>) {
    setLineItems((prev) => prev.map((li) => (li.code === code ? { ...li, ...patch } : li)));
  }

  function removeLineItem(code: string) {
    setLineItems((prev) => prev.filter((li) => li.code !== code));
  }

  async function handleSubmit() {
    if (!kcdCode) {
      setError("진단(상병코드)를 입력해주세요.");
      return;
    }
    if (lineItems.length === 0) {
      setError("처방/시술 내역을 1개 이상 추가해주세요.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await checkoutQueueItem(
        queueItem.id,
        kcdCode.code,
        lineItems.map((li) => ({ code: li.code, qty: li.qty, days: li.days }))
      );
      onComplete(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "청구 저장 실패");
    } finally {
      setSaving(false);
    }
  }

  const tabs = quickItems ? ["자주", ...quickItems.categories] : ["자주"];
  const tabItems: QuickFeeItem[] = quickItems
    ? activeTab === "자주"
      ? quickItems.favorites
      : quickItems.by_category[activeTab] || []
    : [];

  const age = calcAge(queueItem.patient_birth_date);
  const gender = genderLabel(queueItem.patient_gender);

  return (
    <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-text">{queueItem.patient_name}</span>
            {(age !== null || gender) && (
              <span className="text-xs text-subtext">
                {[age !== null ? `${age}세` : null, gender || null].filter(Boolean).join(" · ")}
              </span>
            )}
            <span className="text-xs text-muted">
              접수{" "}
              {new Date(queueItem.checked_in_at).toLocaleTimeString("ko-KR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {queueItem.assigned_bed && (
              <span className="text-[10px] bg-fill rounded-full px-2 py-0.5 text-subtext">
                {queueItem.assigned_bed}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-subtext hover:text-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
          <div className="grid grid-cols-4 gap-2">
            <SummaryCard label="총진료비" value={`${preview.total_amount.toLocaleString()}원`} />
            <SummaryCard label="본인부담금" value={`${preview.patient_copay.toLocaleString()}원`} />
            <SummaryCard label="청구액" value={`${preview.claim_amount.toLocaleString()}원`} />
            <SummaryCard
              label="산정특례"
              value={preview.special_code ? preview.special_code : "해당없음"}
              highlight={!!preview.special_code}
            />
          </div>

          <div>
            <div className="text-xs font-medium text-subtext mb-1.5">진단 (상병코드)</div>
            {kcdCode ? (
              <div className="flex items-center justify-between gap-2 bg-fill border border-border rounded-md px-3 py-2">
                <div className="text-sm text-text">
                  <span className="font-medium text-[#EF6600]">{kcdCode.code}</span>
                  {kcdCode.korean_name ? <span> {kcdCode.korean_name}</span> : null}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setKcdCode(null);
                    setKcdQuery("");
                  }}
                  className="text-subtext hover:text-text transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  value={kcdQuery}
                  onChange={(e) => {
                    setKcdQuery(e.target.value);
                    setKcdDropdownOpen(true);
                  }}
                  onFocus={() => setKcdDropdownOpen(true)}
                  onBlur={() => setTimeout(() => setKcdDropdownOpen(false), 150)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && kcdQuery.trim()) {
                      const match = kcdResults[0];
                      const code = match ?? { code: kcdQuery.trim().toUpperCase(), korean_name: "" };
                      setKcdCode(code);
                      setKcdQuery("");
                      setKcdResults([]);
                      setKcdDropdownOpen(false);
                    }
                  }}
                  placeholder="코드 또는 진단명 검색 (예: M545, 요통)"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
                {kcdDropdownOpen && (kcdResults.length > 0 || kcdQuery.trim().length > 0) && (
                  <div className="absolute left-0 right-0 mt-1 bg-card border border-border rounded-md shadow-lg max-h-48 overflow-y-auto z-10">
                    {kcdResults.map((item) => (
                      <button
                        key={item.code}
                        type="button"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setKcdCode(item);
                          setKcdQuery("");
                          setKcdResults([]);
                          setKcdDropdownOpen(false);
                        }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-bg transition-colors border-b border-border last:border-b-0"
                      >
                        <span className="font-medium text-[#EF6600]">{item.code}</span>{" "}
                        <span className="text-text">{item.korean_name}</span>
                      </button>
                    ))}
                    {kcdResults.length === 0 && kcdQuery.trim().length > 0 && (
                      <button
                        type="button"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setKcdCode({ code: kcdQuery.trim().toUpperCase(), korean_name: "" });
                          setKcdQuery("");
                          setKcdResults([]);
                          setKcdDropdownOpen(false);
                        }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-bg transition-colors"
                      >
                        <span className="text-subtext">직접 입력:</span>{" "}
                        <span className="font-medium text-text">{kcdQuery.trim()}</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <div className="text-xs font-medium text-subtext mb-1.5">처방/시술 내역</div>
            <div className="flex gap-1 mb-2 flex-wrap">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 text-xs rounded-full transition-colors ${
                    activeTab === tab ? "bg-[#EF6600] text-white" : "bg-fill text-subtext hover:text-text"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5 mb-3 max-h-[140px] overflow-y-auto">
              {tabItems.length === 0 ? (
                <div className="col-span-full text-xs text-muted text-center py-4">항목이 없습니다</div>
              ) : (
                tabItems.map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => addQuickItem(item)}
                    className={`text-left px-2.5 py-1.5 rounded-md border text-xs transition-colors ${
                      CATEGORY_COLORS[item.category] || DEFAULT_COLOR
                    }`}
                  >
                    <div className="font-medium truncate">{item.name}</div>
                    <div className="text-[10px] opacity-70">{item.unit_price.toLocaleString()}원</div>
                  </button>
                ))
              )}
            </div>

            <div className="border border-border rounded-md overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-fill text-subtext">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium">코드명</th>
                    <th className="text-right px-2 py-1.5 font-medium w-20">단가</th>
                    <th className="text-center px-2 py-1.5 font-medium w-14">수량</th>
                    <th className="text-center px-2 py-1.5 font-medium w-14">일수</th>
                    <th className="text-right px-2 py-1.5 font-medium w-20">금액</th>
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center text-muted py-4">
                        추가된 항목이 없습니다
                      </td>
                    </tr>
                  ) : (
                    lineItems.map((li) => (
                      <tr key={li.code} className="border-t border-border">
                        <td className="px-2 py-1.5 text-text">{li.name}</td>
                        <td className="px-2 py-1.5 text-right text-subtext">{li.unit_price.toLocaleString()}</td>
                        <td className="px-1 py-1.5">
                          <input
                            type="number"
                            min={1}
                            value={li.qty}
                            onChange={(e) => updateLineItem(li.code, { qty: Math.max(1, Number(e.target.value) || 1) })}
                            className="w-full bg-transparent border border-border rounded px-1 py-0.5 text-center outline-none focus:border-[#EF6600]"
                          />
                        </td>
                        <td className="px-1 py-1.5">
                          <input
                            type="number"
                            min={1}
                            value={li.days}
                            onChange={(e) => updateLineItem(li.code, { days: Math.max(1, Number(e.target.value) || 1) })}
                            className="w-full bg-transparent border border-border rounded px-1 py-0.5 text-center outline-none focus:border-[#EF6600]"
                          />
                        </td>
                        <td className="px-2 py-1.5 text-right text-text font-medium">
                          {(li.unit_price * li.qty * li.days).toLocaleString()}
                        </td>
                        <td className="px-1 py-1.5 text-center">
                          <button
                            type="button"
                            onClick={() => removeLineItem(li.code)}
                            className="text-subtext hover:text-red-500 transition-colors"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {error && <div className="text-xs text-red-500">{error}</div>}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border flex-shrink-0">
          <button onClick={onClose} className="px-4 py-2 text-sm text-subtext hover:text-text transition-colors">
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium bg-[#EF6600] text-white rounded-md hover:opacity-90 transition-colors disabled:opacity-50"
          >
            {saving ? "저장 중..." : "저장 및 청구"}
          </button>
        </div>
      </div>
    </div>
  );
}
