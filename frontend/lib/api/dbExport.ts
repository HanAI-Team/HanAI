const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DB_EXPORT_TABLES = [
  { value: "patients", label: "환자 (patients)" },
  { value: "medical_records", label: "진료기록 (medical_records)" },
  { value: "claims", label: "청구 (claims)" },
  { value: "claim_line_items", label: "청구 라인 (claim_line_items)" },
  { value: "prescriptions", label: "처방 (prescriptions)" },
  { value: "fee_master", label: "수가 마스터 (fee_master)" },
  { value: "drug_master", label: "약가 마스터 (drug_master)" },
  { value: "claim_rejection_codes", label: "반송·심사불능 코드 (claim_rejection_codes)" },
  { value: "audit_logs", label: "감사 로그 (audit_logs)" },
  { value: "login_logs", label: "로그인 로그 (login_logs)" },
  { value: "account_histories", label: "계정 이력 (account_histories)" },
  { value: "access_control_logs", label: "접근권한 이력 (access_control_logs)" },
  { value: "daily_queue", label: "접수 (daily_queue)" },
] as const;

export type DbExportFormat = "csv" | "xlsx";

function todayCompact(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

export async function downloadDbExport(
  table: string,
  format: DbExportFormat,
  reason: string
): Promise<void> {
  const token = localStorage.getItem("token");
  const params = new URLSearchParams({ table, format, reason });
  const res = await fetch(`${BASE_URL}/api/manage/db-export?${params.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || "DB 내역 추출 실패");
  }

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = `${table}_${todayCompact()}.${format}`;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
