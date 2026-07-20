"use client";
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import {
  ClaimPayment,
  ClaimPaymentSummary,
  getClaimPaymentSummary,
  listClaimPayments,
} from "@/lib/api/billing";

interface PaymentHistoryModalProps {
  onClose: () => void;
}

const METHOD_LABEL: Record<string, string> = {
  cash: "현금",
  card: "카드",
  transfer: "계좌이체",
};

const SIZE = 20;

const EMPTY_SUMMARY: ClaimPaymentSummary = {
  today_total: 0,
  month_total: 0,
  cash_ratio: 0,
  card_ratio: 0,
};

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-fill/40 px-3 py-2">
      <div className="text-[10px] text-subtext mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-text">{value}</div>
    </div>
  );
}

export default function PaymentHistoryModal({ onClose }: PaymentHistoryModalProps) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [method, setMethod] = useState("");
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<ClaimPayment[]>([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<ClaimPaymentSummary>(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setPage(1);
  }, [startDate, endDate, method]);

  useEffect(() => {
    setLoading(true);
    const params = {
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      method: method || undefined,
    };
    Promise.all([
      listClaimPayments({ ...params, page, size: SIZE }),
      getClaimPaymentSummary(params),
    ])
      .then(([listResult, summaryResult]) => {
        setItems(listResult.items);
        setTotal(listResult.total);
        setSummary(summaryResult);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
        setSummary(EMPTY_SUMMARY);
      })
      .finally(() => setLoading(false));
  }, [startDate, endDate, method, page]);

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <div className="text-sm font-medium text-text">수납 내역</div>
          <button onClick={onClose} className="text-subtext hover:text-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-fill border border-border rounded-md px-2 py-1.5 text-xs text-text outline-none focus:border-[#EF6600] transition-colors"
            />
            <span className="text-xs text-muted">~</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-fill border border-border rounded-md px-2 py-1.5 text-xs text-text outline-none focus:border-[#EF6600] transition-colors"
            />
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="bg-fill border border-border rounded-md px-2 py-1.5 text-xs text-text outline-none focus:border-[#EF6600] transition-colors"
            >
              <option value="">전체 수납방법</option>
              <option value="cash">현금</option>
              <option value="card">카드</option>
              <option value="transfer">계좌이체</option>
            </select>
            {(startDate || endDate || method) && (
              <button
                onClick={() => {
                  setStartDate("");
                  setEndDate("");
                  setMethod("");
                }}
                className="text-xs text-subtext hover:text-text transition-colors"
              >
                필터 초기화
              </button>
            )}
          </div>

          <div className="grid grid-cols-4 gap-2">
            <SummaryCard label="오늘 수납액" value={`${summary.today_total.toLocaleString()}원`} />
            <SummaryCard label="이번달 수납액" value={`${summary.month_total.toLocaleString()}원`} />
            <SummaryCard label="현금 비율" value={`${summary.cash_ratio}%`} />
            <SummaryCard label="카드 비율" value={`${summary.card_ratio}%`} />
          </div>

          <div className="border border-border rounded-md overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-fill text-subtext">
                <tr>
                  <th className="text-left px-2 py-1.5 font-medium">날짜</th>
                  <th className="text-left px-2 py-1.5 font-medium">환자명</th>
                  <th className="text-center px-2 py-1.5 font-medium">수납방법</th>
                  <th className="text-right px-2 py-1.5 font-medium">청구액</th>
                  <th className="text-right px-2 py-1.5 font-medium">수납액</th>
                  <th className="text-left px-2 py-1.5 font-medium">처리자</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center text-muted py-6">
                      불러오는 중...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center text-muted py-6">
                      수납 내역이 없습니다
                    </td>
                  </tr>
                ) : (
                  items.map((p) => (
                    <tr key={p.id} className="border-t border-border">
                      <td className="px-2 py-1.5 text-subtext">{p.paid_at}</td>
                      <td className="px-2 py-1.5 text-text">{p.patient_name}</td>
                      <td className="px-2 py-1.5 text-center text-subtext">{METHOD_LABEL[p.method] || p.method}</td>
                      <td className="px-2 py-1.5 text-right text-subtext">{p.claim_amount.toLocaleString()}원</td>
                      <td className="px-2 py-1.5 text-right text-text font-medium">{p.amount.toLocaleString()}원</td>
                      <td className="px-2 py-1.5 text-subtext">{p.processed_by_name}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-2 py-1 text-xs rounded-md border border-border text-subtext hover:text-text disabled:opacity-40 transition-colors"
              >
                이전
              </button>
              <span className="text-xs text-subtext">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-2 py-1 text-xs rounded-md border border-border text-subtext hover:text-text disabled:opacity-40 transition-colors"
              >
                다음
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
