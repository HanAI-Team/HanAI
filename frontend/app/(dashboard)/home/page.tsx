"use client";
import { getPatients } from "@/lib/api/patients";
import { getStats } from "@/lib/api/stats";
import { Patient } from "@/types";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Stats {
  total_patients: number;
  today_records: number;
  recent_records: { patient_name: string; recorded_at: string | null; chart_structured: string | null }[];
}

function parseDiagSummary(chart: string | null): string {
  if (!chart) return "-";
  const match = chart.match(/▶\s*한의학적 진단\s*\n([^\n▶]+)/);
  return match?.[1]?.trim() || "-";
}

export default function HomePage() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getPatients().catch(() => [] as Patient[]),
      getStats().catch(() => null),
    ]).then(([p, s]) => {
      setPatients(p);
      setStats(s);
    }).finally(() => setLoading(false));
  }, []);

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
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
        <div className="bg-card border border-border rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-medium text-text uppercase tracking-wide">환자 목록</div>
            <button
              onClick={() => router.push("/diagnosis")}
              className="text-xs text-subtext hover:text-[#EF6600] transition-colors"
            >
              진료 시작 →
            </button>
          </div>
          {loading ? (
            <div className="text-sm text-muted py-4 text-center">불러오는 중...</div>
          ) : patients.length === 0 ? (
            <div className="text-sm text-muted py-4 text-center">등록된 환자가 없습니다</div>
          ) : (
            patients.slice(0, 6).map((patient) => (
              <div
                key={patient.id}
                onClick={() => router.push("/diagnosis")}
                className="flex items-center gap-3 py-2.5 border-b border-border last:border-none cursor-pointer hover:bg-bg -mx-2 px-2 rounded transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div>
                  <div className="text-sm font-medium text-text">{patient.name}</div>
                  <div className="text-xs text-subtext">
                    {(() => {
                      const gender = ({ male: "남", female: "여", 남성: "남", 여성: "여" } as Record<string, string>)[patient.gender] ?? patient.gender;
                      let birthStr: string | null = null;
                      if (patient.birth_date) {
                        const birth = patient.birth_date.replace(/^\d{2}(\d{2})-(\d{2})-(\d{2})$/, "$1$2$3");
                        const today = new Date();
                        const b = new Date(patient.birth_date);
                        let a = today.getFullYear() - b.getFullYear();
                        if (today < new Date(today.getFullYear(), b.getMonth(), b.getDate())) a--;
                        birthStr = `${birth} (만 ${a}세)`;
                      }
                      return [gender, birthStr].filter(Boolean).join(", ") || patient.phone || "-";
                    })()}
                  </div>
                </div>
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-muted" />
              </div>
            ))
          )}
        </div>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => router.push("/diagnosis")}
            className="w-full bg-[#EF6600] text-white rounded-lg py-3.5 text-sm font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
          >
            🎙 새 진료 시작
          </button>
          <div className="bg-card border border-border rounded-lg p-5 flex-1">
            <div className="text-xs font-medium text-text uppercase tracking-wide mb-3">최근 진료 기록</div>
            {loading ? (
              <div className="text-sm text-muted text-center py-4">불러오는 중...</div>
            ) : !stats?.recent_records?.length ? (
              <div className="text-sm text-muted text-center py-4">아직 진료 기록이 없습니다</div>
            ) : (
              <div className="flex flex-col gap-2">
                {stats.recent_records.map((rec, i) => (
                  <div key={i} className="py-2 border-b border-border last:border-none">
                    <div className="text-sm font-medium text-text">{rec.patient_name}</div>
                    <div className="text-xs text-subtext mt-0.5">
                      {parseDiagSummary(rec.chart_structured)}
                    </div>
                    <div className="text-xs text-muted mt-0.5">
                      {rec.recorded_at
                        ? new Date(rec.recorded_at).toLocaleString("ko-KR", { month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })
                        : "-"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
