"use client";
import { useEffect, useState } from "react";
import {
  ClaimListItem,
  bulkDownloadEdi,
  downloadEdi,
  getClaims,
  resubmitClaim,
  statusLabel,
} from "@/lib/api/billing";

const STATUS_FILTERS = [
  { key: "", label: "전체" },
  { key: "draft", label: "작성중" },
  { key: "submitted", label: "제출완료" },
  { key: "approved", label: "승인" },
  { key: "rejected", label: "반려" },
];

function getCurrentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function BillingPage() {
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(getCurrentMonth());
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState<string | null>(null);
  const [resubmitTarget, setResubmitTarget] = useState<ClaimListItem | null>(null);

  function reload() {
    setLoading(true);
    setSelected(new Set());
    getClaims({ month: month || undefined, status: statusFilter || undefined })
      .then(setClaims)
      .catch(() => setClaims([]))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [month, statusFilter]);

  const counts = {
    전체: claims.length,
    작성중: claims.filter((c) => c.status === "draft").length,
    제출완료: claims.filter((c) => c.status === "submitted").length,
    승인: claims.filter((c) => c.status === "approved").length,
    반려: claims.filter((c) => c.status === "rejected").length,
  };

  function toggleAll() {
    if (selected.size === claims.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(claims.map((c) => c.id)));
    }
  }

  function toggleOne(id: string) {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  }

  async function handleDownload(id: string) {
    setDownloading(id);
    try {
      await downloadEdi(id);
    } catch {
      alert("EDI 다운로드에 실패했습니다.");
    } finally {
      setDownloading(null);
    }
  }

  async function handleBulkDownload() {
    if (selected.size === 0) return;
    setDownloading("bulk");
    try {
      await bulkDownloadEdi([...selected]);
    } catch {
      alert("일괄 EDI 다운로드에 실패했습니다.");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="font-serif text-2xl text-text">보험 청구</h1>
        <p className="text-xs text-subtext mt-1">EDI 파일 생성 및 다운로드</p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          { label: "전체", value: counts["전체"], color: "text-text" },
          { label: "작성중", value: counts["작성중"], color: "text-subtext" },
          { label: "제출완료", value: counts["제출완료"], color: "text-blue-500" },
          { label: "승인", value: counts["승인"], color: "text-green-500" },
          { label: "반려", value: counts["반려"], color: "text-red-500" },
        ].map((s) => (
          <div key={s.label} className="bg-card border border-border rounded-lg p-4">
            <div className="text-xs text-subtext uppercase tracking-wide mb-1">{s.label}</div>
            <div className={`text-3xl font-light ${s.color}`}>{loading ? "-" : s.value}</div>
          </div>
        ))}
      </div>

      {/* 필터 영역 */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-text"
        />
        <div className="flex gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                statusFilter === f.key
                  ? "bg-[#EF6600] border-[#EF6600] text-white"
                  : "border-border text-subtext hover:text-text"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        {selected.size > 0 && (
          <button
            onClick={handleBulkDownload}
            disabled={downloading === "bulk"}
            className="ml-auto px-4 py-1.5 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] disabled:opacity-50 transition-all"
          >
            {downloading === "bulk" ? "생성 중..." : `EDI 일괄 다운로드 (${selected.size}건)`}
          </button>
        )}
      </div>

      {/* 테이블 */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr className="text-xs text-subtext">
              <th className="p-3 w-8">
                <input
                  type="checkbox"
                  checked={claims.length > 0 && selected.size === claims.length}
                  onChange={toggleAll}
                  className="cursor-pointer"
                />
              </th>
              <th className="p-3 text-left">환자명</th>
              <th className="p-3 text-left">청구월</th>
              <th className="p-3 text-left">상태</th>
              <th className="p-3 text-right">급여합계</th>
              <th className="p-3 text-right">본인부담</th>
              <th className="p-3 text-right">청구금액</th>
              <th className="p-3 text-center">EDI</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-subtext text-xs">
                  불러오는 중...
                </td>
              </tr>
            ) : claims.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-subtext text-xs">
                  청구 내역이 없습니다.
                </td>
              </tr>
            ) : (
              claims.map((claim) => (
                <tr
                  key={claim.id}
                  className={`border-t border-border hover:bg-fill transition-colors ${
                    selected.has(claim.id) ? "bg-fill" : ""
                  }`}
                >
                  <td className="p-3 text-center">
                    <input
                      type="checkbox"
                      checked={selected.has(claim.id)}
                      onChange={() => toggleOne(claim.id)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="p-3 text-text font-medium">{claim.patient_name}</td>
                  <td className="p-3 text-subtext">{claim.claim_period}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        claim.status === "rejected"
                          ? "bg-red-500/10 text-red-500"
                          : claim.status === "approved"
                          ? "bg-green-500/10 text-green-500"
                          : claim.status === "submitted"
                          ? "bg-blue-500/10 text-blue-500"
                          : "bg-fill text-subtext"
                      }`}
                    >
                      {statusLabel(claim.status)}
                    </span>
                  </td>
                  <td className="p-3 text-right text-text">
                    {claim.total_amount.toLocaleString()}원
                  </td>
                  <td className="p-3 text-right text-text">
                    {claim.patient_copay.toLocaleString()}원
                  </td>
                  <td className="p-3 text-right text-text font-medium">
                    {claim.claim_amount.toLocaleString()}원
                  </td>
                  <td className="p-3 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <button
                        onClick={() => handleDownload(claim.id)}
                        disabled={downloading === claim.id}
                        className="px-3 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text disabled:opacity-50 transition-all"
                      >
                        {downloading === claim.id ? "생성 중..." : "다운로드"}
                      </button>
                      {claim.status === "rejected" && (
                        <button
                          onClick={() => setResubmitTarget(claim)}
                          className="px-3 py-1 text-xs rounded-md border border-[#EF6600] text-[#EF6600] hover:bg-[#EF6600] hover:text-white transition-all"
                        >
                          보완·추가청구
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {resubmitTarget && (
        <ResubmissionModal
          claim={resubmitTarget}
          onClose={() => setResubmitTarget(null)}
          onDone={() => {
            setResubmitTarget(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function ResubmissionModal({
  claim,
  onClose,
  onDone,
}: {
  claim: ClaimListItem;
  onClose: () => void;
  onDone: () => void;
}) {
  const [claimType, setClaimType] = useState<"supplement" | "addition">("supplement");
  const [receiptNo, setReceiptNo] = useState("");
  const [recordSerial, setRecordSerial] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    if (!receiptNo || !recordSerial) {
      setError("접수번호와 명일련을 입력해주세요.");
      return;
    }
    if (claimType === "supplement" && !reasonCode) {
      setError("보완청구는 심사불능사유코드를 입력해주세요.");
      return;
    }
    setSubmitting(true);
    try {
      await resubmitClaim(claim.id, {
        claim_type: claimType,
        original_receipt_no: Number(receiptNo),
        original_record_serial: Number(recordSerial),
        rejection_reason_code: claimType === "supplement" ? reasonCode : undefined,
      });
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "처리에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-card border border-border rounded-lg p-6 w-[380px]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-lg text-text mb-1">보완·추가청구</h2>
        <p className="text-xs text-subtext mb-4">
          {claim.patient_name} · {claim.claim_period}
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-subtext mb-1">청구구분</label>
            <select
              value={claimType}
              onChange={(e) => setClaimType(e.target.value as "supplement" | "addition")}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            >
              <option value="supplement">보완청구</option>
              <option value="addition">추가청구</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-subtext mb-1">당초 청구명세서 접수번호</label>
            <input
              type="number"
              value={receiptNo}
              onChange={(e) => setReceiptNo(e.target.value)}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext mb-1">명일련</label>
            <input
              type="number"
              value={recordSerial}
              onChange={(e) => setRecordSerial(e.target.value)}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            />
          </div>
          {claimType === "supplement" && (
            <div>
              <label className="block text-xs text-subtext mb-1">심사불능사유코드 (2자리)</label>
              <input
                type="text"
                maxLength={2}
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
              />
            </div>
          )}
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 text-xs rounded-md border border-border text-subtext hover:text-text transition-all"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-3 py-2 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] disabled:opacity-50 transition-all"
          >
            {submitting ? "처리 중..." : "제출"}
          </button>
        </div>
      </div>
    </div>
  );
}
