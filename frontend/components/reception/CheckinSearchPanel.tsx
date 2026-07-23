"use client";
import { useEffect, useRef, useState } from "react";
import { Search, Plus, X } from "lucide-react";
import { createPatient, getPatients } from "@/lib/api/patients";
import { checkinPatient, QueueItem } from "@/lib/api/queue";
import { Patient } from "@/types";

interface CheckinSearchPanelProps {
  onCheckedIn: (item: QueueItem) => void;
}

function calcAge(birthDate?: string | null): number | null {
  if (!birthDate) return null;
  return new Date().getFullYear() - new Date(birthDate).getFullYear();
}

function genderLabel(g?: string | null): string {
  return g === "M" ? "남" : g === "F" ? "여" : "";
}

export default function CheckinSearchPanel({ onCheckedIn }: CheckinSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Patient[]>([]);
  const [searching, setSearching] = useState(false);
  const searchTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [confirmTarget, setConfirmTarget] = useState<Patient | null>(null);
  const [checkingIn, setCheckingIn] = useState(false);
  const [error, setError] = useState("");

  const [showRegister, setShowRegister] = useState(false);
  const [registerForm, setRegisterForm] = useState({ name: "", birth_date: "", gender: "", phone: "" });
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setSearching(true);
    searchTimerRef.current = setTimeout(() => {
      getPatients(query)
        .then((result) => setResults(result.items))
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [query]);

  async function handleConfirmCheckin() {
    if (!confirmTarget) return;
    setCheckingIn(true);
    setError("");
    try {
      const item = await checkinPatient(confirmTarget.id);
      onCheckedIn(item);
      setConfirmTarget(null);
      setQuery("");
      setResults([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "접수 처리에 실패했습니다.");
    } finally {
      setCheckingIn(false);
    }
  }

  async function handleRegisterSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRegistering(true);
    setError("");
    try {
      const created: Patient = await createPatient(registerForm);
      setShowRegister(false);
      setRegisterForm({ name: "", birth_date: "", gender: "", phone: "" });
      setConfirmTarget(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "환자 등록에 실패했습니다.");
    } finally {
      setRegistering(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-card border border-border rounded-lg overflow-hidden">
      <div className="border-b border-border px-5 py-4 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2 flex-1">
          <Search className="w-3.5 h-3.5 text-muted flex-shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="환자 이름을 검색하세요"
            className="flex-1 bg-transparent text-sm text-text outline-none"
          />
        </div>
        <button
          onClick={() => setShowRegister(true)}
          className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity flex-shrink-0"
        >
          <Plus className="w-3.5 h-3.5" /> 신규 환자 등록
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {!query.trim() ? (
          <div className="text-sm text-muted text-center py-16">환자 이름을 검색하세요</div>
        ) : searching ? (
          <div className="text-sm text-muted text-center py-16">검색 중...</div>
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16">
            <div className="text-sm text-muted">&apos;{query}&apos;와 일치하는 환자가 없습니다</div>
            <button
              onClick={() => {
                setRegisterForm((p) => ({ ...p, name: query }));
                setShowRegister(true);
              }}
              className="text-xs text-[#EF6600] hover:underline"
            >
              + 신규 환자로 등록
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {results.map((p) => {
              const age = calcAge(p.birth_date);
              return (
                <button
                  key={p.id}
                  onClick={() => setConfirmTarget(p)}
                  className="flex items-center justify-between px-3 py-2.5 rounded-md border border-border hover:border-[#EF6600] hover:bg-fill transition-colors text-left"
                >
                  <span className="text-sm font-medium text-text">{p.name}</span>
                  <span className="text-xs text-subtext">
                    {[age !== null ? `${age}세` : null, genderLabel(p.gender) || null, p.birth_date || null]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {confirmTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl p-5">
            <div className="text-sm text-text mb-1">
              <span className="font-medium text-[#EF6600]">{confirmTarget.name}</span>님, 오늘 접수하시겠습니까?
            </div>
            {error && <div className="text-xs text-red-500 mt-2">{error}</div>}
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  setConfirmTarget(null);
                  setError("");
                }}
                className="flex-1 border border-border rounded-md py-2 text-sm text-subtext hover:text-text transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleConfirmCheckin}
                disabled={checkingIn}
                className="flex-1 bg-[#EF6600] text-white rounded-md py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-colors"
              >
                {checkingIn ? "처리 중..." : "접수"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showRegister && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">신규 환자 등록</div>
              <button
                onClick={() => setShowRegister(false)}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleRegisterSubmit} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">이름 *</label>
                <input
                  value={registerForm.name}
                  onChange={(e) => setRegisterForm((p) => ({ ...p, name: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">생년월일</label>
                <input
                  type="date"
                  value={registerForm.birth_date}
                  onChange={(e) => setRegisterForm((p) => ({ ...p, birth_date: e.target.value }))}
                  min="1900-01-01"
                  max={new Date().toISOString().slice(0, 10)}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">성별</label>
                <div className="flex gap-4">
                  {[
                    { value: "M", label: "남" },
                    { value: "F", label: "여" },
                  ].map((opt) => (
                    <label key={opt.value} className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="gender"
                        value={opt.value}
                        checked={registerForm.gender === opt.value}
                        onChange={() => setRegisterForm((p) => ({ ...p, gender: opt.value }))}
                        className="accent-[#EF6600]"
                      />
                      <span className="text-sm text-text">{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">전화번호</label>
                <input
                  value={registerForm.phone}
                  onChange={(e) => setRegisterForm((p) => ({ ...p, phone: e.target.value }))}
                  placeholder="010-0000-0000"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              {error && <div className="text-xs text-red-500">{error}</div>}
              <div className="flex gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => setShowRegister(false)}
                  className="flex-1 border border-border rounded-md py-2 text-sm text-subtext hover:text-text transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={registering}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-colors"
                >
                  {registering ? "등록 중..." : "등록"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
