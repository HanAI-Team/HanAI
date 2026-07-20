"use client";
import {
  ClaimReviewResult,
  getReviewResult,
  getReviewResults,
  uploadReviewResults,
} from "@/lib/api/billing";
import { useEffect, useState } from "react";

const RESULT_CODE_FILTERS = [
  { key: "", label: "전체" },
  { key: "인정", label: "인정" },
  { key: "삭감", label: "삭감" },
  { key: "보류", label: "보류" },
];

function resultBadgeClass(resultCode: string): string {
  if (resultCode === "인정") return "bg-green-500/10 text-green-500";
  if (resultCode === "삭감") return "bg-red-500/10 text-red-500";
  if (resultCode === "보류") return "bg-amber-500/10 text-amber-600";
  return "bg-fill text-subtext";
}

const PAGE_SIZE = 20;

export default function ReviewResultsTab() {
  const [items, setItems] = useState<ClaimReviewResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [resultCodeFilter, setResultCodeFilter] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [detail, setDetail] = useState<ClaimReviewResult | null>(null);

  function reload() {
    setLoading(true);
    getReviewResults({
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      resultCode: resultCodeFilter || undefined,
      page,
      size: PAGE_SIZE,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }

  useEffect(reload, [startDate, endDate, resultCodeFilter, page]);

  async function handleRowClick(item: ClaimReviewResult) {
    try {
      const full = await getReviewResult(item.id);
      setDetail(full);
    } catch (e) {
      alert(e instanceof Error ? e.message : "상세 조회에 실패했습니다.");
    }
  }

  function handlePrint() {
    const printWindow = window.open("", "_blank", "width=1000,height=800");
    if (!printWindow) {
      alert("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    const rowsHtml = items
      .map(
        (item) =>
          `<tr>` +
          `<td>${item.receipt_number}</td>` +
          `<td>${item.review_type}</td>` +
          `<td>${item.result_code}</td>` +
          `<td class="right">${item.original_amount.toLocaleString()}원</td>` +
          `<td class="right">${item.approved_amount.toLocaleString()}원</td>` +
          `<td class="right">${item.reduced_amount.toLocaleString()}원</td>` +
          `<td>${item.review_date}</td>` +
          `</tr>`
      )
      .join("");

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>심사결과 조회</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:20px 28px;font-size:12px}`
      + `h1{font-size:16px;font-weight:bold;margin-bottom:10px}`
      + `table{width:100%;border-collapse:collapse;font-size:11px}`
      + `th,td{border:1px solid #999;padding:5px 8px;text-align:center}`
      + `th{background:#f0f0f0;font-weight:500}`
      + `td.right{text-align:right}`
      + `@media print{body{padding:0}@page{margin:10mm;size:A4}}`
      + `</style></head><body>`
      + `<h1>심사결과 조회</h1>`
      + `<table><thead><tr>`
      + `<th>접수번호</th><th>심사구분</th><th>결과코드</th><th>청구금액</th><th>인정금액</th><th>삭감금액</th><th>심사일자</th>`
      + `</tr></thead><tbody>${rowsHtml || `<tr><td colspan="7">데이터가 없습니다.</td></tr>`}</tbody></table>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="date"
          value={startDate}
          onChange={(e) => {
            setPage(1);
            setStartDate(e.target.value);
          }}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-text"
        />
        <span className="text-xs text-subtext">~</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => {
            setPage(1);
            setEndDate(e.target.value);
          }}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-text"
        />
        <select
          value={resultCodeFilter}
          onChange={(e) => {
            setPage(1);
            setResultCodeFilter(e.target.value);
          }}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-text"
        >
          {RESULT_CODE_FILTERS.map((f) => (
            <option key={f.key} value={f.key}>
              {f.label}
            </option>
          ))}
        </select>
        <div className="ml-auto flex gap-2">
          <button
            onClick={handlePrint}
            className="px-4 py-1.5 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-all"
          >
            인쇄
          </button>
          <button
            onClick={() => setUploadOpen(true)}
            className="px-4 py-1.5 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] transition-all"
          >
            심사결과 업로드
          </button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr className="text-xs text-subtext">
              <th className="p-3 text-left">접수번호</th>
              <th className="p-3 text-left">심사구분</th>
              <th className="p-3 text-left">결과코드</th>
              <th className="p-3 text-right">청구금액</th>
              <th className="p-3 text-right">인정금액</th>
              <th className="p-3 text-right">삭감금액</th>
              <th className="p-3 text-left">심사일자</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-subtext text-xs">
                  불러오는 중...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-subtext text-xs">
                  심사결과 내역이 없습니다.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => handleRowClick(item)}
                  className="border-t border-border hover:bg-fill transition-colors cursor-pointer"
                >
                  <td className="p-3 text-text">{item.receipt_number}</td>
                  <td className="p-3 text-subtext">{item.review_type}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${resultBadgeClass(item.result_code)}`}>
                      {item.result_code}
                    </span>
                  </td>
                  <td className="p-3 text-right text-text">{item.original_amount.toLocaleString()}원</td>
                  <td className="p-3 text-right text-text">{item.approved_amount.toLocaleString()}원</td>
                  <td className="p-3 text-right text-text">{item.reduced_amount.toLocaleString()}원</td>
                  <td className="p-3 text-subtext">{item.review_date}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-xs rounded-md border border-border text-subtext hover:text-text disabled:opacity-40 transition-all"
          >
            이전
          </button>
          <span className="text-xs text-subtext">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-xs rounded-md border border-border text-subtext hover:text-text disabled:opacity-40 transition-all"
          >
            다음
          </button>
        </div>
      )}

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onDone={() => {
            setUploadOpen(false);
            setPage(1);
            reload();
          }}
        />
      )}

      {detail && <DetailModal item={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function UploadModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!file) {
      setError("CSV 파일을 선택해주세요.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const res = await uploadReviewResults(file);
      alert(`업로드 완료: ${res.inserted}건 등록, ${res.skipped}건 건너뜀`);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드에 실패했습니다.");
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
        <h2 className="font-serif text-lg text-text mb-1">심사결과 업로드</h2>
        <p className="text-xs text-subtext mb-4">
          접수번호, 심사구분, 결과코드, 청구금액, 인정금액, 삭감금액, 삭감사유, 심사일자 컬럼을 포함한 CSV 파일
        </p>

        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
        />
        {error && <p className="text-xs text-red-500 mt-2">{error}</p>}

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
            {submitting ? "업로드 중..." : "업로드"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailModal({ item, onClose }: { item: ClaimReviewResult; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-card border border-border rounded-lg p-6 w-[480px] max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-lg text-text mb-1">심사결과 상세</h2>
        <p className="text-xs text-subtext mb-4">
          접수번호 {item.receipt_number} · {item.review_type}
        </p>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-subtext">결과코드</span>
            <span className={`px-2 py-0.5 rounded-full text-xs ${resultBadgeClass(item.result_code)}`}>
              {item.result_code}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-subtext">청구금액</span>
            <span className="text-text">{item.original_amount.toLocaleString()}원</span>
          </div>
          <div className="flex justify-between">
            <span className="text-subtext">인정금액</span>
            <span className="text-text">{item.approved_amount.toLocaleString()}원</span>
          </div>
          <div className="flex justify-between">
            <span className="text-subtext">삭감금액</span>
            <span className="text-text">{item.reduced_amount.toLocaleString()}원</span>
          </div>
          <div className="flex justify-between">
            <span className="text-subtext">심사일자</span>
            <span className="text-text">{item.review_date}</span>
          </div>
        </div>

        <div className="mt-4">
          <div className="text-xs text-subtext mb-1">삭감사유</div>
          <div className="bg-fill border border-border rounded-md p-3 text-xs text-text min-h-[2.5rem] whitespace-pre-wrap">
            {item.reduce_reason || "-"}
          </div>
        </div>

        <div className="mt-4">
          <div className="text-xs text-subtext mb-1">원본 내용</div>
          <div className="bg-fill border border-border rounded-md p-3 text-xs text-text whitespace-pre-wrap break-all">
            {item.raw_content || "-"}
          </div>
        </div>

        <div className="flex mt-5">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 text-xs rounded-md border border-border text-subtext hover:text-text transition-all"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
