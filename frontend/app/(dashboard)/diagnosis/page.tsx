"use client";
import { AcupointViewer, parseAcupointCodes } from "@/components/AcupointViewer";
import BetaFeedbackBanner from "@/components/BetaFeedbackBanner";
import { BillableItemPicker } from "@/components/billing/BillableItemPicker";
import {
  askDiagnosisStream,
  ChartingEvent,
  diagnoseText,
  finalizeRecord,
  updateKcdCode,
  uploadAndAnalyze,
} from "@/lib/api/diagnosis";
import { KcdSearchResult, KcdValidateResult, searchKcd, validateKcdCodes } from "@/lib/api/kcd";
import { ClaimStatement, getClaimStatement } from "@/lib/api/billing";
import {
  createPatient,
  deleteRecord,
  getPatient,
  getPatientRecords,
  getPatients,
  saveRecord,
  updatePatient,
} from "@/lib/api/patients";
import { getTodayQueue, QueueItem, updateQueueStatus } from "@/lib/api/queue";
import { useIsExpired } from "@/contexts/SubscriptionContext";
import { DiagnosisResult, Patient } from "@/types";
import {
  Check,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  Clipboard,
  FileText,
  FolderOpen,
  Leaf,
  MapPin,
  History,
  MessageCircle,
  Mic,
  Plus,
  Printer,
  Receipt,
  ReceiptText,
  Save,
  Search,
  Sparkles,
  Square,
  Stethoscope,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  TriangleAlert,
  User,
  X,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

const ASK_SAVE_FIELDS: { key: string; label: string }[] = [
  { key: "constitution", label: "사상체질" },
  { key: "diagnosis", label: "한의학적 진단 / 양방 대응" },
  { key: "prescription", label: "한약 처방" },
  { key: "acupuncture", label: "침 처방" },
];

function getQueueStatusLabel(status: QueueItem["status"]): { label: string; className: string } {
  if (status === "paid") return { label: "수납완료", className: "text-green-500" };
  if (status === "done") return { label: "진료완료", className: "text-blue-500" };
  return { label: "대기", className: "text-[#EF6600]" };
}

export default function DiagnosisPage() {
  const isExpired = useIsExpired();
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientPage, setPatientPage] = useState(1);
  const [patientHasMore, setPatientHasMore] = useState(true);
  const [patientLoadingMore, setPatientLoadingMore] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [activeTab, setActiveTab] = useState<
    "record" | "result" | "history" | "ask" | "billing"
  >("record");
  const [isRecording, setIsRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioFiles, setAudioFiles] = useState<File[]>([]);
  const [memo, setMemo] = useState("");
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingResult2, setLoadingResult2] = useState(false);
  const [historyCopied, setHistoryCopied] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    name: "",
    birth_date: "",
    gender: "",
    phone: "",
    rrn: "",
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
  const [recordClaimIds, setRecordClaimIds] = useState<Record<string, string>>({});
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [kcdQuery, setKcdQuery] = useState("");
  const [kcdResults, setKcdResults] = useState<KcdSearchResult[]>([]);
  const [kcdCodes, setKcdCodes] = useState<KcdSearchResult[]>([]);
  const [kcdDropdownOpen, setKcdDropdownOpen] = useState(false);
  const [kcdValidation, setKcdValidation] = useState<Record<string, KcdValidateResult>>({});
  const [showPastKcd, setShowPastKcd] = useState(false);
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
      kcd_code: string | null;
      secondary_kcd_codes: string[] | null;
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
  const [recordMedicalHistory, setRecordMedicalHistory] = useState<{
    hasHistory: boolean;
    text: string;
  }>({ hasHistory: false, text: "" });
  const [recordsLastFetchedFor, setRecordsLastFetchedFor] = useState<
    string | null
  >(null);
  const [importResult, setImportResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [expandedRecord, setExpandedRecord] = useState<string | null>(null);
  const [expandedCC, setExpandedCC] = useState<Set<string>>(new Set());
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [feedbackAvailable, setFeedbackAvailable] = useState(false);
  const [feedbackHelpful, setFeedbackHelpful] = useState<boolean | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackRecordId, setFeedbackRecordId] = useState<string | null>(null);
  const [resultMemoOpen, setResultMemoOpen] = useState(false);
  const [recordMemoOpen, setRecordMemoOpen] = useState(false);
  const [recordHistoryOpen, setRecordHistoryOpen] = useState(false);
  const [historyMemoOpenIds, setHistoryMemoOpenIds] = useState<Set<string>>(
    new Set(),
  );
  const [todayQueue, setTodayQueue] = useState<QueueItem[]>([]);
  const [selectedQueueItem, setSelectedQueueItem] = useState<QueueItem | null>(null);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueOpen, setQueueOpen] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const secondsRef = useRef(0);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const patientScrollRef = useRef<HTMLDivElement | null>(null);
  const urlPatientIdRef = useRef<string | null>(null);
  const PAGE_SIZE = 10;

  const filtered = patients.filter((p) => p.name.includes(search));
  const sortedQueue = [...todayQueue].sort((a, b) => {
    const aDone = a.status === "paid" ? 1 : 0;
    const bDone = b.status === "paid" ? 1 : 0;
    if (aDone !== bDone) return aDone - bDone;
    return new Date(a.checked_in_at).getTime() - new Date(b.checked_in_at).getTime();
  });
  const isOverviewTab = ["result", "history", "billing"].includes(activeTab);
  const recordsLoading =
    isOverviewTab &&
    !!selectedPatient &&
    recordsLastFetchedFor !== selectedPatient.id;

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      urlPatientIdRef.current = params.get("patientId");
    }
  }, []);

  useEffect(() => {
    getPatients(undefined, 1, PAGE_SIZE)
      .then((result) => {
        setPatients(result.items);
        setPatientHasMore(result.items.length === PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setPatientsLoading(false));
  }, []);

  useEffect(() => {
    getTodayQueue()
      .then(setTodayQueue)
      .catch(console.error)
      .finally(() => setQueueLoading(false));
  }, []);

  // 다음 페이지를 서버에서 조회해 patients에 append (홈 화면과 동일한 방식)
  const loadMorePatients = async () => {
    if (patientLoadingMore || !patientHasMore) return;
    const nextPage = patientPage + 1;
    setPatientLoadingMore(true);
    const result = await getPatients(undefined, nextPage, PAGE_SIZE).catch(() => ({ items: [] as Patient[], total: 0, page: nextPage, size: PAGE_SIZE }));
    const newItems = result.items;
    setPatients((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const deduped = newItems.filter((p) => !existingIds.has(p.id));
      return [...prev, ...deduped];
    });
    setPatientPage(nextPage);
    if (newItems.length < PAGE_SIZE) setPatientHasMore(false);
    setPatientLoadingMore(false);
  };

  useEffect(() => {
    const id = urlPatientIdRef.current;
    if (!id) return;
    urlPatientIdRef.current = null;
    getPatient(id)
      .then((p: Patient) => {
        setSelectedPatient(p);
        setSelectedQueueItem(null);
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
        if (latest) setCurrentRecordId(latest.id);
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
    setKcdQuery("");
    setKcdResults([]);
    setKcdCodes([]);
    setKcdValidation({});
    setKcdDropdownOpen(false);
    setShowPastKcd(false);
  }, [selectedPatient?.id]);

  useEffect(() => {
    if (kcdCodes.length === 0) {
      setKcdValidation({});
      return;
    }
    const genderMap: Record<string, "M" | "F"> = { male: "M", female: "F", 남성: "M", 여성: "F" };
    const patientGenderCode = selectedPatient ? genderMap[selectedPatient.gender] : undefined;
    validateKcdCodes(kcdCodes.map((c) => c.code), patientGenderCode)
      .then((res) => {
        const map: Record<string, KcdValidateResult> = {};
        for (const r of res.results) map[r.code] = r;
        setKcdValidation(map);
      })
      .catch(() => setKcdValidation({}));
  }, [kcdCodes, selectedPatient?.gender]);

  const pastKcdCodes = useMemo(() => {
    const codes = new Set<string>();
    for (const r of records) {
      if (r.kcd_code) codes.add(r.kcd_code);
      for (const c of r.secondary_kcd_codes ?? []) codes.add(c);
    }
    return Array.from(codes);
  }, [records]);

  function persistKcdCodes(codes: KcdSearchResult[]) {
    if (!currentRecordId) return; // 아직 저장 전인 신규 기록 — "저장" 시 함께 전송됨
    const [primary, ...secondary] = codes;
    updateKcdCode(currentRecordId, primary?.code ?? null, secondary.map((c) => c.code)).catch(() => {
      setErrorMessage("상병코드 저장에 실패했습니다.");
    });
  }

  function addKcdCode(item: KcdSearchResult) {
    setKcdCodes((prev) => {
      if (prev.some((c) => c.code === item.code)) return prev;
      const next = [...prev, item];
      persistKcdCodes(next);
      return next;
    });
  }

  function removeKcdCode(code: string) {
    setKcdCodes((prev) => {
      const next = prev.filter((c) => c.code !== code);
      persistKcdCodes(next);
      return next;
    });
  }

  function kcdWarnings(code: string): string[] {
    const v = kcdValidation[code];
    if (!v) return [];
    const warnings: string[] = [];
    if (v.reason === "not_found" || v.reason === "expired") {
      warnings.push("완전코드가 아닙니다. 하위 코드를 선택하세요");
    } else if (v.reason === "gender_mismatch") {
      const label = v.sex_restriction === "M" ? "남성" : "여성";
      warnings.push(`이 상병코드는 ${label}에게만 적용 가능합니다`);
    }
    if (v.is_notifiable) {
      warnings.push("법정감염병 상병입니다. 신고 의무를 확인하세요");
    }
    return warnings;
  }

  useEffect(() => {
    if (!kcdQuery.trim()) {
      setKcdResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchKcd(kcdQuery)
        .then(setKcdResults)
        .catch(() => setKcdResults([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [kcdQuery]);

  useEffect(() => {
    if (!isOverviewTab || !selectedPatient) return;
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
        .catch(() => { });
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

  async function handleAddPatient(e: React.FormEvent) {
    e.preventDefault();
    setAddLoading(true);
    try {
      const { rrn, ...basicFields } = newPatient;
      const created = await createPatient(basicFields);
      if (rrn.trim()) {
        await updatePatient(created.id, { rrn: rrn.trim() });
      }
      setPatientsLoading(true);
      const updated = await getPatients();
      setPatients(updated.items);
      setShowAddModal(false);
      setNewPatient({ name: "", birth_date: "", gender: "", phone: "", rrn: "" });
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

  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!result || !selectedPatient) return;
    const ccLine = result.chiefComplaintSummary?.trim() || chiefComplaint.trim() || "-";
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
      if (response?.id) {
        setCurrentRecordId(response.id);
      }
      if (kcdCodes.length > 0 && response?.id) {
        const [primary, ...secondary] = kcdCodes;
        await updateKcdCode(response.id, primary.code, secondary.map((c) => c.code)).catch(() => {
          setErrorMessage("상병코드 저장에 실패했습니다.");
        });
      }
      setSavedSymptomText(undefined);
      setFeedbackRecordId(response?.id ?? null);
      setFeedbackHelpful(null);
      setFeedbackComment("");
      setFeedbackSubmitted(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      setShowSavedModal(true);
      setTimeout(() => setShowSavedModal(false), 2000);
      if (
        selectedQueueItem &&
        (selectedQueueItem.status === "waiting" || selectedQueueItem.status === "in_progress")
      ) {
        updateQueueStatus(selectedQueueItem.id, "done")
          .then((updated) => {
            setTodayQueue((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
            setSelectedQueueItem(updated);
          })
          .catch(console.error);
      }
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

▶ 병력
${historyLine}

※ AI 참고용 / 최종 판단은 담당 한의사`;
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
      "white-space: pre-wrap;  font-size: 13px; line-height: 1.6; color: #232323; padding: 24px; margin: 0;";
    pre.textContent = text;
    printWindow.document.body.appendChild(pre);
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  async function handlePrescriptionPrint() {
    if (!result || !selectedPatient) return;
    const printWindow = window.open("", "_blank", "width=720,height=960");
    if (!printWindow) {
      setErrorMessage("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = localStorage.getItem("token");
    const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

    let doctorName = "담당 한의사";
    let licenseNumber = "-";
    let hospitalName = "-";
    try {
      const meRes = await fetch(`${base}/api/auth/me`, { headers: authHeaders });
      if (meRes.ok) {
        const me = await meRes.json();
        if (me.name) doctorName = me.name;
        if (me.license_number) licenseNumber = me.license_number;
        if (me.hospital_id) {
          const hospRes = await fetch(`${base}/api/hospitals/${me.hospital_id}`, { headers: authHeaders });
          if (hospRes.ok) {
            const hosp = await hospRes.json();
            if (hosp.name) hospitalName = hosp.name;
          }
        }
      }
    } catch { }

    const target =
      saveSelection === "result2" && result.claudeBased
        ? result.claudeBased
        : result;

    const today = new Date().toLocaleDateString("ko-KR");
    const birthDate = selectedPatient.birth_date
      ? selectedPatient.birth_date.replace(/(\d{4})-(\d{2})-(\d{2})/, "$1년 $2월 $3일")
      : "-";

    const herbRows = (target.herbs ?? []).length > 0
      ? (target.herbs ?? []).map((h) => {
        const m = h.match(/^(.+?)\s+(\d[\w.]*)$/);
        const name = m ? m[1] : h;
        const dosage = m ? m[2] : "-";
        return `<tr><td>${name}</td><td>${dosage}</td></tr>`;
      }).join("")
      : `<tr><td colspan="2" style="text-align:center;color:#888">-</td></tr>`;

    const acuSection =
      (target.acupuncture ?? []).length > 0
        ? `<div class="section-label">침 처방</div>
<div class="acu">${(target.acupuncture ?? []).join(", ")}</div>`
        : "";

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>처방전 - ${selectedPatient.name}</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:28px 36px;max-width:600px;margin:0 auto}`
      + `.hospital{text-align:center;font-size:13px;font-weight:600;margin-bottom:6px}`
      + `h1{font-size:22px;font-weight:bold;text-align:center;letter-spacing:10px;margin-bottom:10px}`
      + `hr{border:none;border-top:1.5px solid #000;margin:10px 0}`
      + `hr.thin{border-top:1px solid #ccc;margin:8px 0}`
      + `.grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px 16px;font-size:13px;margin:8px 0}`
      + `.item{display:flex;gap:6px;align-items:baseline}`
      + `.lbl{color:#444;min-width:60px;font-weight:500;flex-shrink:0}`
      + `.full{display:flex;gap:6px;font-size:13px;margin:6px 0;align-items:baseline}`
      + `.full .lbl{min-width:60px;flex-shrink:0}`
      + `.section-label{font-size:12px;font-weight:600;margin:12px 0 4px;color:#333}`
      + `table{width:100%;border-collapse:collapse;font-size:12px;margin:4px 0}`
      + `th{border:1px solid #999;padding:5px 8px;background:#f5f5f5;font-weight:500;text-align:left}`
      + `td{border:1px solid #ccc;padding:5px 8px;text-align:left}`
      + `.usage{font-size:13px;margin:8px 0}`
      + `.acu{font-size:13px;margin-bottom:8px}`
      + `.notice{margin-top:16px;font-size:11px;color:#888;border-top:1px dashed #bbb;padding-top:8px}`
      + `@media print{body{padding:0}@page{margin:15mm;size:A4}}`
      + `</style></head><body>`
      + `<div class="hospital">${hospitalName}</div>`
      + `<h1>처  방  전</h1>`
      + `<hr/>`
      + `<div class="grid2">`
      + `<div class="item"><span class="lbl">환자명</span><span>${selectedPatient.name}</span></div>`
      + `<div class="item"><span class="lbl">생년월일</span><span>${birthDate}</span></div>`
      + `<div class="item"><span class="lbl">처방일</span><span>${today}</span></div>`
      + `<div class="item"><span class="lbl">면허번호</span><span>${licenseNumber}</span></div>`
      + `</div>`
      + `<div class="full"><span class="lbl">한의사명</span><span>${doctorName}</span></div>`
      + `<hr/>`
      + `<div class="full"><span class="lbl">처방명</span><span>${target.prescription || "-"}</span></div>`
      + `<div class="section-label">약재 목록</div>`
      + `<table><thead><tr><th>약재명</th><th>용량</th></tr></thead>`
      + `<tbody>${herbRows}</tbody></table>`
      + `<hr class="thin"/>`
      + `<div class="usage">용법: 1일 3회, 식후 30분</div>`
      + acuSection
      + `<hr/>`
      + `<div class="notice">※ 본 처방전은 AI 보조 도구를 활용한 참고용이며, 최종 처방은 담당 한의사의 판단에 따릅니다.</div>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  async function handleReceiptPrint(claimId?: string) {
    if (!claimId) {
      setErrorMessage("청구 정보가 없습니다. 청구 탭에서 항목을 등록한 뒤 다시 시도해주세요.");
      return;
    }
    const printWindow = window.open("", "_blank", "width=620,height=880");
    if (!printWindow) {
      setErrorMessage("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    let statement: ClaimStatement;
    try {
      statement = await getClaimStatement(claimId);
    } catch {
      printWindow.close();
      setErrorMessage("영수증 데이터를 불러오지 못했습니다.");
      return;
    }

    const won = (n: number) => n.toLocaleString() + "원";
    const today = new Date().toLocaleDateString("ko-KR");
    const sum = (rows: ClaimStatement["procedures"]) => rows.reduce((a, p) => a + p.amount, 0);

    // claim_line_items 기반 항목별 금액 (hang: 01=진찰료 04=시술및처치료 11=투약료 05=검사료 09=비급여)
    const itemRows = [
      { label: "진찰료", amount: sum(statement.procedures.filter((p) => p.hang === "01")) },
      { label: "시술료", amount: sum(statement.procedures.filter((p) => p.hang === "04")) },
      { label: "투약료", amount: sum(statement.procedures.filter((p) => p.hang === "11")) },
      { label: "검사료", amount: sum(statement.procedures.filter((p) => p.hang === "05")) },
      {
        label: "비급여",
        amount: sum(statement.procedures.filter((p) => p.hang === "09" || p.is_non_benefit)),
      },
    ].filter((r) => r.amount > 0);

    const itemRowsHtml =
      itemRows.length > 0
        ? itemRows
            .map((r) => `<tr><td class="item-name">${r.label}</td><td class="amount">${won(r.amount)}</td></tr>`)
            .join("")
        : `<tr><td class="item-name" colspan="2" style="text-align:center;color:#888">청구 항목이 없습니다</td></tr>`;

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>영수증 - ${statement.patient_name}</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:28px 36px;max-width:560px;margin:0 auto}`
      + `h1{font-size:18px;font-weight:bold;text-align:center;letter-spacing:6px;margin-bottom:3px}`
      + `.subtitle{text-align:center;font-size:11px;color:#555;margin-bottom:12px}`
      + `hr{border:none;border-top:1.5px solid #000;margin:10px 0}`
      + `hr.thin{border-top:1px solid #ccc;margin:8px 0}`
      + `.grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px 16px;font-size:13px;margin:8px 0}`
      + `.item{display:flex;gap:6px;align-items:baseline}`
      + `.lbl{color:#444;min-width:72px;font-weight:500;flex-shrink:0}`
      + `table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}`
      + `th{border:1px solid #999;padding:6px 10px;background:#f0f0f0;font-weight:500}`
      + `th.left{text-align:left}`
      + `th.right{text-align:right}`
      + `td{border:1px solid #ccc;padding:6px 10px}`
      + `td.item-name{text-align:left}`
      + `td.amount{text-align:right}`
      + `.totals{font-size:13px;margin-top:4px}`
      + `.t-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee}`
      + `.t-row.bold{font-weight:bold;font-size:14px;border-top:1.5px solid #000;border-bottom:none;padding-top:10px;margin-top:4px}`
      + `.notice{margin-top:14px;font-size:11px;color:#888;border-top:1px dashed #bbb;padding-top:8px;text-align:center}`
      + `@media print{body{padding:0}@page{margin:12mm;size:A5}}`
      + `</style></head><body>`
      + `<h1>진료비 계산서·영수증</h1>`
      + `<div class="subtitle">「국민건강보험 요양급여의 기준에 관한 규칙」별지 제9호 서식</div>`
      + `<hr/>`
      + `<div class="grid2">`
      + `<div class="item"><span class="lbl">요양기관명</span><span>${statement.hospital_name}</span></div>`
      + `<div class="item"><span class="lbl">요양기관기호</span><span>${statement.institution_code}</span></div>`
      + `<div class="item"><span class="lbl">환자명</span><span>${statement.patient_name}</span></div>`
      + `<div class="item"><span class="lbl">생년월일</span><span>${statement.birth_masked}</span></div>`
      + `<div class="item"><span class="lbl">진료일자</span><span>${statement.visit_dates.join(", ") || "-"}</span></div>`
      + `<div class="item"><span class="lbl">발행일자</span><span>${today}</span></div>`
      + `</div>`
      + `<hr/>`
      + `<table>`
      + `<thead><tr><th class="left">항목</th><th class="right">금액</th></tr></thead>`
      + `<tbody>${itemRowsHtml}</tbody>`
      + `</table>`
      + `<hr class="thin"/>`
      + `<div class="totals">`
      + `<div class="t-row"><span>본인부담금</span><span>${won(statement.copayment)}</span></div>`
      + `<div class="t-row"><span>공단부담금</span><span>${won(statement.claim_amount)}</span></div>`
      + (statement.non_benefit_total > 0
        ? `<div class="t-row"><span>비급여</span><span>${won(statement.non_benefit_total)}</span></div>`
        : "")
      + `<div class="t-row bold"><span>총액</span><span>${won(statement.benefit_total_2)}</span></div>`
      + `</div>`
      + `<div class="notice">발행자: ${statement.doctor_name} (한의사) · 본 영수증은 보험 청구 목적으로 발급된 것입니다.</div>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
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

  function formatRrn(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 13);
    if (digits.length <= 6) return digits;
    return `${digits.slice(0, 6)}-${digits.slice(6)}`;
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

  function patientGenderAge(patient: Patient): string {
    const gender =
      (
        { male: "남", female: "여", 남성: "남", 여성: "여" } as Record<
          string,
          string
        >
      )[patient.gender] ?? patient.gender;
    let age: number | null = null;
    if (patient.birth_date) {
      const today = new Date();
      const b = new Date(patient.birth_date);
      age = today.getFullYear() - b.getFullYear();
      if (today < new Date(today.getFullYear(), b.getMonth(), b.getDate())) age--;
    }
    const parts = [gender, age != null ? `${age}세` : null].filter(Boolean);
    return parts.join(" · ") || "-";
  }

  function insuranceLabel(type?: string | null): string {
    if (type === "health") return "건강보험";
    if (type === "medical_aid") return "의료급여";
    return "-";
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
      <div className="hidden sm:flex w-[220px] flex-shrink-0 bg-card border-r border-border flex-col">
        {/* 섹션 1: 오늘 접수 */}
        <div className="p-3 border-b border-border">
          <div
            onClick={() => setQueueOpen((prev) => !prev)}
            className="flex items-center gap-2 mb-2 cursor-pointer"
          >
            <div className="text-xs font-medium text-text uppercase tracking-wide">
              오늘 접수
            </div>
            <span className="text-xs text-muted bg-fill rounded-full px-1.5 py-0.5">
              {todayQueue.length}
            </span>
            {queueOpen ? (
              <ChevronUp className="w-3.5 h-3.5 text-muted ml-auto" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-muted ml-auto" />
            )}
          </div>
          {queueOpen && (queueLoading ? (
            <div className="w-5 h-5 border-2 border-[#EF6600] border-t-transparent rounded-full animate-spin mx-auto py-2" />
          ) : sortedQueue.length === 0 ? (
            <div className="text-xs text-muted text-center py-4">
              오늘 접수된 환자가 없습니다
            </div>
          ) : (
            <div className="flex flex-col gap-1 max-h-[240px] overflow-y-auto">
              {sortedQueue.map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    setSelectedQueueItem(item);
                    const patient = patients.find((p) => p.id === item.patient_id);
                    const applyPatient = (patient: Patient) => {
                      setSelectedPatient(patient);
                      setResult(null);
                      setRecordsLastFetchedFor(null);
                      setSavedSymptomText(undefined);
                      setActiveTab("record");
                      setMemo(patient.memo || "");
                      setRecordMedicalHistory({ hasHistory: false, text: "" });
                    };
                    if (patient) {
                      applyPatient(patient);
                    } else {
                      getPatient(item.patient_id).then(applyPatient).catch(console.error);
                    }
                  }}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-all border-l-[2.5px] ${selectedPatient?.id === item.patient_id
                      ? "border-l-[#EF6600] bg-[#EF6600]/5"
                      : "border-l-transparent hover:bg-bg"
                    }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-text truncate">{item.patient_name}</div>
                    <div className="text-xs text-muted">
                      {new Date(item.checked_in_at).toLocaleTimeString("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-medium flex-shrink-0 ${getQueueStatusLabel(item.status).className}`}
                  >
                    {getQueueStatusLabel(item.status).label}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>

      </div>

      {/* 오른쪽 메인 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 모바일 환자 정보 바 */}
        <div className="sm:hidden bg-card border-b border-border px-4 py-2 flex-shrink-0">
          {selectedPatient ? (
            <div className="flex items-center gap-2 min-w-0">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-sm font-medium text-text">{selectedPatient.name}</span>
                  <span className="text-xs text-subtext">{patientGenderAge(selectedPatient)}</span>
                  <span className="text-xs text-subtext">{insuranceLabel(selectedPatient.insurance_type)}</span>
                </div>
                {selectedQueueItem?.symptom && (
                  <div className="text-xs text-muted truncate">증상: {selectedQueueItem.symptom}</div>
                )}
              </div>
            </div>
          ) : (
            <button
              onClick={() => router.push("/home")}
              className="text-sm text-[#EF6600] font-medium"
            >
              환자를 선택하세요 →
            </button>
          )}
        </div>
        {/* 데스크톱 환자 정보 바 */}
        <div className="hidden sm:flex items-center px-5 py-3 border-b border-border bg-card flex-shrink-0">
          {selectedPatient ? (
            <div className="flex items-center gap-3 min-w-0">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-text">{selectedPatient.name}</span>
                  <span className="text-xs text-subtext">{patientGenderAge(selectedPatient)}</span>
                  <span className="text-xs text-subtext">{insuranceLabel(selectedPatient.insurance_type)}</span>
                </div>
                {selectedQueueItem?.symptom && (
                  <div className="text-xs text-muted mt-0.5 truncate">증상: {selectedQueueItem.symptom}</div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">접수 목록에서 환자를 선택해주세요</div>
          )}
        </div>
        <div className="flex border-b border-border bg-card flex-shrink-0">
          {([
            { id: "record" as const, label: "진료 기록" },
            { id: "result" as const, label: "진단·이력·청구" },
            { id: "ask" as const, label: "한의학 검색" },
          ]).map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`px-5 py-3.5 text-xs transition-all border-b-2 ${(id === "result" ? isOverviewTab : activeTab === id)
                  ? "text-[#EF6600] border-[#EF6600]"
                  : "text-subtext border-transparent hover:text-text"
                }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div
          className={`flex-1 p-5 ${activeTab === "ask" ? "overflow-hidden flex flex-col" : "overflow-y-auto"}`}
        >
          {!selectedPatient && activeTab === "record" && (
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
                    onClick={() => {
                      if (isExpired) {
                        alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                        return;
                      }
                      toggleRecording();
                    }}
                    className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-all ${isExpired
                        ? "bg-[#68413E]/40 opacity-50 cursor-not-allowed"
                        : isRecording
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
                        const selected = Array.from(e.target.files);
                        setAudioFiles((prev) => [...prev, ...selected]);
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
                  onClick={() => {
                    if (isExpired) {
                      alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                      return;
                    }
                    startAnalysis();
                  }}
                  disabled={
                    loading || (audioFiles.length === 0 && !symptomText.trim())
                  }
                  className={`w-full bg-[#EF6600] text-white rounded-md py-3.5 text-sm font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-40 ${isExpired ? "opacity-50 cursor-not-allowed" : ""
                    }`}
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

          {/* 진단·이력·청구 통합 탭 */}
          {isOverviewTab && selectedPatient && (
            <div className="flex flex-col gap-8">

              {/* ── 진단 결과 ── */}
              <div>
                <p className="text-[10px] font-semibold text-subtext uppercase tracking-widest mb-4 pb-2 border-b border-border">진단 결과</p>
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
                    {(result.acupuncture?.length || result.claudeBased?.acupuncture?.length) ? (
                      <div className="mt-3 bg-card border border-border rounded-lg p-4">
                        <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide mb-3">
                          <MapPin className="w-3.5 h-3.5" /> 침 처방 위치
                        </div>
                        <AcupointViewer
                          readOnly
                          highlightedPoints={parseAcupointCodes([
                            ...(result.acupuncture ?? []),
                            ...(result.claudeBased?.acupuncture ?? []),
                          ])}
                        />
                      </div>
                    ) : null}
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
                        onClick={handlePrescriptionPrint}
                        className="flex-1 border border-border-strong rounded-md py-2.5 text-xs text-subtext hover:border-text transition-all flex items-center justify-center gap-1.5"
                      >
                        <Printer className="w-3.5 h-3.5" /> 처방전 출력
                      </button>
                      <button
                        onClick={() =>
                          handleReceiptPrint(
                            currentRecordId ? recordClaimIds[currentRecordId] : undefined
                          )
                        }
                        className="flex-1 border border-border-strong rounded-md py-2.5 text-xs text-subtext hover:border-text transition-all flex items-center justify-center gap-1.5"
                      >
                        <Receipt className="w-3.5 h-3.5" /> 영수증 출력
                      </button>
                      <button
                        onClick={() => {
                          if (isExpired) {
                            alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                            return;
                          }
                          setActiveTab("record");
                          setFeedbackAvailable(false);
                          setFeedbackHelpful(null);
                          setFeedbackComment("");
                          setFeedbackSubmitted(false);
                          setFeedbackRecordId(null);
                          setResultMemoOpen(false);
                        }}
                        title={isExpired ? "구독을 갱신해주세요" : undefined}
                        className={`flex-1 border border-border-strong rounded-md py-2.5 text-xs text-subtext hover:border-text transition-all flex items-center justify-center gap-1.5 ${isExpired ? "opacity-50 cursor-not-allowed" : ""
                          }`}
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
                                className={`flex items-center gap-1.5 px-4 py-2 rounded-md border text-xs transition-all ${feedbackHelpful === true
                                    ? "bg-[#EF6600] text-white border-[#EF6600]"
                                    : "border-border text-subtext hover:border-[#EF6600] hover:text-[#EF6600]"
                                  }`}
                              >
                                <ThumbsUp className="w-3.5 h-3.5" /> 도움됨
                              </button>
                              <button
                                onClick={() => setFeedbackHelpful(false)}
                                className={`flex items-center gap-1.5 px-4 py-2 rounded-md border text-xs transition-all ${feedbackHelpful === false
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

              {/* ── 진료 이력 ── */}
              <div>
                <p className="text-[10px] font-semibold text-subtext uppercase tracking-widest mb-4 pb-2 border-b border-border">진료 이력</p>
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
                                onClick={() => {
                                  if (!r.chart_structured) return;
                                  navigator.clipboard.writeText(r.chart_structured);
                                  setHistoryCopied(r.id);
                                  setTimeout(() => setHistoryCopied(null), 2000);
                                }}
                                className="px-3 border-l border-border text-muted hover:text-[#EF6600] hover:bg-orange-50 transition-colors"
                                title="복사"
                              >
                                {historyCopied === r.id ? (
                                  <Check className="w-3.5 h-3.5 text-green-500" />
                                ) : (
                                  <Clipboard className="w-3.5 h-3.5" />
                                )}
                              </button>
                              <button
                                onClick={() => {
                                  setCurrentRecordId(r.id);
                                  setActiveTab("billing");
                                }}
                                className="px-3 border-l border-border text-muted hover:text-[#EF6600] hover:bg-orange-50 transition-colors"
                                title="청구"
                              >
                                <ReceiptText className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleReceiptPrint(recordClaimIds[r.id])}
                                className="px-3 border-l border-border text-muted hover:text-[#EF6600] hover:bg-orange-50 transition-colors"
                                title="영수증 출력"
                              >
                                <Receipt className="w-3.5 h-3.5" />
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

              {/* ── 청구 ── */}
              <div>
                <p className="text-[10px] font-semibold text-subtext uppercase tracking-widest mb-4 pb-2 border-b border-border">청구</p>
                <div className="mb-4 bg-card border border-border rounded-lg p-4">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-1.5 text-xs text-subtext uppercase tracking-wide">
                      <Search className="w-3.5 h-3.5" /> 상병코드 (KCD)
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowPastKcd((v) => !v)}
                      className="flex items-center gap-1 text-[11px] text-subtext hover:text-[#EF6600] transition-colors"
                    >
                      <History className="w-3 h-3" /> 과거 상병
                    </button>
                  </div>

                  {kcdCodes.length > 0 && (
                    <div className="flex flex-col gap-1.5 mb-2">
                      {kcdCodes.map((c, idx) => {
                        const warnings = kcdWarnings(c.code);
                        return (
                          <div key={c.code}>
                            <div
                              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs w-fit ${
                                warnings.length > 0
                                  ? "border-amber-400 bg-amber-50 text-amber-700"
                                  : "border-border bg-fill text-text"
                              }`}
                            >
                              <span
                                className={`text-[9px] font-semibold px-1 rounded ${
                                  idx === 0 ? "bg-[#EF6600] text-white" : "bg-border text-subtext"
                                }`}
                              >
                                {idx === 0 ? "주상병" : "부상병"}
                              </span>
                              <span className="font-medium">{c.code}</span>
                              {c.korean_name && <span>{c.korean_name}</span>}
                              <button
                                type="button"
                                onClick={() => removeKcdCode(c.code)}
                                className="text-subtext hover:text-text transition-colors"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                            {warnings.length > 0 && (
                              <div className="mt-1 flex flex-col gap-0.5">
                                {warnings.map((w) => (
                                  <span
                                    key={w}
                                    className="flex items-center gap-1 text-[11px] text-amber-600"
                                  >
                                    <TriangleAlert className="w-3 h-3 flex-shrink-0" /> {w}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {kcdCodes.length >= 2 && (
                    <div className="mb-2 flex items-center gap-1.5 text-[11px] text-subtext bg-fill rounded-md px-2.5 py-1.5">
                      <TriangleAlert className="w-3 h-3 flex-shrink-0" />
                      상병 자동 묶음이 적용되지 않습니다. 각 진료내역은 개별적으로 연결해주세요.
                    </div>
                  )}

                  {showPastKcd && (
                    <div className="mb-2 rounded-md border border-border bg-fill p-2">
                      {pastKcdCodes.length === 0 ? (
                        <p className="text-[11px] text-subtext px-1 py-0.5">과거 진료기록에 등록된 상병이 없습니다.</p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {pastKcdCodes.map((code) => (
                            <button
                              key={code}
                              type="button"
                              onClick={() => addKcdCode({ code, korean_name: "" })}
                              disabled={kcdCodes.some((c) => c.code === code)}
                              className="rounded-full border border-border bg-card px-2 py-0.5 text-[11px] text-text hover:border-[#EF6600] hover:text-[#EF6600] transition-colors disabled:opacity-40"
                            >
                              {code}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="relative">
                    <input
                      value={kcdQuery}
                      onChange={(e) => { setKcdQuery(e.target.value); setKcdDropdownOpen(true); }}
                      onFocus={() => setKcdDropdownOpen(true)}
                      onBlur={() => setTimeout(() => setKcdDropdownOpen(false), 150)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && kcdQuery.trim()) {
                          const match = kcdResults[0];
                          const code = match ?? { code: kcdQuery.trim().toUpperCase(), korean_name: "" };
                          addKcdCode(code);
                          setKcdQuery("");
                          setKcdResults([]);
                          setKcdDropdownOpen(false);
                        }
                      }}
                      placeholder={kcdCodes.length > 0 ? "부상병 추가 검색" : "코드 또는 진단명 검색 (예: M545, 요통)"}
                      className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                    />
                    {kcdDropdownOpen && (kcdResults.length > 0 || kcdQuery.trim().length > 0) && (
                      <div className="absolute left-0 right-0 mt-1 bg-card border border-border rounded-md shadow-lg max-h-48 overflow-y-auto z-10">
                        {kcdResults.map((item) => (
                          <button
                            key={item.code}
                            type="button"
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => { addKcdCode(item); setKcdQuery(""); setKcdResults([]); setKcdDropdownOpen(false); }}
                            disabled={kcdCodes.some((c) => c.code === item.code)}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-bg transition-colors border-b border-border last:border-b-0 disabled:opacity-40"
                          >
                            <span className="font-medium text-[#EF6600]">{item.code}</span>{" "}
                            <span className="text-text">{item.korean_name}</span>
                          </button>
                        ))}
                        {kcdResults.length === 0 && kcdQuery.trim().length > 0 && (
                          <button
                            type="button"
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => {
                              addKcdCode({ code: kcdQuery.trim().toUpperCase(), korean_name: "" });
                              setKcdQuery("");
                              setKcdResults([]);
                              setKcdDropdownOpen(false);
                            }}
                            className="w-full text-left px-3 py-2 text-sm hover:bg-bg transition-colors"
                          >
                            <span className="text-subtext">직접 입력:</span>{" "}
                            <span className="font-medium text-text">{kcdQuery.trim()}</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                {currentRecordId ? (
                  <BillableItemPicker
                    medicalRecordId={currentRecordId}
                    onConfirmed={(claim) =>
                      setRecordClaimIds((prev) => ({ ...prev, [currentRecordId]: claim.id }))
                    }
                  />
                ) : (
                  <div className="text-sm text-muted text-center py-8">
                    먼저 진료 기록을 저장해주세요
                  </div>
                )}
              </div>

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
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${askMode === "ask"
                        ? "bg-card text-text shadow-sm"
                        : "text-subtext hover:text-text"
                      }`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" /> 질문하기
                  </button>
                  <button
                    type="button"
                    onClick={() => setAskMode("diagnose")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${askMode === "diagnose"
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
              <div className="flex gap-2">
                <button
                  onClick={() => setShowSavedModal(false)}
                  className="flex-1 border border-border text-text rounded-md py-2.5 text-sm font-medium hover:bg-fill transition-colors"
                >
                  확인
                </button>
                {currentRecordId && (
                  <button
                    onClick={() => {
                      setShowSavedModal(false);
                      setActiveTab("billing");
                    }}
                    className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-1.5"
                  >
                    <ReceiptText className="w-3.5 h-3.5" /> 청구하기
                  </button>
                )}
              </div>
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
                {
                  label: "주민번호",
                  key: "rrn",
                  type: "text",
                  placeholder: "000000-0000000",
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
                            : field.key === "rrn"
                              ? formatRrn(e.target.value)
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
                      className={`flex-1 py-2.5 text-sm rounded-md border transition-all ${newPatient.gender === g
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
