import { Patient } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function getPatients(search?: string, page = 1, size = 20): Promise<{
  items: Patient[];
  total: number;
  page: number;
  size: number;
}> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  params.set("page", String(page));
  params.set("size", String(size));
  const url = `${BASE_URL}/api/patients/?${params.toString()}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (res.status === 404) return { items: [], total: 0, page, size };
  if (!res.ok) throw new Error("환자 목록 조회 실패");
  const data = await res.json();
  return {
    items: Array.isArray(data) ? data : data.items || [],
    total: data.total || 0,
    page: data.page || page,
    size: data.size || size,
  };
}

export type DataPurgeLog = {
  id: number;
  doctor_id: string;
  patient_name_before: string | null;
  reason: string;
  purge_type: string;
  purged_at: string;
};

export async function getPurgeLogs(): Promise<DataPurgeLog[]> {
  const res = await fetch(`${BASE_URL}/api/patients/purge-logs`, { headers: getHeaders() });
  if (!res.ok) throw new Error("파기대장 조회 실패");
  const data = await res.json();
  return data.items || [];
}

export async function getPatient(id: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${id}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("환자 조회 실패");
  return res.json();
}


export async function anonymizePatient(id: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${id}/anonymize`, {
    method: "PATCH",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("환자 익명화에 실패했습니다.");
  return res.json();
}


export async function saveRecord(
  patientId: string,
  chartStructured: string,
  rawTranscription?: string,
  medicalHistory?: string | null,
  selectedResult?: string,
) {
  const res = await fetch(`${BASE_URL}/api/patients/${patientId}/records`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      chart_structured: chartStructured,
      raw_transcription: rawTranscription,
      medical_history: medicalHistory,
      selected_result: selectedResult,
    }),
  });
  if (!res.ok) throw new Error("저장 실패");
  return res.json();
}

export async function getPatientRecords(patientId: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${patientId}/records`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("진료 이력 조회 실패");
  return res.json() as Promise<{
    patient: any;
    records: {
      id: string;
      recorded_at: string | null;
      chart_structured: string | null;
      raw_transcription: string | null;
      medical_history: string | null;
    }[];
  }>;
}

export async function importPatientsFromExcel(file: File) {
  const token = localStorage.getItem("token");
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/api/patients/import/excel`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error("엑셀 가져오기 실패");
  return res.json() as Promise<{ inserted: number; skipped: number }>;
}

export async function importPatientsFromCsv(file: File) {
  const token = localStorage.getItem("token");
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/api/patients/import/csv`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error("CSV 가져오기 실패");
  return res.json() as Promise<{ inserted: number; skipped: number }>;
}

export async function downloadPatientsCsv(reason: string): Promise<void> {
  const token = localStorage.getItem("token");
  const url = `${BASE_URL}/api/patients/export/csv?${new URLSearchParams({ reason })}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("환자 목록 CSV 다운로드 실패");

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = "patients.csv";
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadRecordsCsv(reason: string): Promise<void> {
  const token = localStorage.getItem("token");
  const url = `${BASE_URL}/api/patients/export/records/csv?${new URLSearchParams({ reason })}`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("진료기록 CSV 다운로드 실패");

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = "medical_records.csv";
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function updatePatient(
  id: string,
  data: {
    name?: string;
    birth_date?: string;
    gender?: string;
    phone?: string;
    memo?: string;
    insurance_type?: string;
    rrn?: string;
    disability_grade?: string | null;
    medical_aid_grade?: string | null;
  },
) {
  const res = await fetch(`${BASE_URL}/api/patients/${id}`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("환자 정보 수정 실패");
  return res.json();
}

export async function deleteRecord(patientId: string, recordId: string) {
  const res = await fetch(
    `${BASE_URL}/api/patients/${patientId}/records/${recordId}`,
    {
      method: "DELETE",
      headers: getHeaders(),
    },
  );
  if (!res.ok) throw new Error("진료 이력 삭제 실패");
}

export async function createPatient(data: {
  name: string;
  birth_date?: string;
  gender?: string;
  phone?: string;
  memo?: string;
}) {
  const res = await fetch(`${BASE_URL}/api/patients/register`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "환자 등록 실패");
  }
  return res.json();
}
