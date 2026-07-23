"use client";
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { getPatientRecordsAll, type PatientRecordItem } from "@/lib/api/patients";
import { listClaimPayments, type ClaimPayment } from "@/lib/api/billing";
import type { Patient } from "@/types";

interface PatientHistoryModalProps {
  patient: Patient;
  onClose: () => void;
}

const METHOD_LABEL: Record<string, string> = {
  cash: "현금",
  card: "카드",
  transfer: "계좌이체",
};

const RECORDS_PAGE_SIZE = 10;

export default function PatientHistoryModal({ patient, onClose }: PatientHistoryModalProps) {
  const [tab, setTab] = useState<"records" | "payments">("records");
  const [records, setRecords] = useState<PatientRecordItem[]>([]);
  const [recordsTotal, setRecordsTotal] = useState(0);
  const [recordsPage, setRecordsPage] = useState(1);
  const [recordsLoadingMore, setRecordsLoadingMore] = useState(false);
  const [payments, setPayments] = useState<ClaimPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setRecordsPage(1);
    Promise.all([
      getPatientRecordsAll(patient.id, 1, RECORDS_PAGE_SIZE).catch(() => ({ total: 0, items: [] as PatientRecordItem[] })),
      listClaimPayments({ patient_id: patient.id, size: 50 }).catch(() => ({ items: [] as ClaimPayment[] })),
    ])
      .then(([recordsRes, paymentsRes]) => {
        setRecords(recordsRes.items);
        setRecordsTotal(recordsRes.total);
        setPayments(paymentsRes.items);
      })
      .finally(() => setLoading(false));
  }, [patient.id]);

  function loadMoreRecords() {
    const nextPage = recordsPage + 1;
    setRecordsLoadingMore(true);
    getPatientRecordsAll(patient.id, nextPage, RECORDS_PAGE_SIZE)
      .then((res) => {
        setRecords((prev) => [...prev, ...res.items]);
        setRecordsPage(nextPage);
        setRecordsTotal(res.total);
      })
      .catch(() => {})
      .finally(() => setRecordsLoadingMore(false));
  }

  return (
    <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl w-full max-w-lg shadow-xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <div className="text-sm font-medium text-text">{patient.name} 이력</div>
          <button onClick={onClose} className="text-subtext hover:text-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex border-b border-border flex-shrink-0">
          <button
            onClick={() => setTab("records")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              tab === "records" ? "text-[#EF6600] border-b-2 border-[#EF6600]" : "text-subtext"
            }`}
          >
            진료 이력{recordsTotal > 0 ? ` (${recordsTotal}건)` : ""}
          </button>
          <button
            onClick={() => setTab("payments")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              tab === "payments" ? "text-[#EF6600] border-b-2 border-[#EF6600]" : "text-subtext"
            }`}
          >
            수납 내역
          </button>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
          ) : tab === "records" ? (
            records.length === 0 ? (
              <div className="text-sm text-muted text-center py-16">진료 이력이 없습니다</div>
            ) : (
              <ul className="divide-y divide-border">
                {records.map((r) => {
                  const kcdList = [r.kcd_code, ...(r.secondary_kcd_codes ?? [])].filter(Boolean);
                  const expanded = expandedId === r.id;
                  return (
                    <li key={r.id} className="p-4">
                      <button
                        onClick={() => setExpandedId(expanded ? null : r.id)}
                        className="w-full flex items-center justify-between text-left"
                      >
                        <div>
                          <div className="text-xs text-subtext">
                            {r.recorded_at ? r.recorded_at.slice(0, 10) : "-"}
                          </div>
                          <div className="text-sm text-text mt-0.5">
                            {kcdList.length > 0 ? kcdList.join(", ") : "상병코드 없음"}
                          </div>
                        </div>
                        <span className="text-xs text-subtext">{expanded ? "접기" : "펼치기"}</span>
                      </button>
                      {expanded && (
                        <pre className="mt-3 text-xs text-text whitespace-pre-wrap bg-fill rounded-md p-3 font-sans">
                          {r.chart_structured || "차트 내용 없음"}
                        </pre>
                      )}
                    </li>
                  );
                })}
              </ul>
            )
          ) : null}
          {tab === "records" && !loading && records.length < recordsTotal && (
            <div className="p-3 text-center">
              <button
                onClick={loadMoreRecords}
                disabled={recordsLoadingMore}
                className="text-xs text-subtext hover:text-[#EF6600] transition-colors disabled:opacity-50"
              >
                {recordsLoadingMore ? "불러오는 중..." : "더보기"}
              </button>
            </div>
          )}
          {tab === "payments" && (payments.length === 0 ? (
            <div className="text-sm text-muted text-center py-16">수납 내역이 없습니다</div>
          ) : (
            <ul className="divide-y divide-border">
              {payments.map((p) => (
                <li key={p.id} className="p-4 flex items-center justify-between text-xs">
                  <div>
                    <div className="text-text">{p.paid_at}</div>
                    <div className="text-subtext mt-0.5">
                      {METHOD_LABEL[p.method] ?? p.method} · {p.processed_by_name || "-"}
                    </div>
                  </div>
                  <div className="text-sm font-medium text-text">{p.amount.toLocaleString()}원</div>
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </div>
  );
}
