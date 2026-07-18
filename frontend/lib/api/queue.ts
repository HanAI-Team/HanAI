const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface QueueItem {
  id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string | null;
  queue_date: string;
  checked_in_at: string;
  status: "waiting" | "in_progress" | "done" | "paid";
  source: "manual" | "record_created" | "reservation";
  symptom: string | null;
  queue_number: number | null;
  payment_method: "card" | "cash" | null;
  paid_at: string | null;
}

export interface QueueBilling {
  claim_id: string;
  claim_amount: number;
  total_amount: number;
  patient_copay: number;
}

export async function getTodayQueue(): Promise<QueueItem[]> {
  const res = await fetch(`${BASE_URL}/api/queue/today`, { headers: getHeaders() });
  if (!res.ok) throw new Error("접수 목록 조회 실패");
  return res.json();
}

export async function getQueueByDate(date: string): Promise<QueueItem[]> {
  const res = await fetch(`${BASE_URL}/api/queue/?date=${date}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("접수 목록 조회 실패");
  return res.json();
}

export async function getQueueMonthlyCountsAPI(year: number, month: number): Promise<Record<string, number>> {
  const res = await fetch(`${BASE_URL}/api/queue/monthly-counts?year=${year}&month=${month}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("월간 접수 건수 조회 실패");
  const data = await res.json();
  return data.counts;
}

export async function checkinPatient(patient_id: string, doctor_id?: string, symptom?: string): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ patient_id, doctor_id, symptom }),
  });
  if (!res.ok) throw new Error("접수 등록 실패");
  return res.json();
}

export async function payQueue(queue_id: string, payment_method: "card" | "cash"): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}/pay`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify({ payment_method }),
  });
  if (!res.ok) throw new Error("수납 처리 실패");
  return res.json();
}

export async function getQueueBilling(queue_id: string): Promise<QueueBilling | null> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}/billing`, { headers: getHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("청구 정보 조회 실패");
  return res.json();
}

export async function removeFromQueue(queue_id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("접수 취소 실패");
}

export async function updateQueueStatus(queue_id: string, status: string): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}/status`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error("접수 상태 변경 실패");
  return res.json();
}
