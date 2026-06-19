"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getPatients,
  getPatient,
  createPatient,
  getPatientRecords,
  saveRecord,
  updatePatient,
  deleteRecord,
  importPatientsFromExcel,
} from "@/lib/api/patients";
import {
  uploadAndAnalyze,
  askDiagnosisStream,
  diagnoseText,
  finalizeRecord,
  ChartingEvent,
} from "@/lib/api/diagnosis";
import { Patient, DiagnosisResult } from "@/types";
import BetaFeedbackBanner from "@/components/BetaFeedbackBanner";
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
  FileText,
  ThumbsUp,
  ThumbsDown,
  type LucideIcon,
} from "lucide-react";

const PAGE_SIZE = 20;

const ASK_SAVE_FIELDS: { key: string; label: string }[] = [
  { key: "constitution", label: "사상체질" },
  { key: "diagnosis", label: "한의학적 진단 / 양방 대응" },
  { key: "prescription", label: "한약 처방" },
  { key: "acupuncture", label: "침 처방" },
];

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
  const [audioFiles, setAudioFiles] = useState<File[]>([]);
  const [memo, setMemo] = useState("");
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingResult2, setLoadingResult2] = useState(false);
  const [copied, setCopied] = useState<"both" | "result1" | "result2" | null>(null);
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
    { question: string; answer: string; result?: DiagnosisResult }[]
  >([]);
  const [askSavePicker, setAskSavePicker] = useState<number | null>(null);
  const [askSaveSelections, setAskSaveSelections] = useState<
    Record<string, boolean>
  >({});
  const [askSaving, setAskSaving] = useState(false);
  const [askMode, setAskMode] = useState<"ask" | "diagnose">("ask");
  const [symptomText, setSymptomText] = useState("");
  const [savedSymptomText, setSavedSymptomText] = useState<string | undefined>(
    undefined,
  );
  const [currentRecordId, setCurrentRecordId] = useState<string | null>(null);
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [saveSelection, setSaveSelection] = useState<
    "both" | "result1" | "result2"
  >("both");
  const [records, setRecords] = useState<
    {
      id: string;
      recorded_at: string | null;
      chart_structured: string | null;
      raw_transcription: string | null;
      medical_history: string | null;
    }[]
  >([]);
  const [latestChartStructured, setLatestChartStructured] = useState<
    string | null
  >(null);
  const [medicalHistories, setMedicalHistories] = useState<
    Record<string, { hasHistory: boolean; text: string }>
  >({});
  const [savingMedicalHistory, setSavingMedicalHistory] = useState<
    string | null
  >(null);
  const [memoEditing, setMemoEditing] = useState(false);
  const [memoDraft, setMemoDraft] = useState("");
  const [recordMedicalHistory, setRecordMedicalHistory] = useState<{
    hasHistory: boolean;
    text: string;
  }>({ hasHistory: false, text: "" });
  const [recordsLastFetchedFor, setRecordsLastFetchedFor] = useState<
    string | null
  >(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const excelInputRef = useRef<HTMLInputElement | null>(null);
  const [expandedRecord, setExpandedRecord] = useState<string | null>(null);
  const [expandedCC, setExpandedCC] = useState<Set<string>>(new Set());
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [editPatient, setEditPatient] = useState<Patient | null>(null);
  const [editForm, setEditForm] = useState({ phone: "", memo: "" });
  const [editLoading, setEditLoading] = useState(false);
  const [feedbackAvailable, setFeedbackAvailable] = useState(false);
  const [feedbackHelpful, setFeedbackHelpful] = useState<boolean | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackRecordId, setFeedbackRecordId] = useState<string | null>(null);
  const [memoSectionOpen, setMemoSectionOpen] = useState(false);
  const [resultMemoOpen, setResultMemoOpen] = useState(false);
  const [recordMemoOpen, setRecordMemoOpen] = useState(false);
  const [recordHistoryOpen, setRecordHistoryOpen] = useState(false);
  const [historyMemoOpenIds, setHistoryMemoOpenIds] = useState<Set<string>>(
    new Set(),
  );
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const secondsRef = useRef(0);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const urlPatientIdRef = useRef<string | null>(null);

  const filtered = patients.filter((p) => p.name.includes(search));
  const displayedPatients = filtered.slice(0, page * PAGE_SIZE);
  const hasMore = filtered.length > page * PAGE_SIZE;
  const recordsLoading =
    activeTab === "history" &&
    !!selectedPatient &&
    recordsLastFetchedFor !== selectedPatient.id;

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      urlPatientIdRef.current = params.get("patientId");
    }
  }, []);

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
    const id = urlPatientIdRef.current;
    if (!id) return;
    urlPatientIdRef.current = null;
    getPatient(id)
      .then((p: Patient) => {
        setSelectedPatient(p);
        setMemo(p.memo || "");
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedPatient) return;
    setCurrentRecordId(null);
    setChiefComplaint("");
    setLatestChartStructured(null);
    getPatientRecords(selectedPatient.id)
      .then((data) => {
        const sorted = [...data.records].sort((a, b) => {
          const da = a.recorded_at ? new Date(a.recorded_at).getTime() : 0;
          const db = b.recorded_at ? new Date(b.recorded_at).getTime() : 0;
          return db - da;
        });
        const latest = sorted[0];
        if (!latest?.chart_structured) return;
        setLatestChartStructured(latest.chart_structured);
        const sections = parseChartSections(latest.chart_structured);
        if (!sections) return;
        setResult(mapSectionsToResult(sections, selectedPatient.id));
        if (latest.raw_transcription) setChiefComplaint(latest.raw_transcription);
      })
      .catch(console.error);
  }, [selectedPatient?.id]);

  useEffect(() => {
    if (activeTab !== "history" || !selectedPatient) return;
    const id = selectedPatient.id;
    getPatientRecords(id)
      .then((data) => {
        setRecords(data.records);
        setRecordsLastFetchedFor(id);
        setMedicalHistories((prev) => {
          const next = { ...prev };
          for (const r of data.records) {
            if (!(r.id in next)) {
              next[r.id] = {
                hasHistory: !!r.medical_history,
                text: r.medical_history || "",
              };
            }
          }
          return next;
        });
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
        if (secondsRef.current < 10) {
          setErrorMessage("녹음 파일이 너무 짧아요. 10초 이상 녹음해주세요.");
          return;
        }
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioFiles((prev) => [
          ...prev,
          new File([blob], `recording-${prev.length + 1}.webm`, {
            type: "audio/webm",
          }),
        ]);
      };
      recorder.start();
      mediaRef.current = recorder;
      setIsRecording(true);
      setSeconds(0);
      secondsRef.current = 0;
      timerRef.current = setInterval(() => {
        secondsRef.current += 1;
        setSeconds(secondsRef.current);
      }, 1000);
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

  function splitResultBlocks(
    text: string | null,
  ): { before: string; result1: string; result2: string } | null {
    if (!text) return null;
    const i1 = text.indexOf("■ 결과 1");
    const i2 = text.indexOf("■ 결과 2");
    if (i1 === -1 || i2 === -1) return null;
    return {
      before: text.slice(0, i1),
      result1: text.slice(i1, i2),
      result2: text.slice(i2),
    };
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
      chiefComplaintSummary: sections["주소증"]?.trim() || "",
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

  function mapSingleDiagnosis(raw: Record<string, unknown>): DiagnosisResult {
    const r = raw as Record<string, Record<string, unknown>>;
    const herb = (r.herbal_prescription as Record<string, unknown>) ?? {};
    const composition =
      (herb.composition as { herb: string; dosage: string }[]) ?? [];
    return {
      id: "",
      patient_id: selectedPatient?.id ?? "",
      created_at: new Date().toISOString(),
      chiefComplaintSummary:
        typeof raw.chief_complaint_summary === "string"
          ? raw.chief_complaint_summary.trim()
          : "",
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

  function formatResultBlock(r: DiagnosisResult, label: string): string {
    return `■ ${label}
▶ 사상체질
${r.constitution}

▶ 한의학적 진단
${r.diagnosis}
양방 대응: ${r.western_diagnosis}

▶ 한약 처방
${r.prescription}
${r.herbs?.join(", ")}

▶ 침 처방
${r.acupuncture?.join(", ")}`;
  }

  function mapDiagnosisResult(raw: Record<string, unknown>): DiagnosisResult {
    const datasetBased = mapSingleDiagnosis(
      (raw.dataset_based as Record<string, unknown>) ?? {},
    );
    const claudeBased = mapSingleDiagnosis(
      (raw.claude_based as Record<string, unknown>) ?? {},
    );
    return { ...datasetBased, claudeBased };
  }

  async function startAnalysis() {
    if (!selectedPatient) return setErrorMessage("환자를 선택해주세요");
    if (audioFiles.length === 0 && !symptomText.trim())
      return setErrorMessage(
        "녹음, 파일 업로드 또는 증상 입력 중 하나가 필요합니다",
      );
    setLoading(true);
    const medicalHistory = recordMedicalHistory.hasHistory
      ? recordMedicalHistory.text || null
      : null;
    if (memo.trim()) {
      updatePatient(selectedPatient.id, { memo: memo.trim() })
        .then(() => {
          const updated = { ...selectedPatient, memo: memo.trim() };
          setPatients((prev) =>
            prev.map((p) => (p.id === selectedPatient.id ? updated : p)),
          );
          setSelectedPatient(updated);
        })
        .catch(() => {});
    }
    try {
      if (audioFiles.length > 0) {
        await uploadAndAnalyze(
          selectedPatient.id,
          audioFiles,
          medicalHistory,
          symptomText.trim() || null,
          (event: ChartingEvent) => {
            switch (event.type) {
              case "transcription":
                setChiefComplaint(event.transcription);
                break;
              case "dataset_based":
                setResult(mapSingleDiagnosis(event.data));
                setSaveSelection("both");
                setFeedbackAvailable(true);
                setResultMemoOpen(false);
                setActiveTab("result");
                setLoading(false);
                setLoadingResult2(true);
                break;
              case "claude_based": {
                const claudeBased = mapSingleDiagnosis(event.data);
                setResult((prev) => (prev ? { ...prev, claudeBased } : prev));
                setLoadingResult2(false);
                break;
              }
              case "done":
                setCurrentRecordId(event.record_id);
                break;
              case "error":
                throw new Error(event.detail);
            }
          },
        );
      } else {
        const { result: raw } = await diagnoseText(
          symptomText.trim(),
          medicalHistory,
        );
        setSavedSymptomText(symptomText.trim());
        setCurrentRecordId(null);
        setChiefComplaint(symptomText.trim());
        setResult(mapDiagnosisResult(raw));
        setSaveSelection("both");
        setFeedbackAvailable(true);
        setResultMemoOpen(false);
        setActiveTab("result");
      }
    } catch (e: any) {
      setErrorMessage(
        e.response?.data?.detail || e.message || "분석에 실패했습니다.",
      );
    } finally {
      setLoading(false);
      setLoadingResult2(false);
    }
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
      // silent fail — user sees nothing if import errors
    } finally {
      setImportLoading(false);
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
    const updateLast = (answer: string, result?: DiagnosisResult) =>
      setAskHistory((prev) =>
        prev.map((item, i) =>
          i === prev.length - 1
            ? { ...item, answer, ...(result ? { result } : {}) }
            : item,
        ),
      );
    try {
      if (askMode === "diagnose") {
        const { result } = await diagnoseText(q);
        const raw = result as Record<string, Record<string, unknown>>;

        const formatOne = (r: Record<string, unknown>) => {
          const rr = r as Record<string, Record<string, unknown>>;
          const constitution = rr.sasang_constitution?.type ?? "-";
          const diagnosis = rr.tkm_diagnosis?.diagnosis_name ?? "-";
          const western = (rr.western_diagnosis?.name ?? "-") as string;
          const herb = rr.herbal_prescription as Record<string, unknown>;
          const herbName = herb?.name_kr ?? "-";
          const composition = (
            (herb?.composition as { herb: string; dosage: string }[]) ?? []
          )
            .map((c) => `${c.herb} ${c.dosage}`)
            .join(", ");
          const acu = (
            (rr.acupuncture_prescription as unknown as {
              point_kr: string;
              point_code: string;
            }[]) ?? []
          )
            .map((p) => `${p.point_kr}(${p.point_code})`)
            .join(", ");
          return `▶ 사상체질: ${constitution}\n▶ 한의학 진단: ${diagnosis}\n▶ 양방 진단: ${western}\n▶ 한약 처방: ${herbName}\n  ${composition}\n▶ 침 처방: ${acu}`;
        };

        const datasetText = formatOne(raw.dataset_based ?? {});
        const claudeText = formatOne(raw.claude_based ?? {});
        updateLast(
          `[결과 1]\n${datasetText}\n\n[결과 2]\n${claudeText}`,
          mapDiagnosisResult(raw),
        );
      } else {
        const sentQuestion =
          selectedPatient && latestChartStructured
            ? `[환자 정보]\n이름: ${selectedPatient.name} / ${patientSubtext(selectedPatient)}\n\n[최근 진료 기록]\n${latestChartStructured}\n\n[질문]\n${q}`
            : q;
        let answer = "";
        await askDiagnosisStream(sentQuestion, (chunk) => {
          answer += chunk;
          updateLast(answer);
        });
      }
    } catch {
      updateLast("답변을 가져오지 못했습니다. 다시 시도해주세요.");
    }
  }

  function openAskSavePicker(index: number) {
    const all: Record<string, boolean> = {};
    for (const r of ["r1", "r2"]) {
      for (const f of ASK_SAVE_FIELDS) {
        all[`${r}.${f.key}`] = true;
      }
    }
    setAskSaveSelections(all);
    setAskSavePicker(index);
  }

  function formatSelectedAskBlock(
    r: DiagnosisResult,
    label: string,
    prefix: string,
  ): string | null {
    const lines: string[] = [];
    if (askSaveSelections[`${prefix}.constitution`])
      lines.push(`▶ 사상체질\n${r.constitution}`);
    if (askSaveSelections[`${prefix}.diagnosis`])
      lines.push(
        `▶ 한의학적 진단\n${r.diagnosis}\n양방 대응: ${r.western_diagnosis}`,
      );
    if (askSaveSelections[`${prefix}.prescription`])
      lines.push(`▶ 한약 처방\n${r.prescription}\n${r.herbs?.join(", ")}`);
    if (askSaveSelections[`${prefix}.acupuncture`])
      lines.push(`▶ 침 처방\n${r.acupuncture?.join(", ")}`);
    if (lines.length === 0) return null;
    return `■ ${label}\n${lines.join("\n\n")}`;
  }

  async function handleAskSave() {
    if (askSavePicker === null) return;
    const item = askHistory[askSavePicker];
    if (!item?.result || !selectedPatient) return;

    const block1 = formatSelectedAskBlock(item.result, "결과 1", "r1");
    const block2 = item.result.claudeBased
      ? formatSelectedAskBlock(item.result.claudeBased, "결과 2", "r2")
      : null;
    const blocks = [block1, block2].filter((b): b is string => !!b);
    if (blocks.length === 0) {
      setErrorMessage("저장할 항목을 선택해주세요");
      return;
    }

    const text = `[AI 한의 진단 보조 — Zinmac (한의학 검색)]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 질문/증상
${item.question}

${blocks.join("\n\n")}

※ AI 참고용 / 최종 판단은 담당 한의사`;

    setAskSaving(true);
    try {
      await saveRecord(selectedPatient.id, text, item.question);
      setAskSavePicker(null);
      setShowSavedModal(true);
      setTimeout(() => setShowSavedModal(false), 2000);
    } catch (e: any) {
      setErrorMessage(e.message || "저장에 실패했습니다.");
    } finally {
      setAskSaving(false);
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

  async function handleSaveMedicalHistory(recordId: string) {
    const draft = medicalHistories[recordId];
    if (!draft) return;
    const medical_history = draft.hasHistory ? draft.text || null : null;
    setSavingMedicalHistory(recordId);
    try {
      const BASE_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("token");
      const res = await fetch(
        `${BASE_URL}/api/charting/${recordId}/medical-history`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ medical_history }),
        },
      );
      if (!res.ok) throw new Error("병력 저장 실패");
      setRecords((prev) =>
        prev.map((r) => (r.id === recordId ? { ...r, medical_history } : r)),
      );
      setMedicalHistories((prev) => ({
        ...prev,
        [recordId]: {
          hasHistory: !!medical_history,
          text: medical_history || "",
        },
      }));
      setShowSavedModal(true);
      setTimeout(() => setShowSavedModal(false), 2000);
    } catch {
      setErrorMessage("병력 저장에 실패했습니다.");
    } finally {
      setSavingMedicalHistory(null);
    }
  }

  async function handleSaveMemo() {
    if (!selectedPatient) return;
    try {
      await updatePatient(selectedPatient.id, { memo: memoDraft });
      const updated = { ...selectedPatient, memo: memoDraft };
      setPatients((prev) =>
        prev.map((p) => (p.id === selectedPatient.id ? updated : p)),
      );
      setSelectedPatient(updated);
      setMemo(memoDraft);
      setMemoEditing(false);
    } catch {
      setErrorMessage("메모 저장에 실패했습니다.");
    }
  }

  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!result || !selectedPatient) return;
    const ccLine = result.chiefComplaintSummary?.trim() || chiefComplaint.trim() || "-";
    const memoLine = memo.trim() || "-";
    const historyLine =
      recordMedicalHistory.hasHistory && recordMedicalHistory.text.trim()
        ? recordMedicalHistory.text.trim()
        : "없음";
    const resultBlock =
      saveSelection === "result1"
        ? formatResultBlock(result, "결과 1")
        : saveSelection === "result2" && result.claudeBased
          ? formatResultBlock(result.claudeBased, "결과 2")
          : result.claudeBased
            ? `${formatResultBlock(result, "결과 1")}\n\n${formatResultBlock(result.claudeBased, "결과 2")}`
            : formatResultBlock(result, "진단 결과");
    const text = `[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 주소증
${ccLine}

${resultBlock}

▶ 메모
${memoLine}

▶ 병력
${historyLine}

※ AI 참고용 / 최종 판단은 담당 한의사`;
    try {
      const response = currentRecordId
        ? await finalizeRecord(currentRecordId, text, saveSelection)
        : await saveRecord(
            selectedPatient.id,
            text,
            chiefComplaint || savedSymptomText,
            recordMedicalHistory.hasHistory
              ? recordMedicalHistory.text || null
              : null,
            saveSelection,
          );
      setSavedSymptomText(undefined);
      setFeedbackRecordId(response?.id ?? null);
      setFeedbackHelpful(null);
      setFeedbackComment("");
      setFeedbackSubmitted(false);
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

  async function handleFeedback() {
    if (!feedbackRecordId || feedbackHelpful === null) return;
    try {
      const BASE_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("token");
      const res = await fetch(`${BASE_URL}/api/feedback/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          medical_record_id: feedbackRecordId,
          is_helpful: feedbackHelpful,
          comment: feedbackComment,
        }),
      });
      if (!res.ok) throw new Error("피드백 제출 실패");
      setFeedbackSubmitted(true);
    } catch {
      setErrorMessage("피드백 제출에 실패했습니다.");
    }
  }

  function buildResultText(
    selection: "both" | "result1" | "result2" = "both",
  ): string | null {
    if (!result || !selectedPatient) return null;
    const ccLine = result.chiefComplaintSummary?.trim() || chiefComplaint.trim() || "-";
    const memoLine = memo.trim() || "-";
    const historyLine =
      recordMedicalHistory.hasHistory && recordMedicalHistory.text.trim()
        ? recordMedicalHistory.text.trim()
        : "없음";
    const resultBlock =
      selection === "result1"
        ? formatResultBlock(result, "결과 1")
        : selection === "result2" && result.claudeBased
          ? formatResultBlock(result.claudeBased, "결과 2")
          : result.claudeBased
            ? `${formatResultBlock(result, "결과 1")}\n\n${formatResultBlock(result.claudeBased, "결과 2")}`
            : formatResultBlock(result, "진단 결과");
    return `[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString("ko-KR")}

▶ 주소증
${ccLine}

${resultBlock}

▶ 메모
${memoLine}

▶ 병력
${historyLine}

※ AI 참고용 / 최종 판단은 담당 한의사`;
  }

  function copyResult(selection: "both" | "result1" | "result2") {
    const text = buildResultText(selection);
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(selection);
    setTimeout(() => setCopied(null), 2500);
  }

  function handlePrint() {
    const text = buildResultText();
    if (!text || !selectedPatient) return;
    const printWindow = window.open("", "_blank", "width=800,height=900");
    if (!printWindow) {
      setErrorMessage("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }
    printWindow.document.title = `진단 결과 - ${selectedPatient.name}`;
    const pre = printWindow.document.createElement("pre");
    pre.style.cssText =
      "white-space: pre-wrap; font-family: sans-serif; font-size: 13px; line-height: 1.6; color: #232323; padding: 24px; margin: 0;";
    pre.textContent = text;
    printWindow.document.body.appendChild(pre);
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
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

  function buildResultCards(r: DiagnosisResult | undefined | null): {
    label: string;
    Icon: LucideIcon;
    value: string | undefined;
    sub?: string;
    tags?: string[];
  }[] {
    if (!r) return [];
    return [
      { label: "사상체질", Icon: User, value: r.constitution },
      {
        label: "한의학적 진단",
        Icon: Stethoscope,
        value: r.diagnosis,
        sub: `양방: ${r.western_diagnosis}`,
      },
      {
        label: "한약 처방",
        Icon: Leaf,
        value: r.prescription,
        tags: r.herbs,
      },
      {
        label: "침 처방",
        Icon: MapPin,
        value: r.acupuncture?.join(" · "),
      },
    ];
  }

  const resultCards = buildResultCards(result);
  const claudeResultCards = buildResultCards(result?.claudeBased);

  const historySections: { key: string; Icon: LucideIcon }[] = [
    { key: "사상체질", Icon: User },
    { key: "한의학적 진단", Icon: Stethoscope },
    { key: "한약 처방", Icon: Leaf },
    { key: "침 처방", Icon: MapPin },
  ];

  const historyMemoSections: { key: string; Icon: LucideIcon }[] = [
    { key: "메모", Icon: FileText },
    { key: "병력", Icon: Clipboard },
  ];

  function renderHistorySection(
    sections: Record<string, string> | null,
    sectionKey: string,
    Icon: LucideIcon,
    keyPrefix = "",
  ) {
    const content = sections?.[sectionKey] || "-";
    const isHerbs = sectionKey === "한약 처방";
    const isAcu = sectionKey === "침 처방";

    if (isHerbs && content !== "-") {
      const lines = content
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const prescName = lines[0];
      const ingredients = lines
        .slice(1)
        .flatMap((l) => l.split(/[,，]/).map((s) => s.trim()))
        .filter(Boolean);
      return (
        <div key={`${keyPrefix}${sectionKey}`}>
          <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-1.5">
            <Icon className="w-3.5 h-3.5" /> {sectionKey}
          </div>
          <div className="text-sm font-semibold text-[#EF6600] mb-1.5">
            {prescName}
          </div>
          {ingredients.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {ingredients.map((t, i) => (
                <span
                  key={i}
                  className="inline-block bg-bg border border-border rounded px-2 py-0.5 text-xs text-text"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    const tags =
      isAcu && content !== "-"
        ? content
            .split(/[,，\n]/)
            .map((s) => s.trim())
            .filter(Boolean)
        : null;
    return (
      <div key={`${keyPrefix}${sectionKey}`}>
        <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-1.5">
          <Icon className="w-3.5 h-3.5" /> {sectionKey}
        </div>
        {tags ? (
          <div className="flex flex-wrap gap-1">
            {tags.map((t, i) => (
              <span
                key={i}
                className="inline-block bg-bg border border-border rounded px-2 py-0.5 text-xs text-text"
              >
                {t}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-sm text-text whitespace-pre-wrap">
            {content}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-52px)] overflow-hidden">
      {/* 왼쪽 환자 패널 */}
      <div className="hidden sm:flex w-[260px] flex-shrink-0 bg-card border-r border-border flex-col">
        <div className="p-3 border-b border-border">
          <div className="text-xs font-medium text-text uppercase tracking-wide mb-2">
            환자 목록
          </div>
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
        <div className="flex-1 overflow-y-auto py-1">
          {patientsLoading ? (
            <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto mt-8" />
          ) : displayedPatients.length === 0 ? (
            <div className="text-xs text-muted text-center py-8">
              등록된 환자가 없습니다
            </div>
          ) : (
            filtered.map((patient) => (
              <div
                key={patient.id}
                className={`group flex items-center gap-2.5 px-3.5 py-2.5 cursor-pointer transition-all border-l-[2.5px] ${
                  selectedPatient?.id === patient.id
                    ? "bg-bg border-l-[#EF6600]"
                    : "border-l-transparent hover:bg-bg"
                }`}
                onClick={() => {
                  setSelectedPatient(patient);
                  setResult(null);
                  setRecordsLastFetchedFor(null);
                  setSavedSymptomText(undefined);
                  setActiveTab("record");
                  setMemoEditing(false);
                  setMemoSectionOpen(false);
                  setMemo(patient.memo || "");
                  setRecordMedicalHistory({ hasHistory: false, text: "" });
                }}
              >
                <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text">
                    {patient.name}
                  </div>
                  <div className="text-xs text-subtext">
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
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-border transition-all flex-shrink-0"
                  title="환자 정보 수정"
                >
                  <Pencil className="w-3 h-3 text-subtext" />
                </button>
              </div>
            ))
          )}
        </div>
        {selectedPatient && (
          <div className="border-t border-border">
            <button
              onClick={() => {
                if (!memoEditing) setMemoSectionOpen((p) => !p);
              }}
              className="w-full flex items-center justify-between px-3 py-2 text-left"
            >
              <span className="text-xs text-subtext uppercase tracking-wide">
                메모
              </span>
              {memoSectionOpen ? (
                <ChevronUp className="w-3 h-3 text-muted" />
              ) : (
                <ChevronDown className="w-3 h-3 text-muted" />
              )}
            </button>
            {memoSectionOpen && (
              <div className="px-3 pb-3 flex flex-col gap-1.5">
                {!memoEditing && (
                  <div className="flex justify-end">
                    <button
                      onClick={() => {
                        setMemoEditing(true);
                        setMemoDraft(selectedPatient.memo || "");
                      }}
                      className="p-1 rounded hover:bg-border transition-all"
                    >
                      <Pencil className="w-3 h-3 text-subtext" />
                    </button>
                  </div>
                )}
                {memoEditing ? (
                  <>
                    <textarea
                      value={memoDraft}
                      onChange={(e) => setMemoDraft(e.target.value)}
                      autoFocus
                      rows={3}
                      className="w-full bg-fill border border-border rounded-md px-2 py-1.5 text-xs text-text outline-none focus:border-[#EF6600] resize-none transition-colors"
                    />
                    <div className="flex gap-1.5">
                      <button
                        onClick={handleSaveMemo}
                        className="flex-1 bg-[#EF6600] text-white rounded-md py-1.5 text-xs hover:opacity-90 transition-opacity"
                      >
                        저장
                      </button>
                      <button
                        onClick={() => setMemoEditing(false)}
                        className="flex-1 border border-border-strong rounded-md py-1.5 text-xs text-subtext hover:border-text transition-all"
                      >
                        취소
                      </button>
                    </div>
                  </>
                ) : (
                  <div
                    onClick={() => {
                      setMemoEditing(true);
                      setMemoDraft(selectedPatient.memo || "");
                    }}
                    className="text-xs text-text cursor-pointer hover:bg-fill rounded-md px-2 py-1.5 min-h-[28px] whitespace-pre-wrap transition-colors"
                  >
                    {selectedPatient.memo ? (
                      selectedPatient.memo
                    ) : (
                      <span className="text-muted">
                        클릭하여 메모 입력...
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        <div className="p-3 border-t border-border flex flex-col gap-2">
          <button
            onClick={() => excelInputRef.current?.click()}
            disabled={importLoading}
            className="w-full border border-border-strong rounded-md py-2 text-xs text-subtext hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" /> {importLoading ? "가져오는 중..." : "환자 정보 가져오기"}
          </button>
          <input
            ref={excelInputRef}
            type="file"
            accept=".xls,.xlsx"
            className="hidden"
            onChange={handleExcelImport}
          />
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
        {/* 모바일 환자 정보 바 */}
        <div className="sm:hidden bg-card border-b border-border flex items-center justify-between px-4 py-2 flex-shrink-0">
          {selectedPatient ? (
            <>
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white">
                  {selectedPatient.name[0]}
                </div>
                <span className="text-sm font-medium text-text">
                  {selectedPatient.name}
                </span>
              </div>
              <button
                onClick={() => router.push("/patients")}
                className="text-xs text-subtext border border-border rounded-md px-3 py-1 hover:border-[#EF6600] hover:text-[#EF6600] transition-all"
              >
                변경
              </button>
            </>
          ) : (
            <button
              onClick={() => router.push("/patients")}
              className="text-sm text-[#EF6600] font-medium"
            >
              환자를 선택하세요 →
            </button>
          )}
        </div>
        <div className="flex border-b border-border bg-card flex-shrink-0">
          {(["record", "result", "history", "ask"] as const).map((tab, i) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3.5 text-xs transition-all border-b-2 ${
                activeTab === tab
                  ? "text-[#EF6600] border-[#EF6600]"
                  : "text-subtext border-transparent hover:text-text"
              }`}
            >
              {["진료 기록", "진단 결과", "진료 이력", "한의학 검색"][i]}
            </button>
          ))}
        </div>

        <div
          className={`flex-1 p-5 ${activeTab === "ask" ? "overflow-hidden flex flex-col" : "overflow-y-auto"}`}
        >
          {!selectedPatient && activeTab !== "ask" && (
            <div className="text-sm text-muted text-center py-16">
              왼쪽에서 환자를 선택해주세요
            </div>
          )}

          {/* 진료 녹음 탭 */}
          {activeTab === "record" && selectedPatient && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-card border border-border rounded-lg p-5">
                <div className="text-xs text-subtext uppercase tracking-wide mb-3">
                  음성 녹음
                </div>
                <div className="text-center p-6 bg-fill border border-border rounded-lg mb-3">
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
                  <div className="text-sm font-medium text-text mb-1">
                    {isRecording
                      ? "녹음 중..."
                      : audioFiles.length > 0
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
                  <div className="text-lg font-light text-text tabular-nums">
                    {timer}
                  </div>
                  <div className="text-xs text-subtext mt-1">
                    {isRecording
                      ? "버튼을 눌러 중지하세요"
                      : "버튼을 눌러 녹음을 시작하세요"}
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="text-xs text-subtext uppercase tracking-wide mb-3">
                    파일 업로드
                  </div>
                  <label className="border-[1.5px] border-dashed border-border-strong rounded-lg p-5 text-center cursor-pointer hover:border-[#EF6600] transition-all bg-fill block">
                    <FolderOpen className="w-7 h-7 text-muted mx-auto mb-2" />
                    <div className="text-xs text-subtext">
                      {audioFiles.length > 0
                        ? `${audioFiles.length}개 파일 선택됨 (추가 선택 가능)`
                        : "파일을 드래그하거나 클릭"}
                    </div>
                    <div className="text-xs text-muted mt-1">
                      mp3, wav, m4a · 최대 100MB · 끊긴 구간별로 여러 파일 업로드 가능
                    </div>
                    <input
                      type="file"
                      accept=".mp3,.wav,.m4a,.webm"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        if (!e.target.files) return;
                        setAudioFiles((prev) => [
                          ...prev,
                          ...Array.from(e.target.files as FileList),
                        ]);
                        e.target.value = "";
                      }}
                    />
                  </label>
                  {audioFiles.length > 0 && (
                    <ul className="mt-3 flex flex-col gap-1.5">
                      {audioFiles.map((file, i) => (
                        <li
                          key={`${file.name}-${i}`}
                          className="flex items-center justify-between gap-2 bg-fill border border-border rounded-md px-3 py-2 text-xs text-text"
                        >
                          <span className="truncate">
                            {i + 1}. {file.name}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              setAudioFiles((prev) =>
                                prev.filter((_, idx) => idx !== i),
                              )
                            }
                            className="text-muted hover:text-[#EF6600] flex-shrink-0"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="bg-card border border-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setRecordMemoOpen((p) => !p)}
                    className="w-full flex items-center justify-between px-5 py-3 text-left"
                  >
                    <span className="text-xs text-subtext uppercase tracking-wide">
                      추가 메모
                    </span>
                    {recordMemoOpen ? (
                      <ChevronUp className="w-3.5 h-3.5 text-muted" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-muted" />
                    )}
                  </button>
                  {recordMemoOpen && (
                    <div className="px-5 pb-5 border-t border-border pt-3">
                      <textarea
                        value={memo}
                        onChange={(e) => setMemo(e.target.value)}
                        placeholder="주요 증상, 특이사항...&#10;예) 소화불량 3개월, 스트레스"
                        className="w-full bg-fill border border-border rounded-md p-3 text-xs text-text outline-none focus:border-[#EF6600] resize-none min-h-[80px] transition-colors"
                      />
                    </div>
                  )}
                </div>
                <div className="bg-card border border-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setRecordHistoryOpen((p) => !p)}
                    className="w-full flex items-center justify-between px-5 py-3 text-left"
                  >
                    <span className="text-xs text-subtext uppercase tracking-wide">
                      병력
                    </span>
                    {recordHistoryOpen ? (
                      <ChevronUp className="w-3.5 h-3.5 text-muted" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-muted" />
                    )}
                  </button>
                  {recordHistoryOpen && (
                    <div className="px-5 pb-5 border-t border-border pt-3">
                      <div className="flex gap-4 mb-2">
                        {["없음", "있음"].map((opt) => (
                          <label
                            key={opt}
                            className="flex items-center gap-1.5 cursor-pointer"
                          >
                            <input
                              type="radio"
                              name="record-medical-history"
                              checked={
                                opt === "있음"
                                  ? recordMedicalHistory.hasHistory
                                  : !recordMedicalHistory.hasHistory
                              }
                              onChange={() =>
                                setRecordMedicalHistory((prev) => ({
                                  ...prev,
                                  hasHistory: opt === "있음",
                                }))
                              }
                              className="accent-[#EF6600]"
                            />
                            <span className="text-xs text-text">
                              {opt}
                            </span>
                          </label>
                        ))}
                      </div>
                      {recordMedicalHistory.hasHistory && (
                        <textarea
                          value={recordMedicalHistory.text}
                          onChange={(e) =>
                            setRecordMedicalHistory((prev) => ({
                              ...prev,
                              text: e.target.value,
                            }))
                          }
                          placeholder="병력을 입력하세요"
                          rows={3}
                          className="w-full bg-fill border border-border rounded-md p-3 text-xs text-text outline-none focus:border-[#EF6600] resize-none transition-colors"
                        />
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="sm:col-span-2">
                <div className="bg-card border border-border rounded-lg p-5">
                  <div className="text-xs text-subtext uppercase tracking-wide mb-3">
                    증상 직접 입력{" "}
                    <span className="normal-case text-muted">
                      (음성과 함께 추가 입력 가능)
                    </span>
                  </div>
                  <textarea
                    value={symptomText}
                    onChange={(e) => setSymptomText(e.target.value)}
                    placeholder="증상을 자세히 입력하세요&#10;예) 손발이 차고 식은땀이 나며 소화가 잘 안 됨. 평소 피로감이 많고 추위를 탐."
                    className="w-full bg-fill border border-border rounded-md p-3 text-xs text-text outline-none focus:border-[#EF6600] resize-none min-h-[90px] transition-colors"
                  />
                </div>
              </div>
              <div className="sm:col-span-2">
                <button
                  onClick={startAnalysis}
                  disabled={
                    loading || (audioFiles.length === 0 && !symptomText.trim())
                  }
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
                <div className="text-sm text-muted text-center py-12">
                  아직 진단 결과가 없습니다.
                </div>
              ) : (
                <>
                  <BetaFeedbackBanner />
                  {(result.chiefComplaintSummary || chiefComplaint) && (
                    <div className="mb-3 bg-card border border-border rounded-lg p-4">
                      <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-2">
                        <FileText className="w-3.5 h-3.5" /> 주소증
                      </div>
                      <div className="text-sm text-text whitespace-pre-wrap">
                        {result.chiefComplaintSummary || chiefComplaint}
                      </div>
                    </div>
                  )}
                  {claudeResultCards.length > 0
                    ? resultCards.map(({ label, Icon, value, sub, tags }, i) => {
                        const c2 = claudeResultCards[i];
                        return (
                          <div key={i} className="mb-3 last:mb-0">
                            <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-2">
                              <Icon className="w-3.5 h-3.5" /> {label}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              <div className="bg-card border border-border rounded-lg p-4 relative">
                                <button
                                  onClick={() =>
                                    navigator.clipboard.writeText(`${label}: ${value}`)
                                  }
                                  className="absolute top-3 right-3 bg-fill border border-border rounded-md px-2 py-1 text-xs text-subtext hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center gap-1"
                                >
                                  <Clipboard className="w-3 h-3" /> 복사
                                </button>
                                <div className="flex items-center gap-1.5 text-[10px] font-semibold text-[#EF6600] uppercase tracking-wide mb-1.5">
                                  <FolderOpen className="w-3 h-3" /> 결과 1
                                </div>
                                <div
                                  className={`text-sm font-semibold ${tags ? "text-[#EF6600]" : "text-text"}`}
                                >
                                  {value}
                                </div>
                                {sub && (
                                  <div className="text-xs text-subtext mt-1">
                                    {sub}
                                  </div>
                                )}
                                {tags && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {tags.map((t, j) => (
                                      <span
                                        key={j}
                                        className="px-2 py-0.5 bg-fill border border-border rounded text-xs text-subtext"
                                      >
                                        {t}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div className="bg-card border border-border rounded-lg p-4 relative">
                                <button
                                  onClick={() =>
                                    navigator.clipboard.writeText(`${label}: ${c2.value}`)
                                  }
                                  className="absolute top-3 right-3 bg-fill border border-border rounded-md px-2 py-1 text-xs text-subtext hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center gap-1"
                                >
                                  <Clipboard className="w-3 h-3" /> 복사
                                </button>
                                <div className="flex items-center gap-1.5 text-[10px] font-semibold text-subtext uppercase tracking-wide mb-1.5">
                                  <Sparkles className="w-3 h-3" /> 결과 2
                                </div>
                                <div
                                  className={`text-sm font-semibold ${c2.tags ? "text-[#EF6600]" : "text-text"}`}
                                >
                                  {c2.value}
                                </div>
                                {c2.sub && (
                                  <div className="text-xs text-subtext mt-1">
                                    {c2.sub}
                                  </div>
                                )}
                                {c2.tags && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {c2.tags.map((t, j) => (
                                      <span
                                        key={j}
                                        className="px-2 py-0.5 bg-fill border border-border rounded text-xs text-subtext"
                                      >
                                        {t}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {resultCards.map(({ label, Icon, value, sub, tags }, i) => (
                          <div
                            key={i}
                            className="bg-card border border-border rounded-lg p-4 relative"
                          >
                            <button
                              onClick={() =>
                                navigator.clipboard.writeText(`${label}: ${value}`)
                              }
                              className="absolute top-3 right-3 bg-fill border border-border rounded-md px-2 py-1 text-xs text-subtext hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center gap-1"
                            >
                              <Clipboard className="w-3 h-3" /> 복사
                            </button>
                            <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-2">
                              <Icon className="w-3.5 h-3.5" /> {label}
                            </div>
                            <div
                              className={`text-sm font-semibold ${tags ? "text-[#EF6600]" : "text-text"}`}
                            >
                              {value}
                            </div>
                            {sub && (
                              <div className="text-xs text-subtext mt-1">
                                {sub}
                              </div>
                            )}
                            {tags && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {tags.map((t, j) => (
                                  <span
                                    key={j}
                                    className="px-2 py-0.5 bg-fill border border-border rounded text-xs text-subtext"
                                  >
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  {loadingResult2 && (
                    <div className="flex items-center gap-2 text-xs text-subtext mt-2">
                      <div className="w-3 h-3 border-2 border-border border-t-[#EF6600] rounded-full animate-spin" />
                      결과 2 (일반 한의학 기반) 분석 중...
                    </div>
                  )}
                  <div className="mt-3 bg-card border border-border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setResultMemoOpen((p) => !p)}
                      className="w-full flex items-center justify-between px-4 py-3 text-left"
                    >
                      <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide">
                        <FileText className="w-3.5 h-3.5" /> 메모 · 병력
                      </div>
                      {resultMemoOpen ? (
                        <ChevronUp className="w-3.5 h-3.5 text-muted" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-muted" />
                      )}
                    </button>
                    {resultMemoOpen && (
                      <div className="border-t border-border p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-2">
                            <FileText className="w-3.5 h-3.5" /> 메모
                          </div>
                          <div className="text-sm text-text whitespace-pre-wrap">
                            {memo.trim() || selectedPatient?.memo || "-"}
                          </div>
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-2">
                            <Clipboard className="w-3.5 h-3.5" /> 병력
                          </div>
                          <div className="text-sm text-text whitespace-pre-wrap">
                            {recordMedicalHistory.hasHistory &&
                            recordMedicalHistory.text.trim()
                              ? recordMedicalHistory.text.trim()
                              : "없음"}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="bg-[#232323] rounded-lg p-5 mt-4">
                    <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                      <div className="flex items-center gap-1.5 text-xs text-[#A09892] uppercase tracking-wide">
                        <Clipboard className="w-3.5 h-3.5" /> 동의보감 차팅용 전체
                        복사
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        {result.claudeBased && (
                          <>
                            <button
                              onClick={() => copyResult("result1")}
                              className={`text-xs px-2.5 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                                copied === "result1"
                                  ? "bg-green-600 text-white"
                                  : "bg-[#3A3A3A] text-white hover:opacity-90"
                              }`}
                            >
                              {copied === "result1" ? (
                                <>
                                  <Check className="w-3.5 h-3.5" /> 복사 완료!
                                </>
                              ) : (
                                <>
                                  <Clipboard className="w-3.5 h-3.5" /> 결과 1 전체
                                  복사
                                </>
                              )}
                            </button>
                            <button
                              onClick={() => copyResult("result2")}
                              className={`text-xs px-2.5 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                                copied === "result2"
                                  ? "bg-green-600 text-white"
                                  : "bg-[#3A3A3A] text-white hover:opacity-90"
                              }`}
                            >
                              {copied === "result2" ? (
                                <>
                                  <Check className="w-3.5 h-3.5" /> 복사 완료!
                                </>
                              ) : (
                                <>
                                  <Clipboard className="w-3.5 h-3.5" /> 결과 2 전체
                                  복사
                                </>
                              )}
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => copyResult("both")}
                          className={`text-xs px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                            copied === "both"
                              ? "bg-green-600 text-white"
                              : "bg-[#EF6600] text-white hover:opacity-90"
                          }`}
                        >
                          {copied === "both" ? (
                            <>
                              <Check className="w-3.5 h-3.5" /> 복사 완료!
                            </>
                          ) : (
                            <>
                              <Clipboard className="w-3.5 h-3.5" /> 전체 복사
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                    <pre className="text-xs text-white/70 leading-relaxed whitespace-pre-wrap font-sans">
                      {buildResultText("both")}
                    </pre>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted mt-3 p-3 bg-fill border border-border rounded-lg">
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
                    <button
                      onClick={handlePrint}
                      className="flex-1 border border-border-strong rounded-md py-2.5 text-xs text-subtext hover:border-text transition-all flex items-center justify-center gap-1.5"
                    >
                      <Printer className="w-3.5 h-3.5" /> 인쇄
                    </button>
                    <button
                      onClick={() => {
                        setActiveTab("record");
                        setFeedbackAvailable(false);
                        setFeedbackHelpful(null);
                        setFeedbackComment("");
                        setFeedbackSubmitted(false);
                        setFeedbackRecordId(null);
                        setResultMemoOpen(false);
                      }}
                      className="flex-1 border border-border-strong rounded-md py-2.5 text-xs text-subtext hover:border-text transition-all flex items-center justify-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> 새 진료
                    </button>
                  </div>
                  {feedbackRecordId && (
                    <div className="mt-3 bg-card border border-border rounded-lg p-4">
                      {feedbackSubmitted ? (
                        <div className="flex items-center justify-center gap-2 py-1 text-sm text-subtext">
                          <CircleCheck className="w-4 h-4 text-[#EF6600]" />
                          피드백 감사합니다
                        </div>
                      ) : (
                        <>
                          <div className="text-xs text-subtext mb-3 text-center">
                            이 진단이 도움이 됐나요?
                          </div>
                          <div className="flex gap-2 justify-center mb-3">
                            <button
                              onClick={() => setFeedbackHelpful(true)}
                              className={`flex items-center gap-1.5 px-4 py-2 rounded-md border text-xs transition-all ${
                                feedbackHelpful === true
                                  ? "bg-[#EF6600] text-white border-[#EF6600]"
                                  : "border-border text-subtext hover:border-[#EF6600] hover:text-[#EF6600]"
                              }`}
                            >
                              <ThumbsUp className="w-3.5 h-3.5" /> 도움됨
                            </button>
                            <button
                              onClick={() => setFeedbackHelpful(false)}
                              className={`flex items-center gap-1.5 px-4 py-2 rounded-md border text-xs transition-all ${
                                feedbackHelpful === false
                                  ? "bg-[#232323] dark:bg-border-strong text-white border-text"
                                  : "border-border text-subtext hover:border-text hover:text-text"
                              }`}
                            >
                              <ThumbsDown className="w-3.5 h-3.5" /> 도움 안 됨
                            </button>
                          </div>
                          {feedbackHelpful !== null && (
                            <>
                              <textarea
                                value={feedbackComment}
                                onChange={(e) =>
                                  setFeedbackComment(e.target.value)
                                }
                                placeholder="추가 의견이 있으시면 입력해주세요 (선택)"
                                rows={2}
                                className="w-full bg-fill border border-border rounded-md px-3 py-2 text-xs text-text outline-none focus:border-[#EF6600] resize-none mb-2 transition-colors"
                              />
                              <button
                                onClick={handleFeedback}
                                className="w-full bg-[#EF6600] text-white rounded-md py-2 text-xs hover:opacity-90 transition-opacity"
                              >
                                피드백 제출
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* 진료 이력 탭 */}
          {activeTab === "history" && selectedPatient && (
            <div className="overflow-y-auto">
              {recordsLoading ? (
                <div className="text-sm text-muted text-center py-12">
                  불러오는 중...
                </div>
              ) : records.length === 0 ? (
                <div className="text-sm text-muted text-center py-12">
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
                      const blocks = splitResultBlocks(r.chart_structured);
                      const sections1 = blocks
                        ? parseChartSections(blocks.result1)
                        : sections;
                      const sections2 = blocks
                        ? parseChartSections(blocks.result2)
                        : null;
                      const isOpen = expandedRecord === r.id;
                      const diagSummary = sections1?.["한의학적 진단"]
                        ?.split("\n")[0]
                        ?.trim();
                      const prescSummary = sections1?.["한약 처방"]
                        ?.split("\n")[0]
                        ?.trim();
                      const ccRaw = sections?.["주소증"]
                        ?.replace(/\n*■[^\n]*$/, "")
                        ?.trim();
                      const ccText = ccRaw || r.raw_transcription;
                      return (
                        <div
                          key={r.id}
                          className="bg-card border border-border rounded-lg overflow-hidden"
                        >
                          <div className="flex items-stretch">
                            <button
                              onClick={() =>
                                setExpandedRecord(isOpen ? null : r.id)
                              }
                              className="flex-1 flex items-start justify-between px-4 py-3 text-left gap-2"
                            >
                              <div className="flex flex-col gap-0.5 min-w-0">
                                <span className="text-sm font-medium text-text">
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
                                  <span className="text-xs text-subtext truncate">
                                    {[diagSummary, prescSummary]
                                      .filter(Boolean)
                                      .join(" · ")}
                                  </span>
                                )}
                              </div>
                              {isOpen ? (
                                <ChevronUp className="w-4 h-4 text-subtext flex-shrink-0 mt-0.5" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-subtext flex-shrink-0 mt-0.5" />
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteRecord(r.id)}
                              className="px-3 border-l border-border text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                              title="삭제"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          {isOpen && (
                            <div className="border-t border-border p-4 flex flex-col gap-4">
                              {ccText && (
                                <div>
                                  <button
                                    onClick={() =>
                                      setExpandedCC((prev) => {
                                        const next = new Set(prev);
                                        next.has(r.id)
                                          ? next.delete(r.id)
                                          : next.add(r.id);
                                        return next;
                                      })
                                    }
                                    className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-1.5 w-full text-left"
                                  >
                                    <FileText className="w-3.5 h-3.5" /> 주소증
                                    {expandedCC.has(r.id) ? (
                                      <ChevronUp className="w-3 h-3 ml-auto" />
                                    ) : (
                                      <ChevronDown className="w-3 h-3 ml-auto" />
                                    )}
                                  </button>
                                  {expandedCC.has(r.id) && (
                                    <div className="text-sm text-text whitespace-pre-wrap bg-bg rounded p-2">
                                      {ccText}
                                    </div>
                                  )}
                                </div>
                              )}
                              {blocks ? (
                                <>
                                  <div className="text-xs font-semibold text-[#EF6600] uppercase tracking-wide">
                                    ■ 결과 1
                                  </div>
                                  {historySections.map(({ key, Icon }) =>
                                    renderHistorySection(
                                      sections1,
                                      key,
                                      Icon,
                                      "r1-",
                                    ),
                                  )}
                                  <div className="text-xs font-semibold text-subtext uppercase tracking-wide">
                                    ■ 결과 2
                                  </div>
                                  {historySections.map(({ key, Icon }) =>
                                    renderHistorySection(
                                      sections2,
                                      key,
                                      Icon,
                                      "r2-",
                                    ),
                                  )}
                                </>
                              ) : sections ? (
                                historySections.map(({ key, Icon }) =>
                                  renderHistorySection(sections, key, Icon),
                                )
                              ) : (
                                <div className="text-sm text-text whitespace-pre-wrap">
                                  {r.chart_structured || "차트 내용 없음"}
                                </div>
                              )}
                              {(sections?.["메모"] ||
                                sections?.["병력"] ||
                                r.medical_history) && (
                                <div>
                                  <button
                                    onClick={() =>
                                      setHistoryMemoOpenIds((prev) => {
                                        const next = new Set(prev);
                                        next.has(r.id)
                                          ? next.delete(r.id)
                                          : next.add(r.id);
                                        return next;
                                      })
                                    }
                                    className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide w-full text-left"
                                  >
                                    <FileText className="w-3.5 h-3.5" /> 메모 ·
                                    병력
                                    {historyMemoOpenIds.has(r.id) ? (
                                      <ChevronUp className="w-3 h-3 ml-auto" />
                                    ) : (
                                      <ChevronDown className="w-3 h-3 ml-auto" />
                                    )}
                                  </button>
                                  {historyMemoOpenIds.has(r.id) && (
                                    <div className="flex flex-col gap-3 mt-2">
                                      {sections?.["메모"] && (
                                        <div>
                                          <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-1.5">
                                            <FileText className="w-3.5 h-3.5" />{" "}
                                            메모
                                          </div>
                                          <div className="text-sm text-text whitespace-pre-wrap">
                                            {sections["메모"]}
                                          </div>
                                        </div>
                                      )}
                                      {(sections?.["병력"] ||
                                        r.medical_history) && (
                                        <div>
                                          <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-1.5">
                                            <Clipboard className="w-3.5 h-3.5" />{" "}
                                            병력
                                          </div>
                                          <div className="text-sm text-text whitespace-pre-wrap">
                                            {sections?.["병력"] ||
                                              r.medical_history}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
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

          {activeTab === "ask" && (
            <div className="flex flex-col flex-1 min-h-0 gap-4">
              <div className="flex-1 flex flex-col gap-3 overflow-y-auto min-h-0">
                {askHistory.length === 0 && (
                  <div className="text-center py-16 text-muted">
                    <MessageCircle className="w-8 h-8 mx-auto mb-3 text-muted" />
                    <div className="text-sm">
                      한의학 관련 궁금한 점을 질문해보세요
                    </div>
                    <div className="text-xs mt-2 text-muted">
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
                      <div className="self-start bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                        {[0, 1, 2].map((j) => (
                          <div
                            key={j}
                            className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce"
                            style={{ animationDelay: `${j * 0.15}s` }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="self-start max-w-[75%] bg-card border border-border text-sm text-text rounded-2xl rounded-tl-sm px-4 py-2.5 leading-relaxed whitespace-pre-wrap">
                        {item.answer}
                      </div>
                    )}
                    {item.result && item.answer !== "" && (
                      <button
                        type="button"
                        onClick={() => openAskSavePicker(i)}
                        className="self-start flex items-center gap-1 text-xs text-subtext hover:text-[#EF6600] transition-colors px-1"
                      >
                        <Save className="w-3 h-3" /> 진료 기록에 저장
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <div className="pt-2 border-t border-border flex flex-col gap-2">
                <div className="flex gap-1 p-1 bg-fill border border-border rounded-lg w-fit">
                  <button
                    type="button"
                    onClick={() => setAskMode("ask")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === "ask"
                        ? "bg-card text-text shadow-sm"
                        : "text-subtext hover:text-text"
                    }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" /> 질문하기
                  </button>
                  <button
                    type="button"
                    onClick={() => setAskMode("diagnose")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === "diagnose"
                        ? "bg-card text-text shadow-sm"
                        : "text-subtext hover:text-text"
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
                    className="flex-1 bg-fill border border-border rounded-lg px-4 py-2.5 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
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

      {/* 한의학 검색 - 진료 기록 저장 항목 선택 모달 */}
      {askSavePicker !== null && askHistory[askSavePicker]?.result && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setAskSavePicker(null)}
        >
          <div
            className="bg-card rounded-xl w-full max-w-[420px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5">
              <div className="text-sm font-medium text-text mb-1">
                진료 기록에 저장할 항목 선택
              </div>
              <div className="text-xs text-subtext mb-4">
                {selectedPatient
                  ? `${selectedPatient.name} 환자에게 저장됩니다`
                  : "환자를 먼저 선택해주세요"}
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-3 mb-5">
                {(["r1", "r2"] as const).map((prefix) => {
                  const r =
                    prefix === "r1"
                      ? askHistory[askSavePicker]!.result!
                      : askHistory[askSavePicker]!.result!.claudeBased;
                  if (!r) return null;
                  return (
                    <div key={prefix}>
                      <div className="text-xs font-medium text-text mb-2">
                        {prefix === "r1"
                          ? "결과 1 (데이터셋 기반)"
                          : "결과 2 (AI 종합 소견)"}
                      </div>
                      <div className="flex flex-col gap-1.5">
                        {ASK_SAVE_FIELDS.map((f) => (
                          <label
                            key={f.key}
                            className="flex items-center gap-2 text-xs text-text"
                          >
                            <input
                              type="checkbox"
                              checked={
                                !!askSaveSelections[`${prefix}.${f.key}`]
                              }
                              onChange={(e) =>
                                setAskSaveSelections((prev) => ({
                                  ...prev,
                                  [`${prefix}.${f.key}`]: e.target.checked,
                                }))
                              }
                            />
                            {f.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleAskSave}
                  disabled={askSaving || !selectedPatient}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {askSaving ? "저장 중..." : "저장"}
                </button>
                <button
                  onClick={() => setAskSavePicker(null)}
                  className="flex-1 border border-border-strong rounded-md py-2.5 text-sm text-subtext hover:border-text hover:text-text transition-all"
                >
                  취소
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 저장 확인 모달 */}
      {showSaveModal && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowSaveModal(false)}
        >
          <div
            className="bg-card rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <div className="text-sm font-medium text-text mb-4">
                저장하시겠습니까?
              </div>
              {result?.claudeBased && (
                <div className="flex flex-col gap-2 mb-5 text-left">
                  {(
                    [
                      { value: "both", label: "결과 1 + 결과 2 모두 저장" },
                      { value: "result1", label: "결과 1만 저장" },
                      { value: "result2", label: "결과 2만 저장" },
                    ] as const
                  ).map((opt) => (
                    <label
                      key={opt.value}
                      className="flex items-center gap-2 text-xs text-text"
                    >
                      <input
                        type="radio"
                        name="saveSelection"
                        checked={saveSelection === opt.value}
                        onChange={() => setSaveSelection(opt.value)}
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
              )}
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
                  className="flex-1 border border-border-strong rounded-md py-2.5 text-sm text-subtext hover:border-text hover:text-text transition-all"
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
            className="bg-card rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <CircleCheck className="w-10 h-10 text-[#EF6600] mx-auto mb-3" />
              <div className="text-sm font-medium text-text mb-5">
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
            className="bg-card rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 text-center">
              <TriangleAlert className="w-10 h-10 text-[#EF6600] mx-auto mb-3" />
              <div className="text-sm font-medium text-text mb-5">
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
            className="bg-card rounded-xl w-full max-w-[400px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
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
                  <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
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
                    className="w-full bg-bg border border-border rounded-md px-4 py-2.5 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                    required={field.key === "name"}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
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
                          : "bg-card text-subtext border-border hover:border-[#EF6600]"
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

      {/* 엑셀 가져오기 결과 모달 */}
      {importResult && (
        <div className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4">
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
      {editPatient && (
        <div
          className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4"
          onClick={() => setEditPatient(null)}
        >
          <div
            className="bg-card rounded-xl w-full max-w-[360px] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">
                {editPatient.name} 정보 수정
              </div>
              <button
                onClick={() => setEditPatient(null)}
                className="text-subtext hover:text-text"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 flex flex-col gap-3">
              <div>
                <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
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
                  className="w-full border border-border-strong rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600]"
                />
              </div>
              <div>
                <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
                  메모
                </label>
                <textarea
                  value={editForm.memo}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, memo: e.target.value }))
                  }
                  placeholder="특이사항 등"
                  rows={3}
                  className="w-full border border-border-strong rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600] resize-none"
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
