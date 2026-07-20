"use client";
import { useEffect, useState, useRef } from "react";
import { getMe } from "@/lib/api/auth";
import { useRouter } from "next/navigation";
import {
  getPatients,
  createPatient,
  updatePatient,
  importPatientsFromExcel,
  downloadPatientsCsv,
  downloadRecordsCsv,
  anonymizePatient,
} from "@/lib/api/patients";
import { Patient } from "@/types";
import { Search, Plus, X } from "lucide-react";

const PAGE_SIZE = 20;

export default function PatientManagementPanel() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
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
  const [editForm, setEditForm] = useState({ name: "", birth_date: "", gender: "", phone: "", rrn: "" });
  const [editLoading, setEditLoading] = useState(false);

  const [anonymizeTarget, setAnonymizeTarget] = useState<Patient | null>(null);
  const [anonymizeLoading, setAnonymizeLoading] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [downloadTarget, setDownloadTarget] = useState<"patient_list" | "medical_records" | null>(null);
  const [downloadReason, setDownloadReason] = useState("");
  const [downloadLoading, setDownloadLoading] = useState(false);
  const excelInputRef = useRef<HTMLInputElement | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  function getPageNumbers(current: number, total: number): (number | "...")[] {
    const pages = new Set<number>();
    pages.add(1);
    pages.add(total);
    for (let i = current - 2; i <= current + 2; i++) {
      if (i >= 1 && i <= total) pages.add(i);
    }
    const sorted = Array.from(pages).sort((a, b) => a - b);
    const result: (number | "...")[] = [];
    let prev = 0;
    for (const p of sorted) {
      if (prev && p - prev > 1) result.push("...");
      result.push(p);
      prev = p;
    }
    return result;
  }

  async function fetchPatients(pg: number, s: string) {
    const result = await getPatients(s, pg, PAGE_SIZE);
    setPatients(result.items);
    setTotalCount(result.total);
  }

  useEffect(() => {
    setLoading(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchPatients(page, search)
        .catch(console.error)
        .finally(() => setLoading(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [page, search]);

  useEffect(() => {
    getMe().then((me) => setIsOwner(me?.role === "owner"));
  }, []);

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
      await fetchPatients(page, search);
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
      await fetchPatients(page, search);
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
      rrn: "",
    });
  }

  async function handleEditSave(e: React.FormEvent) {
    e.preventDefault();
    if (!editTarget) return;
    setEditLoading(true);
    try {
      const { rrn, ...basicFields } = editForm;
      const updated = await updatePatient(editTarget.id, {
        ...basicFields,
        ...(rrn.trim() ? { rrn: rrn.trim() } : {}),
      });
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
    <div className="flex flex-col h-full bg-card border border-border rounded-lg overflow-hidden">
      {/* 상단 툴바: 좌측 검색, 우측 액션 버튼 그룹 */}
      <div className="border-b border-border px-4 pt-4 pb-3 flex flex-col gap-3">
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
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
        ) : patients.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">
            {search ? "검색 결과가 없습니다" : "등록된 환자가 없습니다"}
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="border-b border-border sticky top-0 bg-card">
                <tr className="text-xs text-subtext">
                  <th className="p-3 text-left">이름</th>
                  <th className="p-3 text-left">생년월일(나이)</th>
                  <th className="p-3 text-left">성별</th>
                  <th className="p-3 text-left">연락처</th>
                  <th className="p-3 text-left">등록일</th>
                  <th className="p-3 text-center">액션</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((patient) => {
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
            <div className="flex items-center justify-center gap-3 py-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-xs rounded-md cursor-pointer border border-border text-subtext hover:text-text hover:border-text transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                &lt; 이전
              </button>
              {getPageNumbers(page, totalPages).map((p, i) =>
                p === "..." ? (
                  <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-subtext">
                    ...
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`px-2.5 py-1.5 text-xs cursor-pointer rounded-md transition-colors ${
                      p === page
                        ? "bg-[#EF6600] text-white"
                        : "border border-border text-subtext hover:text-text"
                    }`}
                  >
                    {p}
                  </button>
                )
              )}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 cursor-pointer text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                다음 &gt;
              </button>
              <span className="text-xs text-subtext ml-2">총 {totalCount}명</span>
            </div>
          </>
        )}
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

      {/* 환자 정보 수정 모달 */}
      {editTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">
                환자 정보 수정
              </div>
              <button
                onClick={() => setEditTarget(null)}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleEditSave} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  이름 *
                </label>
                <input
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, name: e.target.value }))
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
                  value={editForm.birth_date}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, birth_date: e.target.value }))
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
                        name="edit-gender"
                        value={opt.value}
                        checked={editForm.gender === opt.value}
                        onChange={() =>
                          setEditForm((p) => ({ ...p, gender: opt.value }))
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
                  value={editForm.phone}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, phone: e.target.value }))
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
                  value={editForm.rrn}
                  onChange={(e) =>
                    setEditForm((p) => ({ ...p, rrn: formatRrn(e.target.value) }))
                  }
                  placeholder="변경할 때만 입력 (미입력 시 기존 값 유지)"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={editLoading || !editForm.name}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm mt-1 disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {editLoading ? "저장 중..." : "저장"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 익명화 확인 모달 */}
      {anonymizeTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm font-medium text-text mb-2">
              {anonymizeTarget.name} 환자를 익명화하시겠습니까?
            </div>
            <div className="text-xs text-red-500 mb-4">
              이 작업은 되돌릴 수 없습니다
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setAnonymizeTarget(null)}
                className="flex-1 border border-border text-text rounded-md py-2.5 text-sm hover:bg-bg transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleAnonymizeConfirm}
                disabled={anonymizeLoading}
                className="flex-1 bg-red-500 text-white rounded-md py-2.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {anonymizeLoading ? "처리 중..." : "확인"}
              </button>
            </div>
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
