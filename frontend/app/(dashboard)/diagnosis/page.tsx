"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getPatients,
  createPatient,
  getPatientRecords,
  saveRecord,
  updatePatient,
  deleteRecord,
} from "@/lib/api/patients";
import {
  uploadAndAnalyze,
  askDiagnosis,
  diagnoseText,
} from "@/lib/api/diagnosis";
import { Patient, DiagnosisResult } from "@/types";
import {
  Search,
  Mic,
  Square,
  FolderOpen,
  Sparkles,
  Clipboard,
  Check,
  TriangleAlert,
  Save,
  CircleCheck,
  Printer,
  Download,
  MessageCircle,
  Stethoscope,
  Leaf,
  MapPin,
  User,
  ChevronUp,
  ChevronDown,
  X,
  Plus,
  Pencil,
  Trash2,
  type LucideIcon,
} from "lucide-react";

const PAGE_SIZE = 20;

export default function DiagnosisPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [activeTab, setActiveTab] = useState<
    "record" | "result" | "history" | "ask"
  >("record");
  const [isRecording, setIsRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [memo, setMemo] = useState("");
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    name: "",
    birth_date: "",
    gender: "",
    phone: "",
  });
  const [addLoading, setAddLoading] = useState(false);
  const [askQuestion, setAskQuestion] = useState("");
  const [askHistory, setAskHistory] = useState<
    { question: string; answer: string }[]
  >([]);
  const [askMode, setAskMode] = useState<"ask" | "diagnose">("ask");
  const [symptomText, setSymptomText] = useState("");
  const [records, setRecords] = useState<
    {
      id: string;
      recorded_at: string | null;
      chart_structured: string | null;
    }[]
  >([]);
  const [recordsLastFetchedFor, setRecordsLastFetchedFor] = useState<
    string | null
  >(null);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [expandedRecord, setExpandedRecord] = useState<string | null>(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [editPatient, setEditPatient] = useState<Patient | null>(null);
  const [editForm, setEditForm] = useState({ phone: "", memo: "" });
  const [editLoading, setEditLoading] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const filtered = patients.filter((p) => p.name.includes(search));
  const displayedPatients = filtered.slice(0, page * PAGE_SIZE);
  const hasMore = filtered.length > page * PAGE_SIZE;
  const recordsLoading =
    activeTab === "history" &&
    !!selectedPatient &&
    recordsLastFetchedFor !== selectedPatient.id;

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(console.error)
      .finally(() => setPatientsLoading(false));
  }, []);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !patientsLoading) {
        setPage((prev) => prev + 1);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, patientsLoading]);

  useEffect(() => {
    if (!selectedPatient) return;
    getPatientRecords(selectedPatient.id)
      .then((data) => {
        const sorted = [...data.records].sort((a, b) => {
          const da = a.recorded_at ? new Date(a.recorded_at).getTime() : 0;
          const db = b.recorded_at ? new Date(b.recorded_at).getTime() : 0;
          return db - da;
        });
        const latest = sorted[0];
        if (!latest?.chart_structured) return;
        const sections = parseChartSections(latest.chart_structured);
        if (!sections) return;
        setResult(mapSectionsToResult(sections, selectedPatient.id));
      })
      .catch(console.error);
  }, [selectedPatient]);

  useEffect(() => {
    if (activeTab !== "history" || !selectedPatient) return;
    const id = selectedPatient.id;
    getPatientRecords(id)
      .then((data) => {
        setRecords(data.records);
        setRecordsLastFetchedFor(id);
      })
      .catch(console.error);
  }, [activeTab, selectedPatient]);

  async function toggleRecording() {
    if (!isRecording) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioFile(
          new File([blob], "recording.webm", { type: "audio/webm" }),
        );
      };
      recorder.start();
      mediaRef.current = recorder;
      setIsRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } else {
      mediaRef.current?.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }

  function parseChartSections(
    text: string | null,
  ): Record<string, string> | null {
    if (!text) return null;
    const sections: Record<string, string> = {};
    const parts = text.split(/▶\s+/);
    for (const part of parts) {
      const lines = part.trim().split("\n");
      const title = lines[0]?.trim();
      const joined = lines.slice(1).join("\n");
      const content = (
        joined.includes("※") ? joined.slice(0, joined.indexOf("※")) : joined
      ).trim();
      if (title) sections[title] = content;
    }
    return Object.keys(sections).length > 0 ? sections : null;
  }

  function mapSectionsToResult(
    sections: Record<string, string>,
    patientId: string,
  ): DiagnosisResult {
    const diagLines = (sections["한의학적 진단"] ?? "")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const diagnosis = diagLines.find((l) => !l.startsWith("양방")) ?? "-";
    const westernLine = diagLines.find((l) => l.startsWith("양방"));
    const western_diagnosis = westernLine
      ? westernLine.replace(/^양방[^:]*:\s*/, "")
      : "-";

    const herbLines = (sections["한약 처방"] ?? "")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const prescription = herbLines[0] ?? "-";
    const herbs = herbLines
      .slice(1)
      .flatMap((l) => l.split(",").map((h) => h.trim()))
      .filter(Boolean);

    const acupuncture = (sections["침 처방"] ?? "")
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);

    return {
      id: "",
      patient_id: patientId,
      created_at: new Date().toISOString(),
      constitution: sections["사상체질"]?.trim() || "-",
      diagnosis,
      western_diagnosis,
      prescription,
      herbs,
      acupuncture,
    };
  }

  function clean(v: unknown): string {
    const s = String(v ?? "").trim();
    return s === "null" || s === "undefined" || s === "" ? "-" : s;
  }

  function mapDiagnosisResult(raw: Record<string, unknown>): DiagnosisResult {
    const r = raw as Record<string, Record<string, unknown>>;
    const herb = (r.herbal_prescription as Record<string, unknown>) ?? {};
    const composition =
      (herb.composition as { herb: string; dosage: string }[]) ?? [];
    return {
      id: "",
      patient_id: selectedPatient?.id ?? "",
      created_at: new Date().toISOString(),
      constitution: clean(r.sasang_constitution?.type),
      diagnosis: clean(r.tkm_diagnosis?.diagnosis_name),
      western_diagnosis: clean(
        (r.western_diagnosis as Record<string, unknown>)?.name,
      ),
      prescription: clean(herb.name_kr),
      herbs: composition
        .map((c) => `${c.herb} ${c.dosage}`)
        .filter((s) => !s.includes("null") && s.trim() !== ""),
      acupuncture: (
        (r.acupuncture_prescription as unknown as {
          point_kr: string;
          point_code: string;
        }[]) ?? []
      )
        .filter((p) => p.point_kr && String(p.point_kr) !== "null")
        .map((p) => `${p.point_kr}(${p.point_code})`),
    };
  }

  async function startAnalysis() {
    if (!selectedPatient) return setErrorMessage("환자를 선택해주세요");
    if (!audioFile && !symptomText.trim())
      return setErrorMessage(
        "녹음, 파일 업로드 또는 증상 입력 중 하나가 필요합니다",
      );
    setLoading(true);
    try {
      if (audioFile) {
        const data = await uploadAndAnalyze(selectedPatient.id, audioFile);
        setResult(data);
      } else {
        const { result: raw } = await diagnoseText(symptomText.trim());
        setResult(mapDiagnosisResult(raw));
      }
      setActiveTab("result");
    } catch (e: any) {
      setErrorMessage(
        e.response?.data?.detail || e.message || "분석에 실패했습니다.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPatient(e: React.FormEvent) {
    e.preventDefault();
    setAddLoading(true);
    try {
      await createPatient(newPatient);
      setPatientsLoading(true);
      const updated = await getPatients();
      setPatients(updated);
      setShowAddModal(false);
      setNewPatient({ name: "", birth_date: "", gender: "", phone: "" });
    } catch (e: any) {
      setErrorMessage(
        e.response?.data?.detail || e.message || "환자 등록에 실패했습니다.",
      );
    } finally {
      setAddLoading(false);
      setPatientsLoading(false);
    }
  }

  async function handleAsk(e: { preventDefault: () => void }) {
    e.preventDefault();
    const isLoading = askHistory.at(-1)?.answer === "";
    if (!askQuestion.trim() || isLoading) return;
    const q = askQuestion.trim();
    setAskQuestion("");
    setAskHistory((prev) => [...prev, { question: q, answer: "" }]);
    const updateLast = (answer: string) =>
      setAskHistory((prev) =>
        prev.map((item, i) =>
          i === prev.length - 1 ? { ...item, answer } : item,
        ),
      );
    try {
      if (askMode === "diagnose") {
        const { result } = await diagnoseText(q);
        const r = result as Record<string, Record<string, unknown>>;
        const constitution = r.sasang_constitution?.type ?? "-";
        const diagnosis = r.tkm_diagnosis?.diagnosis_name ?? "-";
        const western = (r.western_diagnosis?.name ?? "-") as string;
        const herb = r.herbal_prescription as Record<string, unknown>;
        const herbName = herb?.name_kr ?? "-";
        const composition = (
          (herb?.composition as { herb: string; dosage: string }[]) ?? []
        )
          .map((c) => `${c.herb} ${c.dosage}`)
          .join(", ");
        const acu = (
          (r.acupuncture_prescription as unknown as {
            point_kr: string;
            point_code: string;
          }[]) ?? []
        )
          .map((p) => `${p.point_kr}(${p.point_code})`)
          .join(", ");
        updateLast(
          `▶ 사상체질: ${constitution}\n▶ 한의학 진단: ${diagnosis}\n▶ 양방 진단: ${western}\n▶ 한약 처방: ${herbName}\n  ${composition}\n▶ 침 처방: ${acu}`,
        );
      } else {
        const res = await askDiagnosis(q);
        updateLast(res.answer);
      }
    } catch {
      updateLast("답변을 가져오지 못했습니다. 다시 시도해주세요.");
    }
  }

  async function handleEditSave() {
    if (!editPatient) return;
    setEditLoading(true);
    try {
      await updatePatient(editPatient.id, editForm);
      setPatients((prev) =>
        prev.map((p) => (p.id === editPatient.id ? { ...p, ...editForm } : p)),
      );
      setEditPatient(null);
    } catch {
      alert("수정에 실패했습니다.");
    } finally {
      setEditLoading(false);
    }
  }

  async function handleDeleteRecord(recordId: string) {
    if (!selectedPatient) return;
    if (!confirm("이 진료 이력을 삭제할까요?")) return;
    try {
      await deleteRecord(selectedPatient.id, recordId);
      setRecords((prev) => prev.filter((r) => r.id !== recordId));
    } catch {
      alert("삭제에 실패했습니다.");
    }
  }

  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!result || !selectedPatient) return;
    const text = `[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 사상체질
${result.constitution}

▶ 한의학적 진단
${result.diagnosis}
양방 대응: ${result.western_diagnosis}

▶ 한약 처방
${result.prescription}
${result.herbs?.join(", ")}

▶ 침 처방
${result.acupuncture?.join(", ")}

※ AI 참고용 / 최종 판단은 담당 한의사`;
    try {
      await saveRecord(selectedPatient.id, text);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      setShowSavedModal(true);
      setTimeout(() => setShowSavedModal(false), 2000);
    } catch (e: any) {
      setErrorMessage(
        e.response?.data?.detail || e.message || "저장에 실패했습니다.",
      );
    }
  }

  function copyAll() {
    if (!result || !selectedPatient) return;
    const text = `[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 사상체질
${result.constitution}

▶ 한의학적 진단
${result.diagnosis}
양방 대응: ${result.western_diagnosis}

▶ 한약 처방
${result.prescription}
${result.herbs?.join(", ")}

▶ 침 처방
${result.acupuncture?.join(", ")}

※ AI 참고용 / 최종 판단은 담당 한의사`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  function formatPhone(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 3) return digits;
    if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
    return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
  }

  const timer = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

  function patientSubtext(patient: Patient) {
    const gender =
      (
        { male: "남", female: "여", 남성: "남", 여성: "여" } as Record<
          string,
          string
        >
      )[patient.gender] ?? patient.gender;
    let birth: string | null = null;
    let age: string | null = null;
    if (patient.birth_date) {
      birth = patient.birth_date.replace(
        /^\d{2}(\d{2})-(\d{2})-(\d{2})$/,
        "$1$2$3",
      );
      const today = new Date();
      const b = new Date(patient.birth_date);
      let a = today.getFullYear() - b.getFullYear();
      if (today < new Date(today.getFullYear(), b.getMonth(), b.getDate())) a--;
      age = `만 ${a}세`;
    }
    const parts = [gender, birth && age ? `${birth} (${age})` : birth].filter(
      Boolean,
    );
    return parts.join(", ") || patient.phone || "-";
  }

  const resultCards: {
    label: string;
    Icon: LucideIcon;
    value: string | undefined;
    sub?: string;
    tags?: string[];
  }[] = result
    ? [
        { label: "사상체질", Icon: User, value: result.constitution },
        {
          label: "한의학적 진단",
          Icon: Stethoscope,
          value: result.diagnosis,
          sub: `양방: ${result.western_diagnosis}`,
        },
        {
          label: "한약 처방",
          Icon: Leaf,
          value: result.prescription,
          tags: result.herbs,
        },
        {
          label: "침 처방",
          Icon: MapPin,
          value: result.acupuncture?.join(" · "),
        },
      ]
    : [];

  const historySections: { key: string; Icon: LucideIcon }[] = [
    { key: "사상체질", Icon: User },
    { key: "한의학적 진단", Icon: Stethoscope },
    { key: "한약 처방", Icon: Leaf },
    { key: "침 처방", Icon: MapPin },
  ];

  return (
    <div className="flex h-[calc(100vh-52px)] overflow-hidden">
      {/* 왼쪽 환자 패널 */}
      <div className="hidden md:flex w-[260px] flex-shrink-0 bg-white border-r border-[#D4CCC4] flex-col">
        <div className="p-3 border-b border-[#D4CCC4]">
          <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-2">
            환자 목록
          </div>
          <div className="flex items-center gap-2 bg-[#EDE8E2] border border-[#D4CCC4] rounded-md px-3 py-2">
            <Search className="w-3.5 h-3.5 text-[#B0AAA4] flex-shrink-0" />
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="이름 검색..."
              className="flex-1 bg-transparent text-xs text-[#232323] outline-none"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {patientsLoading ? (
            <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto mt-8" />
          ) : displayedPatients.length === 0 ? (
            <div className="text-xs text-[#B0AAA4] text-center py-8">
              등록된 환자가 없습니다
            </div>
          ) : (
            filtered.map((patient) => (
              <div
                key={patient.id}
                className={`group flex items-center gap-2.5 px-3.5 py-2.5 cursor-pointer transition-all border-l-[2.5px] ${
                  selectedPatient?.id === patient.id
                    ? "bg-[#F5F2EE] border-l-[#EF6600]"
                    : "border-l-transparent hover:bg-[#F5F2EE]"
                }`}
                onClick={() => {
                  setSelectedPatient(patient);
                  setResult(null);
                  setRecordsLastFetchedFor(null);
                  setActiveTab("record");
                }}
              >
                <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-[#232323]">
                    {patient.name}
                  </div>
                  <div className="text-xs text-[#8A8480]">
                    {patientSubtext(patient)}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditPatient(patient);
                    setEditForm({
                      phone: patient.phone || "",
                      memo: patient.memo || "",
                    });
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[#D4CCC4] transition-all flex-shrink-0"
                  title="환자 정보 수정"
                >
                  <Pencil className="w-3 h-3 text-[#8A8480]" />
                </button>
              </div>
            ))
          )}
        </div>
        <div className="p-3 border-t border-[#D4CCC4] flex flex-col gap-2">
          <button
            onClick={() => setShowSyncModal(true)}
            className="w-full border border-[#C8BFB6] rounded-md py-2 text-xs text-[#8A8480] hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center justify-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> 환자 정보 가져오기
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="w-full bg-[#EF6600] text-white rounded-md py-2 text-xs flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3.5 h-3.5" /> 신규 환자 등록
          </button>
        </div>
      </div>

      {/* 오른쪽 메인 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex border-b border-[#D4CCC4] bg-white flex-shrink-0">
          {(["record", "result", "history", "ask"] as const).map((tab, i) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3.5 text-xs transition-all border-b-2 ${
                activeTab === tab
                  ? "text-[#EF6600] border-[#EF6600]"
                  : "text-[#8A8480] border-transparent hover:text-[#232323]"
              }`}
            >
              {["진료 녹음", "진단 결과", "진료 이력", "한의학 검색"][i]}
            </button>
          ))}
        </div>

        <div
          className={`flex-1 p-5 ${activeTab === "ask" ? "overflow-hidden flex flex-col" : "overflow-y-auto"}`}
        >
          {!selectedPatient && activeTab !== "ask" && (
            <div className="text-sm text-[#B0AAA4] text-center py-16">
              왼쪽에서 환자를 선택해주세요
            </div>
          )}

          {/* 진료 녹음 탭 */}
          {activeTab === "record" && selectedPatient && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">
                  음성 녹음
                </div>
                <div className="text-center p-6 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg mb-3">
                  <button
                    onClick={toggleRecording}
                    className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-all ${
                      isRecording
                        ? "bg-[#68413E] animate-pulse"
                        : "bg-[#EF6600] hover:scale-105"
                    }`}
                  >
                    {isRecording ? (
                      <Square className="w-5 h-5 text-white" />
                    ) : (
                      <Mic className="w-5 h-5 text-white" />
                    )}
                  </button>
                  <div className="text-sm font-medium text-[#232323] mb-1">
                    {isRecording
                      ? "녹음 중..."
                      : audioFile
                        ? "녹음 완료"
                        : "녹음 시작"}
                  </div>
                  {isRecording && (
                    <div className="flex items-center justify-center gap-1 h-6 my-2">
                      {[10, 18, 24, 16, 22, 14, 20].map((h, i) => (
                        <div
                          key={i}
                          className="w-[3px] rounded-sm bg-[#989689] animate-bounce"
                          style={{ height: h, animationDelay: `${i * 0.1}s` }}
                        />
                      ))}
                    </div>
                  )}
                  <div className="text-lg font-light text-[#232323] tabular-nums">
                    {timer}
                  </div>
                  <div className="text-xs text-[#8A8480] mt-1">
                    {isRecording
                      ? "버튼을 눌러 중지하세요"
                      : "버튼을 눌러 녹음을 시작하세요"}
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">
                    파일 업로드
                  </div>
                  <label className="border-[1.5px] border-dashed border-[#C8BFB6] rounded-lg p-5 text-center cursor-pointer hover:border-[#EF6600] transition-all bg-[#EDE8E2] block">
                    <FolderOpen className="w-7 h-7 text-[#B0AAA4] mx-auto mb-2" />
                    <div className="text-xs text-[#8A8480]">
                      {audioFile ? audioFile.name : "파일을 드래그하거나 클릭"}
                    </div>
                    <div className="text-xs text-[#B0AAA4] mt-1">
                      mp3, wav, m4a · 최대 100MB
                    </div>
                    <input
                      type="file"
                      accept=".mp3,.wav,.m4a,.webm"
                      className="hidden"
                      onChange={(e) =>
                        e.target.files && setAudioFile(e.target.files[0])
                      }
                    />
                  </label>
                </div>
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">
                    추가 메모
                  </div>
                  <textarea
                    value={memo}
                    onChange={(e) => setMemo(e.target.value)}
                    placeholder="주요 증상, 특이사항...&#10;예) 소화불량 3개월, 스트레스"
                    className="w-full bg-[#EDE8E2] border border-[#D4CCC4] rounded-md p-3 text-xs text-[#232323] outline-none focus:border-[#EF6600] resize-none min-h-[80px] transition-colors"
                  />
                </div>
              </div>
              <div className="md:col-span-2">
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">
                    증상 직접 입력{" "}
                    <span className="normal-case text-[#B0AAA4]">
                      (음성 없이 텍스트로 분석)
                    </span>
                  </div>
                  <textarea
                    value={symptomText}
                    onChange={(e) => setSymptomText(e.target.value)}
                    placeholder="증상을 자세히 입력하세요&#10;예) 손발이 차고 식은땀이 나며 소화가 잘 안 됨. 평소 피로감이 많고 추위를 탐."
                    className="w-full bg-[#EDE8E2] border border-[#D4CCC4] rounded-md p-3 text-xs text-[#232323] outline-none focus:border-[#EF6600] resize-none min-h-[90px] transition-colors"
                    disabled={!!audioFile}
                  />
                  {audioFile && (
                    <div className="text-xs text-[#B0AAA4] mt-1">
                      음성 파일이 있으면 텍스트 입력은 무시됩니다.
                    </div>
                  )}
                </div>
              </div>
              <div className="md:col-span-2">
                <button
                  onClick={startAnalysis}
                  disabled={loading || (!audioFile && !symptomText.trim())}
                  className="w-full bg-[#EF6600] text-white rounded-md py-3.5 text-sm font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {loading ? (
                    "분석 중..."
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" /> AI 진단 분석 시작
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* 진단 결과 탭 */}
          {activeTab === "result" && selectedPatient && (
            <div>
              {!result ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">
                  아직 진단 결과가 없습니다.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {resultCards.map(({ label, Icon, value, sub, tags }, i) => (
                      <div
                        key={i}
                        className="bg-white border border-[#D4CCC4] rounded-lg p-4 relative"
                      >
                        <button
                          onClick={() =>
                            navigator.clipboard.writeText(`${label}: ${value}`)
                          }
                          className="absolute top-3 right-3 bg-[#EDE8E2] border border-[#D4CCC4] rounded-md px-2 py-1 text-xs text-[#8A8480] hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center gap-1"
                        >
                          <Clipboard className="w-3 h-3" /> 복사
                        </button>
                        <div className="flex items-center gap-1.5 text-xs text-[#8A8480] uppercase tracking-wide mb-2">
                          <Icon className="w-3.5 h-3.5" /> {label}
                        </div>
                        <div className="text-sm font-medium text-[#232323]">
                          {value}
                        </div>
                        {sub && (
                          <div className="text-xs text-[#8A8480] mt-1">
                            {sub}
                          </div>
                        )}
                        {tags && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {tags.map((t, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 bg-[#EDE8E2] border border-[#D4CCC4] rounded text-xs text-[#585753]"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="bg-[#232323] rounded-lg p-5 mt-4 relative">
                    <div className="flex items-center gap-1.5 text-xs text-[#A09892] uppercase tracking-wide mb-3">
                      <Clipboard className="w-3.5 h-3.5" /> 동의보감 차팅용 전체
                      복사
                    </div>
                    <button
                      onClick={copyAll}
                      className={`absolute top-4 right-4 text-xs px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                        copied
                          ? "bg-green-600 text-white"
                          : "bg-[#EF6600] text-white hover:opacity-90"
                      }`}
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5" /> 복사 완료!
                        </>
                      ) : (
                        <>
                          <Clipboard className="w-3.5 h-3.5" /> 전체 복사
                        </>
                      )}
                    </button>
                    <pre className="text-xs text-white/70 leading-relaxed whitespace-pre-wrap font-sans mt-6">
                      {`[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient?.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 사상체질
${result.constitution}

▶ 한의학적 진단
${result.diagnosis}
양방: ${result.western_diagnosis}

▶ 한약 처방
${result.prescription}
${result.herbs?.join(", ")}

▶ 침 처방
${result.acupuncture?.join(", ")}

※ AI 참고용 / 최종 판단은 담당 한의사`}
                    </pre>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-[#B0AAA4] mt-3 p-3 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg">
                    <TriangleAlert className="w-3.5 h-3.5 flex-shrink-0" />본
                    결과는 AI 참고용이며 최종 진단 및 처방은 반드시 한의사가
                    직접 판단해야 합니다.
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => setShowSaveModal(true)}
                      className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-xs flex items-center justify-center gap-1.5 hover:opacity-90 disabled:opacity-50"
                      disabled={saved}
                    >
                      {saved ? (
                        <>
                          <CircleCheck className="w-3.5 h-3.5" /> 저장됨
                        </>
                      ) : (
                        <>
                          <Save className="w-3.5 h-3.5" /> 저장
                        </>
                      )}
                    </button>
                    <button className="flex-1 border border-[#C8BFB6] rounded-md py-2.5 text-xs text-[#8A8480] hover:border-[#232323] transition-all flex items-center justify-center gap-1.5">
                      <Printer className="w-3.5 h-3.5" /> 인쇄
                    </button>
                    <button
                      onClick={() => setActiveTab("record")}
                      className="flex-1 border border-[#C8BFB6] rounded-md py-2.5 text-xs text-[#8A8480] hover:border-[#232323] transition-all flex items-center justify-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> 새 진료
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* 진료 이력 탭 */}
          {activeTab === "history" && selectedPatient && (
            <div className="overflow-y-auto">
              {recordsLoading ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">
                  불러오는 중...
                </div>
              ) : records.length === 0 ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">
                  진료 이력이 없습니다
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {records
                    .slice()
                    .sort((a, b) => {
                      const da = a.recorded_at
                        ? new Date(a.recorded_at).getTime()
                        : 0;
                      const db = b.recorded_at
                        ? new Date(b.recorded_at).getTime()
                        : 0;
                      return db - da;
                    })
                    .map((r) => {
                      const sections = parseChartSections(r.chart_structured);
                      const isOpen = expandedRecord === r.id;
                      const diagSummary = sections?.["한의학적 진단"]
                        ?.split("\n")[0]
                        ?.trim();
                      const prescSummary = sections?.["한약 처방"]
                        ?.split("\n")[0]
                        ?.trim();
                      return (
                        <div
                          key={r.id}
                          className="bg-white border border-[#D4CCC4] rounded-lg overflow-hidden"
                        >
                          <div className="flex items-stretch">
                            <button
                              onClick={() =>
                                setExpandedRecord(isOpen ? null : r.id)
                              }
                              className="flex-1 flex items-start justify-between px-4 py-3 text-left gap-2"
                            >
                              <div className="flex flex-col gap-0.5 min-w-0">
                                <span className="text-sm font-medium text-[#232323]">
                                  {r.recorded_at
                                    ? new Date(r.recorded_at).toLocaleString(
                                        "ko-KR",
                                        {
                                          year: "numeric",
                                          month: "long",
                                          day: "numeric",
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        },
                                      )
                                    : "날짜 미상"}
                                </span>
                                {(diagSummary || prescSummary) && (
                                  <span className="text-xs text-[#8A8480] truncate">
                                    {[diagSummary, prescSummary]
                                      .filter(Boolean)
                                      .join(" · ")}
                                  </span>
                                )}
                              </div>
                              {isOpen ? (
                                <ChevronUp className="w-4 h-4 text-[#8A8480] flex-shrink-0 mt-0.5" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-[#8A8480] flex-shrink-0 mt-0.5" />
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteRecord(r.id)}
                              className="px-3 border-l border-[#D4CCC4] text-[#B0AAA4] hover:text-red-500 hover:bg-red-50 transition-colors"
                              title="삭제"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          {isOpen && (
                            <div className="border-t border-[#D4CCC4] p-4 flex flex-col gap-4">
                              {sections ? (
                                historySections.map(({ key, Icon }) => {
                                  const content = sections[key] || "-";
                                  const isHerbs = key === "한약 처방";
                                  const isAcu = key === "침 처방";
                                  const tags =
                                    (isHerbs || isAcu) && content !== "-"
                                      ? content
                                          .split(/[,，\n]/)
                                          .map((s) => s.trim())
                                          .filter(Boolean)
                                      : null;
                                  return (
                                    <div key={key}>
                                      <div className="flex items-center gap-1.5 text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">
                                        <Icon className="w-3.5 h-3.5" /> {key}
                                      </div>
                                      {tags ? (
                                        <div className="flex flex-wrap gap-1">
                                          {tags.map((t, i) => (
                                            <span
                                              key={i}
                                              className="inline-block bg-[#F5F2EE] border border-[#D4CCC4] rounded px-2 py-0.5 text-xs text-[#232323]"
                                            >
                                              {t}
                                            </span>
                                          ))}
                                        </div>
                                      ) : (
                                        <div className="text-sm text-[#232323] whitespace-pre-wrap">
                                          {content}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })
                              ) : (
                                <div className="text-sm text-[#232323] whitespace-pre-wrap">
                                  {r.chart_structured || "차트 내용 없음"}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          )}

          {/* 한의학 검색 탭 */}
          {activeTab === "ask" && (
            <div className="flex flex-col flex-1 min-h-0 gap-4">
              <div className="flex-1 flex flex-col gap-3 overflow-y-auto min-h-0">
                {askHistory.length === 0 && (
                  <div className="text-center py-16 text-[#B0AAA4]">
                    <MessageCircle className="w-8 h-8 mx-auto mb-3 text-[#B0AAA4]" />
                    <div className="text-sm">
                      한의학 관련 궁금한 점을 질문해보세요
                    </div>
                    <div className="text-xs mt-2 text-[#C8BFB6]">
                      예) 소음인 소화불량에 어떤 처방이 좋나요?
                    </div>
                  </div>
                )}
                {askHistory.map((item, i) => (
                  <div key={i} className="flex flex-col gap-2">
                    <div className="self-end max-w-[75%] bg-[#EF6600] text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5">
                      {item.question}
                    </div>
                    {item.answer === "" ? (
                      <div className="self-start bg-white border border-[#D4CCC4] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                        {[0, 1, 2].map((j) => (
                          <div
                            key={j}
                            className="w-1.5 h-1.5 bg-[#B0AAA4] rounded-full animate-bounce"
                            style={{ animationDelay: `${j * 0.15}s` }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="self-start max-w-[75%] bg-white border border-[#D4CCC4] text-sm text-[#232323] rounded-2xl rounded-tl-sm px-4 py-2.5 leading-relaxed whitespace-pre-wrap">
                        {item.answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="pt-2 border-t border-[#D4CCC4] flex flex-col gap-2">
                <div className="flex gap-1 p-1 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg w-fit">
                  <button
                    type="button"
                    onClick={() => setAskMode("ask")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === "ask"
                        ? "bg-white text-[#232323] shadow-sm"
                        : "text-[#8A8480] hover:text-[#232323]"
                    }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" /> 질문하기
                  </button>
                  <button
                    type="button"
                    onClick={() => setAskMode("diagnose")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === "diagnose"
                        ? "bg-white text-[#232323] shadow-sm"
                        : "text-[#8A8480] hover:text-[#232323]"
                    }`}
                  >
                    <Stethoscope className="w-3.5 h-3.5" /> 증상 분석
                  </button>
                </div>
                <form onSubmit={handleAsk} className="flex gap-2">
                  <input
                    value={askQuestion}
                    onChange={(e) => setAskQuestion(e.target.value)}
                    placeholder={
                      askMode === "diagnose"
                        ? "증상을 입력하면 진단·처방을 분석합니다..."
                        : "한의학 관련 질문을 입력하세요..."
                    }
                    className="flex-1 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                    disabled={askHistory.at(-1)?.answer === ""}
                  />
                  <button
                    type="submit"
                    disabled={
                      askHistory.at(-1)?.answer === "" || !askQuestion.trim()
                    }
                    className="bg-[#EF6600] text-white px-4 py-2.5 rounded-lg text-sm disabled:opacity-40 hover:opacity-90 transition-opacity"
                  >
                    전송
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 저장 확인 모달 */}
      {showSaveModal && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowSaveModal(false)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <div className="text-sm font-medium text-[#232323] mb-6">
                저장하시겠습니까?
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowSaveModal(false);
                    handleSave();
                  }}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  확인
                </button>
                <button
                  onClick={() => setShowSaveModal(false)}
                  className="flex-1 border border-[#C8BFB6] rounded-md py-2.5 text-sm text-[#8A8480] hover:border-[#232323] hover:text-[#232323] transition-all"
                >
                  취소
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 저장 완료 모달 */}
      {showSavedModal && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowSavedModal(false)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <CircleCheck className="w-10 h-10 text-[#EF6600] mx-auto mb-3" />
              <div className="text-sm font-medium text-[#232323] mb-5">
                저장되었습니다
              </div>
              <button
                onClick={() => setShowSavedModal(false)}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 에러 모달 */}
      {errorMessage && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setErrorMessage(null)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <TriangleAlert className="w-10 h-10 text-[#EF6600] mx-auto mb-3" />
              <div className="text-sm font-medium text-[#232323] mb-5">
                {errorMessage}
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 신규 환자 등록 모달 */}
      {showAddModal && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#D4CCC4]">
              <div className="text-sm font-medium text-[#232323]">
                신규 환자 등록
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-[#8A8480] hover:text-[#232323] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form
              onSubmit={handleAddPatient}
              className="p-5 flex flex-col gap-3"
            >
              {[
                {
                  label: "이름 *",
                  key: "name",
                  type: "text",
                  placeholder: "환자 이름",
                },
                {
                  label: "생년월일",
                  key: "birth_date",
                  type: "date",
                  placeholder: "",
                },
                {
                  label: "전화번호",
                  key: "phone",
                  type: "tel",
                  placeholder: "010-0000-0000",
                },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">
                    {field.label}
                  </label>
                  <input
                    type={field.type}
                    placeholder={field.placeholder}
                    value={newPatient[field.key as keyof typeof newPatient]}
                    onChange={(e) =>
                      setNewPatient({
                        ...newPatient,
                        [field.key]:
                          field.key === "phone"
                            ? formatPhone(e.target.value)
                            : e.target.value,
                      })
                    }
                    className="w-full bg-[#F5F2EE] border border-[#D4CCC4] rounded-md px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                    required={field.key === "name"}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">
                  성별
                </label>
                <div className="flex gap-2">
                  {["남성", "여성"].map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() =>
                        setNewPatient({ ...newPatient, gender: g })
                      }
                      className={`flex-1 py-2.5 text-sm rounded-md border transition-all ${
                        newPatient.gender === g
                          ? "bg-[#EF6600] text-white border-[#EF6600]"
                          : "bg-white text-[#8A8480] border-[#D4CCC4] hover:border-[#EF6600]"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <button
                type="submit"
                disabled={addLoading}
                className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 mt-2"
              >
                {addLoading ? "등록 중..." : "등록 완료"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 동기화 에이전트 안내 모달 */}
      {showSyncModal && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowSyncModal(false)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[440px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#D4CCC4]">
              <div className="text-sm font-medium text-[#232323]">
                환자 정보 자동 동기화 설정
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="text-[#8A8480] hover:text-[#232323] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 flex flex-col gap-4 text-sm text-[#232323]">
              <p className="text-[#8A8480] text-xs leading-relaxed">
                기존 차팅 프로그램의 환자 데이터를 Zinmac으로 자동으로
                가져옵니다.
                <br />
                한의맥 또는 네오보감이 설치된 Windows 컴퓨터에서 아래 스크립트를
                한 번만 실행하면 이후 1시간마다 자동 동기화됩니다.
              </p>
              <div className="flex flex-col gap-3">
                {[
                  {
                    name: "한의맥",
                    file: "hanimac_setup.bat",
                    color: "bg-[#EEF4FF] border-[#C7D9F8] text-[#2563EB]",
                  },
                  {
                    name: "네오보감",
                    file: "neobogam_setup.bat",
                    color: "bg-[#F0FDF4] border-[#BBF7D0] text-[#16A34A]",
                  },
                ].map(({ name, file, color }) => (
                  <div key={name} className={`rounded-lg border p-4 ${color}`}>
                    <div className="font-medium mb-2">{name}</div>
                    <ol className="text-xs leading-relaxed list-decimal list-inside flex flex-col gap-1 text-[#232323]">
                      <li>
                        관리자에게{" "}
                        <span className="font-mono font-semibold">{file}</span>{" "}
                        파일 요청
                      </li>
                      <li>{name} Windows 컴퓨터에서 파일 실행</li>
                      <li>Zinmac 면허번호 · 비밀번호 입력</li>
                      <li>완료 — 이후 자동 동기화</li>
                    </ol>
                  </div>
                ))}
              </div>
              <p className="text-xs text-[#B0AAA4]">
                문의: 관리자에게 연락하세요.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 환자 정보 수정 모달 */}
      {editPatient && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setEditPatient(null)}
        >
          <div
            className="bg-white rounded-xl w-full max-w-[360px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#D4CCC4]">
              <div className="text-sm font-medium text-[#232323]">
                {editPatient.name} 정보 수정
              </div>
              <button
                onClick={() => setEditPatient(null)}
                className="text-[#8A8480] hover:text-[#232323]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 flex flex-col gap-3">
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">
                  전화번호
                </label>
                <input
                  type="text"
                  value={editForm.phone}
                  onChange={(e) =>
                    setEditForm((f) => ({
                      ...f,
                      phone: formatPhone(e.target.value),
                    }))
                  }
                  placeholder="010-0000-0000"
                  className="w-full border border-[#C8BFB6] rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">
                  메모
                </label>
                <textarea
                  value={editForm.memo}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, memo: e.target.value }))
                  }
                  placeholder="특이사항 등"
                  rows={3}
                  className="w-full border border-[#C8BFB6] rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600] resize-none"
                />
              </div>
              <button
                onClick={handleEditSave}
                disabled={editLoading}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50 mt-1"
              >
                {editLoading ? "저장 중..." : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 로딩 오버레이 */}
      {loading && (
        <div className="fixed inset-0 bg-[#232323]/60 z-50 flex flex-col items-center justify-center gap-4">
          <div className="w-9 h-9 border-2 border-white/20 border-t-[#EF6600] rounded-full animate-spin" />
          <div className="text-sm text-white/80">
            AI가 진료 내용을 분석하고 있습니다...
          </div>
        </div>
      )}
    </div>
  );
}
