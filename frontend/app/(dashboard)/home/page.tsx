"use client";
import { getPatients } from "@/lib/api/patients";
import { checkinPatient, getTodayQueue, QueueItem, updateQueueStatus } from "@/lib/api/queue";
import { getStats } from "@/lib/api/stats";
import { Patient } from "@/types";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Stats {
  total_patients: number;
  today_records: number;
  recent_records: { patient_id: string; record_id: string; patient_name: string; recorded_at: string | null; chart_structured: string | null }[];
}

export default function HomePage() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [todayQueue, setTodayQueue] = useState<QueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    Promise.all([
      getPatients().catch(() => [] as Patient[]),
      getStats().catch(() => null),
      getTodayQueue().catch(() => [] as QueueItem[]),
    ]).then(([p, s, q]) => {
      setPatients(p);
      setStats(s);
      setTodayQueue(q);
    }).finally(() => {
      setLoading(false);
      setQueueLoading(false);
    });
  }, []);

  // 접수 목록 정렬: done 나중, 같은 status면 checked_in_at 오름차순
  const sortedQueue = [...todayQueue].sort((a, b) => {
    const aDone = a.status === "done" ? 1 : 0;
    const bDone = b.status === "done" ? 1 : 0;
    if (aDone !== bDone) return aDone - bDone;
    return new Date(a.checked_in_at).getTime() - new Date(b.checked_in_at).getTime();
  });

  // 환자 검색 필터
  const filteredPatients = patients.filter((p) => p.name.includes(search)).slice(0, 6);

  const today = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl text-text">오늘의 진료</h1>
        <p className="text-xs text-subtext mt-1">{today}</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {[
          { label: "전체 환자", value: loading ? "-" : stats?.total_patients ?? patients.length, sub: "명 등록" },
          { label: "오늘 진료", value: loading ? "-" : stats?.today_records ?? 0, sub: "건 완료" },
          { label: "최근 등록", value: loading ? "-" : patients.slice(-1)[0]?.name ?? "-", sub: "환자", small: true },
        ].map((stat, i) => (
          <div key={i} className="bg-card border border-border rounded-lg p-4">
            <div className="text-xs text-subtext uppercase tracking-wide mb-2">{stat.label}</div>
            <div className={`font-light text-text ${stat.small ? "text-xl truncate" : "text-3xl"}`}>
              {stat.value}
            </div>
            <div className="h-0.5 bg-fill rounded mt-3 mb-1">
              <div className="h-full bg-[#EF6600] rounded" style={{ width: i === 0 ? "100%" : "0%" }} />
            </div>
            <div className="text-xs text-muted">{stat.sub}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <div className="bg-card border border-border rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="text-xs font-medium text-text uppercase tracking-wide">오늘 접수</div>
            <span className="text-xs text-muted bg-fill rounded-full px-1.5 py-0.5">{todayQueue.length}</span>
          </div>
          {queueLoading ? (
            <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto my-4" />
          ) : sortedQueue.length === 0 ? (
            <div className="text-xs text-muted text-center py-4">오늘 접수된 환자가 없습니다</div>
          ) : (
            sortedQueue.map((item) => (
              <div
                key={item.id}
                onClick={() => router.push(`/diagnosis?patientId=${item.patient_id}`)}
                className="flex items-center justify-between gap-3 py-2.5 border-b border-border last:border-none cursor-pointer hover:bg-bg -mx-2 px-2 rounded transition-colors"
              >
                <div>
                  <div className="text-sm font-medium text-text">{item.patient_name}</div>
                  <div className="text-xs text-subtext mt-0.5">
                    {new Date(item.checked_in_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      item.status === "waiting"
                        ? "bg-muted/20 text-muted"
                        : item.status === "in_progress"
                          ? "bg-[#EF6600]/15 text-[#EF6600]"
                          : "bg-green-500/15 text-green-500"
                    }`}
                  >
                    {item.status === "waiting" ? "대기" : item.status === "in_progress" ? "진료중" : "완료"}
                  </span>
                  {item.status !== "done" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        updateQueueStatus(item.id, "done")
                          .then((updated) => {
                            setTodayQueue((prev) =>
                              prev.map((q) => (q.id === updated.id ? updated : q)),
                            );
                          })
                          .catch(console.error);
                      }}
                      className="text-xs text-subtext hover:text-[#EF6600] border border-border rounded px-1.5 py-0.5 transition-all"
                    >
                      ✓
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
        <div className="bg-card border border-border rounded-lg p-5">
          <div className="text-xs font-medium text-text uppercase tracking-wide mb-3">환자 접수</div>
          <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2 mb-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="이름 검색..."
              className="flex-1 bg-transparent text-xs text-text outline-none"
            />
          </div>
          {loading ? (
            <div className="text-sm text-muted py-4 text-center">불러오는 중...</div>
          ) : filteredPatients.length === 0 ? (
            <div className="text-sm text-muted py-4 text-center">환자가 없습니다</div>
          ) : (
            filteredPatients.map((patient) => (
              <div
                key={patient.id}
                onClick={() => {
                  checkinPatient(patient.id)
                    .then((item) => setTodayQueue((prev) => [...prev, item]))
                    .catch(console.error);
                }}
                className="flex flex-col py-2.5 border-b border-border last:border-none cursor-pointer hover:bg-bg -mx-2 px-2 rounded transition-colors"
              >
                <div className="text-sm font-medium text-text">{patient.name}</div>
                <div className="text-xs text-subtext">{patient.birth_date || "-"}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
