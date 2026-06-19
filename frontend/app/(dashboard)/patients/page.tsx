"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { getPatients, createPatient, importPatientsFromExcel } from "@/lib/api/patients";
import { Patient } from "@/types";
import { Search, Plus, ChevronRight, X } from "lucide-react";

const PAGE_SIZE = 20;

export default function PatientsPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    name: "",
    birth_date: "",
    gender: "",
    phone: "",
  });
  const [addLoading, setAddLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const excelInputRef = useRef<HTMLInputElement | null>(null);

  const filtered = patients.filter((p) => p.name.includes(search));
  const displayed = filtered.slice(0, page * PAGE_SIZE);
  const hasMore = filtered.length > page * PAGE_SIZE;

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore) setPage((p) => p + 1);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore]);

  function patientSubtext(p: Patient) {
    const gender = p.gender === "M" ? "남" : p.gender === "F" ? "여" : "";
    const birth = p.birth_date;
    const age = birth
      ? `${new Date().getFullYear() - new Date(birth).getFullYear()}세`
      : "";
    const parts = [
      gender,
      birth && age ? `${birth} (${age})` : birth,
    ].filter(Boolean);
    return parts.join(", ") || p.phone || "-";
  }

  async function handleExcelImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImportLoading(true);
    try {
      const result = await importPatientsFromExcel(file);
      setImportResult(result);
      const updated = await getPatients();
      setPatients(updated);
    } catch {
      setErrorMessage("엑셀 파일 가져오기에 실패했습니다.");
    } finally {
      setImportLoading(false);
    }
  }

  async function handleAddPatient(e: React.FormEvent) {
    e.preventDefault();
    setAddLoading(true);
    try {
      const created: Patient = await createPatient(newPatient);
      const updated = await getPatients();
      setPatients(updated);
      setShowAddModal(false);
      setNewPatient({ name: "", birth_date: "", gender: "", phone: "" });
      router.push(`/diagnosis?patientId=${created.id}`);
    } catch (e: any) {
      setErrorMessage(e.message || "환자 등록에 실패했습니다.");
    } finally {
      setAddLoading(false);
    }
  }

  return (
    <div className="flex flex-col bg-bg" style={{ minHeight: "100%" }}>
      {/* 검색 헤더 */}
      <div className="bg-card border-b border-border px-4 pt-4 pb-3 flex flex-col gap-3 sticky top-0 z-10">
        <div className="text-sm font-medium text-text">환자 목록</div>
        <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2">
          <Search className="w-3.5 h-3.5 text-muted flex-shrink-0" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="이름 검색..."
            className="flex-1 bg-transparent text-xs text-text outline-none"
          />
        </div>
      </div>

      {/* 환자 목록 */}
      <div className="flex-1">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">
            불러오는 중...
          </div>
        ) : displayed.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">
            {search ? "검색 결과가 없습니다" : "등록된 환자가 없습니다"}
          </div>
        ) : (
          <>
            {displayed.map((patient) => (
              <button
                key={patient.id}
                onClick={() =>
                  router.push(`/diagnosis?patientId=${patient.id}`)
                }
                className="w-full flex items-center gap-3 px-4 py-3.5 border-b border-border bg-card hover:bg-bg transition-colors text-left"
              >
                <div className="w-9 h-9 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text">
                    {patient.name}
                  </div>
                  <div className="text-xs text-subtext mt-0.5">
                    {patientSubtext(patient)}
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-muted flex-shrink-0" />
              </button>
            ))}
            <div ref={sentinelRef} className="h-2" />
          </>
        )}
      </div>

      {/* 하단 버튼 */}
      <div className="p-4 bg-card border-t border-border sticky bottom-0 flex flex-col gap-2">
        <button
          onClick={() => setShowAddModal(true)}
          className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" /> 신규 환자 등록
        </button>
        <button
          onClick={() => excelInputRef.current?.click()}
          disabled={importLoading}
          className="w-full border border-border text-text rounded-md py-3 text-sm flex items-center justify-center gap-2 hover:bg-bg transition-colors disabled:opacity-50"
        >
          {importLoading ? "가져오는 중..." : "📂 엑셀로 환자 가져오기"}
        </button>
        <input
          ref={excelInputRef}
          type="file"
          accept=".xls,.xlsx"
          className="hidden"
          onChange={handleExcelImport}
        />
      </div>

      {/* 신규 환자 등록 모달 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">
                신규 환자 등록
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleAddPatient} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  이름 *
                </label>
                <input
                  value={newPatient.name}
                  onChange={(e) =>
                    setNewPatient((p) => ({ ...p, name: e.target.value }))
                  }
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  생년월일
                </label>
                <input
                  type="date"
                  value={newPatient.birth_date}
                  onChange={(e) =>
                    setNewPatient((p) => ({ ...p, birth_date: e.target.value }))
                  }
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  성별
                </label>
                <div className="flex gap-4">
                  {[
                    { value: "M", label: "남" },
                    { value: "F", label: "여" },
                  ].map((opt) => (
                    <label
                      key={opt.value}
                      className="flex items-center gap-1.5 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="gender"
                        value={opt.value}
                        checked={newPatient.gender === opt.value}
                        onChange={() =>
                          setNewPatient((p) => ({ ...p, gender: opt.value }))
                        }
                        className="accent-[#EF6600]"
                      />
                      <span className="text-sm text-text">{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  전화번호
                </label>
                <input
                  value={newPatient.phone}
                  onChange={(e) =>
                    setNewPatient((p) => ({ ...p, phone: e.target.value }))
                  }
                  placeholder="010-0000-0000"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={addLoading || !newPatient.name}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm mt-1 disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {addLoading ? "등록 중..." : "등록"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 엑셀 가져오기 결과 모달 */}
      {importResult && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-base font-semibold text-text mb-2">가져오기 완료</div>
            <div className="text-sm text-subtext mb-4">
              <span className="text-[#EF6600] font-medium">{importResult.inserted}명</span> 등록됨
              {importResult.skipped > 0 && ` · ${importResult.skipped}건 건너뜀`}
            </div>
            <button
              onClick={() => setImportResult(null)}
              className="bg-[#EF6600] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition-opacity"
            >
              확인
            </button>
          </div>
        </div>
      )}

      {/* 에러 모달 */}
      {errorMessage && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm text-text mb-4">{errorMessage}</div>
            <button
              onClick={() => setErrorMessage(null)}
              className="bg-[#EF6600] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition-opacity"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
