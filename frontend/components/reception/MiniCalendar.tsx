"use client";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface MiniCalendarProps {
  year: number;
  month: number; // 1~12
  counts: Record<string, number>; // "2026-07-14" -> 4
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  onMonthChange: (year: number, month: number) => void;
}

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function toDateStr(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export default function MiniCalendar({
  year,
  month,
  counts,
  selectedDate,
  onSelectDate,
  onMonthChange,
}: MiniCalendarProps) {
  const firstDayOfWeek = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const todayStr = new Date().toISOString().slice(0, 10);

  const cells: (number | null)[] = [
    ...Array(firstDayOfWeek).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  function prevMonth() {
    if (month === 1) onMonthChange(year - 1, 12);
    else onMonthChange(year, month - 1);
  }

  function nextMonth() {
    if (month === 12) onMonthChange(year + 1, 1);
    else onMonthChange(year, month + 1);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={prevMonth}
          className="p-1 text-subtext hover:text-text transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        <div className="text-xs font-medium text-text">
          {year}년 {month}월
        </div>
        <button
          onClick={nextMonth}
          className="p-1 text-subtext hover:text-text transition-colors"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {WEEKDAYS.map((w) => (
          <div key={w} className="text-[9px] text-muted text-center py-0.5">
            {w}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((day, i) => {
          if (day === null) return <div key={`empty-${i}`} />;
          const dateStr = toDateStr(year, month, day);
          const count = counts[dateStr] || 0;
          const isSelected = selectedDate === dateStr;
          const isToday = dateStr === todayStr;
          const isFuture = dateStr > todayStr;
          return (
            <button
              key={dateStr}
              onClick={() => onSelectDate(dateStr)}
              className={`flex flex-col items-center justify-center rounded-md py-1 transition-colors ${
                isSelected
                  ? "bg-[#EF6600] text-white"
                  : isToday
                    ? "bg-fill text-text"
                    : "text-text hover:bg-fill"
              }`}
            >
              <span className="text-[10px]">{day}</span>
              <span
                className={`text-[8px] leading-tight ${
                  isSelected ? "text-white/80" : count > 0 ? "text-[#EF6600]" : "text-muted"
                }`}
              >
                {isFuture ? "-" : `${count}명`}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
