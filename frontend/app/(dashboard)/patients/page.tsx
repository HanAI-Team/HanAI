"use client";
import { useEffect, useState, useRef } from "react";
import {getMe} from "@/lib/api/auth";
import { useRouter } from "next/navigation";
import {
  getPatients,
  createPatient,
  updatePatient,
  importPatientsFromExcel,
  downloadPatientsCsv,
  downloadRecordsCsv,
  anonymizePatient
} from "@/lib/api/patients";
import { Patient } from "@/types";
import { Search, Plus, X, ChevronUp, ChevronDown } from "lucide-react";

const PAGE_SIZE = 20;

type SortField = "name" | "birth_date" | "phone" | "created_at";

export default function PatientsPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [isOwner, setIsOwner] = useState(false);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    name: "",
    birth_date: "",
    gender: "",
    phone: "",
    rrn: "",
  });
  const [addLoading, setAddLoading] = useState(false);

  const [editTarget, setEditTarget] = useState<Patient | null>(null);
  const [editForm, setEditForm] = useState({ name: "", birth_date: "", gender: "", phone: "" });
  const [editLoading, setEditLoading] = useState(false);

  const [anonymizeTarget, setAnonymizeTarget] = useState<Patient | null>(null);
  const [anonymizeLoading, setAnonymizeLoading] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [downloadTarget, setDownloadTarget] = useState<"patient_list" | "medical_records" | null>(null);
  const [downloadReason, setDownloadReason] = useState("");
  const [downloadLoading, setDownloadLoading] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const excelInputRef = useRef<HTMLInputElement | null>(null);

  const filtered = patients.filter((p) => p.name.includes(search));
  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDir === "asc" ? 1 : -1;
    switch (sortField) {
      case "birth_date":
        return (a.birth_date || "").localeCompare(b.birth_date || "") * dir;
      case "phone":
        return (a.phone || "").localeCompare(b.phone || "") * dir;
      case "created_at":
        return (a.created_at || "").localeCompare(b.created_at || "") * dir;
      default:
        return a.name.localeCompare(b.name, "ko") * dir;
    }
  });
  const displayed = sorted.slice(0, page * PAGE_SIZE);
  const hasMore = sorted.length > page * PAGE_SIZE;

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    getMe().then((me) => setIsOwner(me?.role === "owner"));
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

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return null;
    return sortDir === "asc" ? (
      <ChevronUp className="w-3 h-3 inline ml-0.5" />
    ) : (
      <ChevronDown className="w-3 h-3 inline ml-0.5" />
    );
  }

  function calcAge(birth?: string) {
    if (!birth) return null;
    return new Date().getFullYear() - new Date(birth).getFullYear();
  }

  function genderLabel(g?: string) {
    return g === "M" ? "남" : g === "F" ? "여" : "-";
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

  async function handleDownloadCsv(e: React.FormEvent) {
    e.preventDefault();
    if (!downloadTarget || !downloadReason.trim()) return;
    setDownloadLoading(true);
    try {
      if (downloadTarget === "patient_list") {
        await downloadPatientsCsv(downloadReason.trim());
      } else {
        await downloadRecordsCsv(downloadReason.trim());
      }
      setDownloadTarget(null);
      setDownloadReason("");
    } catch (e: any) {
      setErrorMessage(e.message || "CSV 다운로드에 실패했습니다.");
    } finally {
      setDownloadLoading(false);
    }
  }

  function formatRrn(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 13);
    if (digits.length <= 6) return digits;
    return `${digits.slice(0, 6)}-${digits.slice(6)}`;
  }

  async function handleAddPatient(e: React.FormEvent) {
    e.preventDefault();
    setAddLoading(true);
    try {
      const { rrn, ...basicFields } = newPatient;
      const created: Patient = await createPatient(basicFields);
      if (rrn.trim()) {
        await updatePatient(created.id, { rrn: rrn.trim() });
      }
      const updated = await getPatients();
      setPatients(updated);
      setShowAddModal(false);
      setNewPatient({ name: "", birth_date: "", gender: "", phone: "", rrn: "" });
      router.push(`/diagnosis?patientId=${created.id}`);
    } catch (e: any) {
      setErrorMessage(e.message || "환자 등록에 실패했습니다.");
    } finally {
      setAddLoading(false);
    }
  }

  function openEditModal(p: Patient) {
    setEditTarget(p);
    setEditForm({
      name: p.name,
      birth_date: p.birth_date || "",
      gender: p.gender || "",
      phone: p.phone || "",
    });
  }

  async function handleEditSave(e: React.FormEvent) {
    e.preventDefault();
    if (!editTarget) return;
    setEditLoading(true);
    try {
      const updated = await updatePatient(editTarget.id, editForm);
      setPatients((prev) =>
        prev.map((p) => (p.id === editTarget.id ? { ...p, ...updated } : p))
      );
      setEditTarget(null);
    } catch (e: any) {
      setErrorMessage(e.message || "환자 정보 수정에 실패했습니다.");
    } finally {
      setEditLoading(false);
    }
  }

  async function handleAnonymizeConfirm() {
    if (!anonymizeTarget) return;
    setAnonymizeLoading(true);
    try {
      const updated = await anonymizePatient(anonymizeTarget.id);
      setPatients((prev) =>
        prev.map((p) => (p.id === anonymizeTarget.id ? { ...p, ...updated } : p))
      );
      setAnonymizeTarget(null);
    } catch (e: any) {
      setErrorMessage(e.message || "익명화 처리에 실패했습니다.");
    } finally {
      setAnonymizeLoading(false);
    }
  }

  return (
    <div className="flex flex-col bg-bg" style={{ minHeight: "100%" }}>
      {/* 상단 툴바: 좌측 검색, 우측 액션 버튼 그룹 */}
      <div className="bg-card border-b border-border px-4 pt-4 pb-3 flex flex-col gap-3 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2 flex-1 min-w-[160px] max-w-xs">
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
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity"
            >
              <Plus className="w-3.5 h-3.5" /> 신규 환자 등록
            </button>
            <button
              onClick={() => excelInputRef.current?.click()}
              disabled={importLoading}
              className="border border-border text-text rounded-md px-3 py-2 text-xs hover:bg-bg transition-colors disabled:opacity-50"
            >
              {importLoading ? "가져오는 중..." : "엑셀로 환자 가져오기"}
            </button>
            <button
              onClick={() => setDownloadTarget("patient_list")}
              className="border border-border text-text rounded-md px-3 py-2 text-xs hover:bg-bg transition-colors"
            >
              환자 목록 CSV
            </button>
            <button
              onClick={() => setDownloadTarget("medical_records")}
              className="border border-border text-text rounded-md px-3 py-2 text-xs hover:bg-bg transition-colors"
            >
              진료기록 CSV
            </button>
          </div>
        </div>
        <input
          ref={excelInputRef}
          type="file"
          accept=".xls,.xlsx"
          className="hidden"
          onChange={handleExcelImport}
        />
      </div>

      {/* 환자 목록 테이블 */}
      <div className="flex-1 overflow-x-auto">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
        ) : displayed.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">
            {search ? "검색 결과가 없습니다" : "등록된 환자가 없습니다"}
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr className="text-xs text-subtext">
                  <th
                    onClick={() => toggleSort("name")}
                    className="p-3 text-left cursor-pointer select-none hover:text-text"
                  >
                    이름 <SortIcon field="name" />
                  </th>
                  <th
                    onClick={() => toggleSort("birth_date")}
                    className="p-3 text-left cursor-pointer select-none hover:text-text"
                  >
                    생년월일(나이) <SortIcon field="birth_date" />
                  </th>
                  <th className="p-3 text-left">성별</th>
                  <th
                    onClick={() => toggleSort("phone")}
                    className="p-3 text-left cursor-pointer select-none hover:text-text"
                  >
                    연락처 <SortIcon field="phone" />
                  </th>
                  <th
                    onClick={() => toggleSort("created_at")}
                    className="p-3 text-left cursor-pointer select-none hover:text-text"
                  >
                    등록일 <SortIcon field="created_at" />
                  </th>
                  <th className="p-3 text-center">액션</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((patient) => {
                  const anonymized = patient.name === "익명";
                  const age = calcAge(patient.birth_date);
                  return (
                    <tr
                      key={patient.id}
                      className={`border-t border-border hover:bg-fill transition-colors ${
                        anonymized ? "opacity-50" : ""
                      }`}
                    >
                      <td className="p-3 text-text font-medium">{patient.name}</td>
                      <td className="p-3 text-subtext">
                        {patient.birth_date ? `${patient.birth_date}${age !== null ? ` (${age}세)` : ""}` : "-"}
                      </td>
                      <td className="p-3 text-subtext">{genderLabel(patient.gender)}</td>
                      <td className="p-3 text-subtext">{patient.phone || "-"}</td>
                      <td className="p-3 text-subtext">{patient.created_at?.slice(0, 10) || "-"}</td>
                      <td className="p-3">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => router.push(`/diagnosis?patientId=${patient.id}`)}
                            className="px-2.5 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors"
                          >
                            진료 시작
                          </button>
                          <button
                            onClick={() => openEditModal(patient)}
                            disabled={anonymized}
                            className="px-2.5 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            수정
                          </button>
                          {isOwner && (
                            <button
                              onClick={() => setAnonymizeTarget(patient)}
                              disabled={anonymized}
                              className="px-2.5 py-1 text-xs rounded-md border border-amber-500/40 text-amber-600 hover:bg-amber-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              익명화
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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
        <div className="flex gap-2">
          <button
            onClick={() => setDownloadTarget("patient_list")}
            className="flex-1 border border-border text-text rounded-md py-2.5 text-xs hover:bg-bg transition-colors"
          >
            환자 목록 CSV 다운로드
          </button>
          <button
            onClick={() => setDownloadTarget("medical_records")}
            className="flex-1 border border-border text-text rounded-md py-2.5 text-xs hover:bg-bg transition-colors"
          >
            진료기록 CSV 다운로드
          </button>
        </div>
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
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  주민번호
                </label>
                <input
                  value={newPatient.rrn}
                  onChange={(e) =>
                    setNewPatient((p) => ({ ...p, rrn: formatRrn(e.target.value) }))
                  }
                  placeholder="000000-0000000"
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

      {/* CSV 다운로드 사유 입력 모달 */}
      {downloadTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">다운로드 사유 입력</div>
              <button
                onClick={() => {
                  setDownloadTarget(null);
                  setDownloadReason("");
                }}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleDownloadCsv} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">사유 *</label>
                <textarea
                  value={downloadReason}
                  onChange={(e) => setDownloadReason(e.target.value)}
                  required
                  minLength={1}
                  rows={3}
                  placeholder="다운로드 사유를 입력하세요"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors resize-none"
                />
              </div>
              <div className="flex gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setDownloadTarget(null);
                    setDownloadReason("");
                  }}
                  className="flex-1 border border-border text-text rounded-md py-2.5 text-sm hover:bg-bg transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={downloadLoading || !downloadReason.trim()}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
                >
                  {downloadLoading ? "다운로드 중..." : "확인"}
                </button>
              </div>
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
