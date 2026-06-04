"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPatients } from "@/lib/api/patients";
import { getStats } from "@/lib/api/stats";
import { Patient } from "@/types";

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
        <h1 className="font-serif text-2xl text-[#232323]">오늘의 진료</h1>
        <p className="text-xs text-[#8A8480] mt-1">{today}</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {[
          { label: "전체 환자", value: loading ? "-" : stats?.total_patients ?? patients.length, sub: "명 등록" },
          { label: "오늘 진료", value: loading ? "-" : stats?.today_records ?? 0, sub: "건 완료" },
          { label: "최근 등록", value: loading ? "-" : patients.slice(-1)[0]?.name ?? "-", sub: "환자", small: true },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-[#D4CCC4] rounded-lg p-4">
            <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-2">{stat.label}</div>
            <div className={`font-light text-[#232323] ${stat.small ? "text-xl truncate" : "text-3xl"}`}>
              {stat.value}
            </div>
            <div className="h-0.5 bg-[#E4DDD5] rounded mt-3 mb-1">
              <div className="h-full bg-[#EF6600] rounded" style={{ width: i === 0 ? "100%" : "0%" }} />
            </div>
            <div className="text-xs text-[#B0AAA4]">{stat.sub}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
        <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-medium text-[#232323] uppercase tracking-wide">환자 목록</div>
            <button
              onClick={() => router.push("/diagnosis")}
              className="text-xs text-[#8A8480] hover:text-[#EF6600] transition-colors"
            >
              진료 시작 →
            </button>
          </div>
          {loading ? (
            <div className="text-sm text-[#B0AAA4] py-4 text-center">불러오는 중...</div>
          ) : patients.length === 0 ? (
            <div className="text-sm text-[#B0AAA4] py-4 text-center">등록된 환자가 없습니다</div>
          ) : (
            patients.slice(0, 6).map((patient) => (
              <div
                key={patient.id}
                onClick={() => router.push("/diagnosis")}
                className="flex items-center gap-3 py-2.5 border-b border-[#D4CCC4] last:border-none cursor-pointer hover:bg-[#F5F2EE] -mx-2 px-2 rounded transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div>
                  <div className="text-sm font-medium text-[#232323]">{patient.name}</div>
                  <div className="text-xs text-[#8A8480]">
                    {[
                      patient.gender === "male" ? "남" : patient.gender === "female" ? "여" : patient.gender,
                      patient.birth_date ? patient.birth_date.replace(/^\d{2}(\d{2})-(\d{2})-(\d{2})$/, "$1$2$3") : null,
                    ].filter(Boolean).join(", ") || patient.phone || "-"}
                  </div>
                </div>
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#B0AAA4]" />
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
          <div className="bg-white border border-[#D4CCC4] rounded-lg p-5 flex-1">
            <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-3">최근 진료 기록</div>
            {loading ? (
              <div className="text-sm text-[#B0AAA4] text-center py-4">불러오는 중...</div>
            ) : !stats?.recent_records?.length ? (
              <div className="text-sm text-[#B0AAA4] text-center py-4">아직 진료 기록이 없습니다</div>
            ) : (
              <div className="flex flex-col gap-2">
                {stats.recent_records.map((rec, i) => (
                  <div key={i} className="py-2 border-b border-[#D4CCC4] last:border-none">
                    <div className="text-sm font-medium text-[#232323]">{rec.patient_name}</div>
                    <div className="text-xs text-[#8A8480] mt-0.5">
                      {parseDiagSummary(rec.chart_structured)}
                    </div>
                    <div className="text-xs text-[#B0AAA4] mt-0.5">
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
