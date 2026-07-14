"use client";
import MiniCalendar from "@/components/reception/MiniCalendar";
import PatientManagementPanel from "@/components/reception/PatientManagementPanel";
import BillingModal from "@/components/billing/BillingModal";
import { getPatients } from "@/lib/api/patients";
import {
  checkinPatient,
  getQueueByDate,
  getQueueCalendar,
  getTodayQueue,
  updateQueueBed,
  QueueItem,
} from "@/lib/api/queue";
import { Patient } from "@/types";
import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";

const STATUS_LABEL: Record<QueueItem["status"], string> = {
  waiting: "대기",
  in_progress: "진료중",
  billed: "처치·수납대기",
  paid: "진료완료",
};

const STATUS_STYLE: Record<QueueItem["status"], { border: string; badge: string }> = {
  waiting: { border: "border-l-gray-400", badge: "bg-gray-400/15 text-gray-500" },
  in_progress: { border: "border-l-blue-500", badge: "bg-blue-500/15 text-blue-500" },
  billed: { border: "border-l-amber-500", badge: "bg-amber-500/15 text-amber-600" },
  paid: { border: "border-l-green-500", badge: "bg-green-500/15 text-green-500" },
};

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function calcAge(birthDate?: string | null): number | null {
  if (!birthDate) return null;
  return new Date().getFullYear() - new Date(birthDate).getFullYear();
}

function genderLabel(g?: string | null): string {
  return g === "M" ? "남" : g === "F" ? "여" : "";
}

export default function HomePage() {
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [calYear, setCalYear] = useState(new Date().getFullYear());
  const [calMonth, setCalMonth] = useState(new Date().getMonth() + 1);
  const [calendarCounts, setCalendarCounts] = useState<Record<string, number>>({});

  const [queueList, setQueueList] = useState<QueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);

  const [checkinSearch, setCheckinSearch] = useState("");
  const [checkinResults, setCheckinResults] = useState<Patient[]>([]);
  const [checkinLoading, setCheckinLoading] = useState(false);
  const searchTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [billingQueueItem, setBillingQueueItem] = useState<QueueItem | null>(null);
  const [bedDrafts, setBedDrafts] = useState<Record<string, string>>({});

  const isToday = selectedDate === todayStr();

  function loadQueue(date: string) {
    setQueueLoading(true);
    const loader = date === todayStr() ? getTodayQueue() : getQueueByDate(date);
    loader
      .then(setQueueList)
      .catch(() => setQueueList([]))
      .finally(() => setQueueLoading(false));
  }

  function loadCalendar(year: number, month: number) {
    getQueueCalendar(year, month)
      .then(setCalendarCounts)
      .catch(() => setCalendarCounts({}));
  }

  useEffect(() => {
    loadQueue(selectedDate);
  }, [selectedDate]);

  useEffect(() => {
    loadCalendar(calYear, calMonth);
  }, [calYear, calMonth]);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!checkinSearch) {
      setCheckinResults([]);
      return;
    }
    setCheckinLoading(true);
    searchTimerRef.current = setTimeout(() => {
      getPatients(checkinSearch)
        .then((result) => setCheckinResults(result.items))
        .catch(() => setCheckinResults([]))
        .finally(() => setCheckinLoading(false));
    }, 300);
  }, [checkinSearch]);

  function handleMonthChange(year: number, month: number) {
    setCalYear(year);
    setCalMonth(month);
  }

  function handleCheckin(patient: Patient) {
    checkinPatient(patient.id)
      .then((item) => {
        setQueueList((prev) => [...prev, item]);
        setCheckinSearch("");
        setCheckinResults([]);
        loadCalendar(calYear, calMonth);
      })
      .catch(console.error);
  }

  function handleBedBlur(item: QueueItem) {
    const draft = bedDrafts[item.id];
    if (draft === undefined || draft === (item.assigned_bed || "")) return;
    updateQueueBed(item.id, draft || null)
      .then((updated) => {
        setQueueList((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
      })
      .catch(console.error);
  }

  function handleCheckoutComplete(updated: QueueItem) {
    setQueueList((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
    setBillingQueueItem(null);
  }

  const sortedQueue = [...queueList].sort((a, b) => {
    const order = { waiting: 0, in_progress: 1, billed: 2, paid: 3 };
    if (order[a.status] !== order[b.status]) return order[a.status] - order[b.status];
    return new Date(a.checked_in_at).getTime() - new Date(b.checked_in_at).getTime();
  });

  return (
    <div className="flex gap-4 p-4 md:p-6" style={{ minHeight: "calc(100vh - 52px)" }}>
      {/* 좌측 사이드바: 달력 + 검색 + 접수목록 */}
      <div className="w-[260px] flex-shrink-0 flex flex-col gap-3">
        <div className="bg-card border border-border rounded-lg p-3">
          <MiniCalendar
            year={calYear}
            month={calMonth}
            counts={calendarCounts}
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            onMonthChange={handleMonthChange}
          />
        </div>

        {isToday && (
          <div className="bg-card border border-border rounded-lg p-3">
            <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2 mb-2">
              <Search className="w-3.5 h-3.5 text-muted flex-shrink-0" />
              <input
                value={checkinSearch}
                onChange={(e) => setCheckinSearch(e.target.value)}
                placeholder="환자 검색 후 접수..."
                className="flex-1 bg-transparent text-xs text-text outline-none"
              />
            </div>
            {checkinSearch && (
              <div className="max-h-[160px] overflow-y-auto">
                {checkinLoading ? (
                  <div className="text-xs text-muted text-center py-2">검색 중...</div>
                ) : checkinResults.length === 0 ? (
                  <div className="text-xs text-muted text-center py-2">검색 결과 없음</div>
                ) : (
                  checkinResults.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => handleCheckin(p)}
                      className="flex flex-col py-1.5 px-1 cursor-pointer hover:bg-fill rounded transition-colors"
                    >
                      <span className="text-xs font-medium text-text">{p.name}</span>
                      <span className="text-[10px] text-subtext">{p.birth_date || "-"}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        <div className="bg-card border border-border rounded-lg p-3 flex-1 overflow-hidden flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <div className="text-xs font-medium text-text uppercase tracking-wide">
              {isToday ? "오늘 접수" : `${selectedDate} 접수`}
            </div>
            <span className="text-xs text-muted bg-fill rounded-full px-1.5 py-0.5">{queueList.length}</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {queueLoading ? (
              <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto my-4" />
            ) : sortedQueue.length === 0 ? (
              <div className="text-xs text-muted text-center py-4">접수된 환자가 없습니다</div>
            ) : (
              sortedQueue.map((item) => {
                const style = STATUS_STYLE[item.status];
                return (
                  <div
                    key={item.id}
                    onClick={() => setBillingQueueItem(item)}
                    className={`border-l-[3px] ${style.border} bg-fill/40 hover:bg-fill rounded-r-md px-2.5 py-2 mb-1.5 cursor-pointer transition-colors`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-sm font-medium text-text truncate">
                        {item.patient_name}
                        {(calcAge(item.patient_birth_date) !== null || genderLabel(item.patient_gender)) && (
                          <span className="text-[10px] text-subtext font-normal ml-1">
                            {[
                              calcAge(item.patient_birth_date) !== null ? `${calcAge(item.patient_birth_date)}세` : null,
                              genderLabel(item.patient_gender) || null,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        )}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${style.badge}`}>
                        {STATUS_LABEL[item.status]}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-[10px] text-subtext">
                        {new Date(item.checked_in_at).toLocaleTimeString("ko-KR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      <input
                        value={bedDrafts[item.id] ?? item.assigned_bed ?? ""}
                        onChange={(e) =>
                          setBedDrafts((prev) => ({ ...prev, [item.id]: e.target.value }))
                        }
                        onBlur={() => handleBedBlur(item)}
                        onClick={(e) => e.stopPropagation()}
                        placeholder="베드"
                        className="w-14 bg-transparent border border-border rounded px-1 py-0.5 text-[10px] text-text outline-none focus:border-[#EF6600] transition-colors text-right"
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 우측: 환자 관리 패널 */}
      <div className="flex-1 min-w-0">
        <PatientManagementPanel />
      </div>

      {billingQueueItem && (
        <BillingModal
          queueItem={billingQueueItem}
          onClose={() => setBillingQueueItem(null)}
          onComplete={handleCheckoutComplete}
        />
      )}
    </div>
  );
}
