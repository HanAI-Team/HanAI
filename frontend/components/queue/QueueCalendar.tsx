"use client";
import { getQueueMonthlyCountsAPI } from "@/lib/api/queue";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function toDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

interface QueueCalendarProps {
  selectedDate: string;
  onSelectDate: (date: string) => void;
}

export default function QueueCalendar({ selectedDate, onSelectDate }: QueueCalendarProps) {
  const [viewMonth, setViewMonth] = useState(() => {
    const d = new Date(`${selectedDate}T00:00:00`);
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [counts, setCounts] = useState<Record<string, number>>({});

  // 날짜별 접수 인원수: 월간 집계 API 한 번으로 조회한다.
  useEffect(() => {
    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();

    let cancelled = false;
    getQueueMonthlyCountsAPI(year, month + 1)
      .then((counts) => {
        if (cancelled) return;
        setCounts(counts);
      })
      .catch(() => {
        if (!cancelled) setCounts({});
      });

    return () => {
      cancelled = true;
    };
  }, [viewMonth]);

  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const todayStr = toDateStr(new Date());

  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setViewMonth(new Date(year, month - 1, 1))}
          className="text-subtext hover:text-text p-1"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div className="text-sm font-medium text-text">
          {year}년 {month + 1}월
        </div>
        <button
          onClick={() => setViewMonth(new Date(year, month + 1, 1))}
          className="text-subtext hover:text-text p-1"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center mb-1">
        {WEEKDAYS.map((w) => (
          <div key={w} className="text-[10px] text-muted py-1">
            {w}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (day === null) return <div key={`blank-${i}`} />;
          const dateStr = toDateStr(new Date(year, month, day));
          const isSelected = dateStr === selectedDate;
          const isToday = dateStr === todayStr;
          const count = counts[dateStr] || 0;
          return (
            <button
              key={dateStr}
              onClick={() => onSelectDate(dateStr)}
              className={`flex flex-col items-center justify-center rounded-md py-1.5 text-xs transition-colors cursor-pointer ${
                isSelected
                  ? "bg-[#EF6600] text-white"
                  : isToday
                    ? "border border-[#EF6600] text-text"
                    : "text-text hover:bg-fill"
              }`}
            >
              <span className="text-[10px] leading-none">{day}</span>
              {count > 0 && (
                <span className={`text-[8px] leading-none mt-1 ${isSelected ? "text-white/80" : "text-[#EF6600]"}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
