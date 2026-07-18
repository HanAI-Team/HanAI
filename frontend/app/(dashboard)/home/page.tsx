"use client";
import MiniCalendar from "@/components/reception/MiniCalendar";
import CheckinSearchPanel from "@/components/reception/CheckinSearchPanel";
import BillingModal from "@/components/billing/BillingModal";
import {
  getQueueByDate,
  getQueueCalendar,
  getTodayQueue,
  updateQueueBed,
  QueueItem,
} from "@/lib/api/queue";
import { useEffect, useState } from "react";

const STATUS_LABEL: Record<QueueItem["status"], string> = {
  waiting: "대기",
  in_progress: "진료중",
  billed: "수납대기",
  paid: "진료완료",
};

const STATUS_STYLE: Record<QueueItem["status"], { border: string; badge: string }> = {
  waiting: { border: "border-l-gray-400", badge: "bg-gray-400/15 text-gray-500" },
  in_progress: { border: "border-l-blue-500", badge: "bg-blue-500/15 text-blue-500" },
  billed: { border: "border-l-amber-500", badge: "bg-amber-500/15 text-amber-600" },
  paid: { border: "border-l-green-500", badge: "bg-green-500/15 text-green-500" },
};

// 구 3단계 상태 체계(waiting/in_progress/done) 시절에 생성된 레코드가 DB에 남아있을 수 있어
// 4단계 맵에 없는 status가 들어와도 화면이 죽지 않도록 안전한 기본값을 둔다.
const FALLBACK_STYLE = { border: "border-l-gray-300", badge: "bg-gray-300/15 text-gray-400" };
function statusLabel(status: QueueItem["status"]): string {
  return STATUS_LABEL[status] ?? status;
}
function statusStyle(status: QueueItem["status"]): { border: string; badge: string } {
  return STATUS_STYLE[status] ?? FALLBACK_STYLE;
}

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

  function handleMonthChange(year: number, month: number) {
    setCalYear(year);
    setCalMonth(month);
  }

  function handleCheckedIn(item: QueueItem) {
    // 오늘 접수한 건은 오늘 목록을 보고 있을 때만 즉시 반영 — 다른 날짜를 보고 있으면
    // 그 날짜 목록에 섞이지 않도록 한다.
    if (isToday) {
      setQueueList((prev) => [...prev, item]);
    }
    setCalendarCounts((prev) => ({
      ...prev,
      [todayStr()]: (prev[todayStr()] || 0) + 1,
    }));
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

  const sortedQueue = [...queueList].sort(
    (a, b) => new Date(a.checked_in_at).getTime() - new Date(b.checked_in_at).getTime()
  );

  return (
    <div className="flex gap-4 p-4 md:p-6" style={{ minHeight: "calc(100vh - 52px)" }}>
      {/* 좌측 사이드바: 달력 + 접수 현황 */}
      <div className="w-[280px] flex-shrink-0 flex flex-col gap-3">
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

        <div className="bg-card border border-border rounded-lg p-3 flex-1 overflow-hidden flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <div className="text-xs font-medium text-text uppercase tracking-wide">
              {isToday ? "오늘 접수 현황" : `${selectedDate} 접수 현황`}
            </div>
            <span className="text-xs text-muted bg-fill rounded-full px-1.5 py-0.5">{queueList.length}명</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {queueLoading ? (
              <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto my-4" />
            ) : sortedQueue.length === 0 ? (
              <div className="text-xs text-muted text-center py-4">접수된 환자가 없습니다</div>
            ) : (
              sortedQueue.map((item, i) => {
                const style = statusStyle(item.status);
                return (
                  <div
                    key={item.id}
                    onClick={() => setBillingQueueItem(item)}
                    className={`border-l-[3px] ${style.border} bg-fill/40 hover:bg-fill rounded-r-md px-2.5 py-2 mb-1.5 cursor-pointer transition-colors`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-sm font-medium text-text truncate">
                        <span className="text-[10px] text-muted font-normal mr-1">{i + 1}.</span>
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
                        {statusLabel(item.status)}
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

      {/* 우측: 환자 검색 · 접수 */}
      <div className="flex-1 min-w-0">
        <CheckinSearchPanel onCheckedIn={handleCheckedIn} />
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
