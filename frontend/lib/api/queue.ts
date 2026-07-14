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
  patient_birth_date: string | null;
  patient_gender: string | null;
  doctor_id: string | null;
  queue_date: string;
  checked_in_at: string;
  status: "waiting" | "in_progress" | "billed" | "paid";
  source: "manual" | "record_created" | "reservation";
  assigned_bed: string | null;
  claim_id: string | null;
}

export async function getTodayQueue(): Promise<QueueItem[]> {
  const res = await fetch(`${BASE_URL}/api/queue/today`, { headers: getHeaders() });
  if (!res.ok) throw new Error("접수 목록 조회 실패");
  return res.json();
}

export async function getQueueByDate(targetDate: string): Promise<QueueItem[]> {
  const res = await fetch(`${BASE_URL}/api/queue/by-date?target_date=${targetDate}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("접수 목록 조회 실패");
  return res.json();
}

export async function getQueueCalendar(year: number, month: number): Promise<Record<string, number>> {
  const res = await fetch(`${BASE_URL}/api/queue/calendar?year=${year}&month=${month}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("접수 달력 조회 실패");
  const data = await res.json();
  return data.counts;
}

export async function checkinPatient(patient_id: string, doctor_id?: string): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ patient_id, doctor_id }),
  });
  if (!res.ok) throw new Error("접수 등록 실패");
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

export async function updateQueueBed(queue_id: string, assigned_bed: string | null): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}/bed`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify({ assigned_bed }),
  });
  if (!res.ok) throw new Error("베드 배정 실패");
  return res.json();
}

export interface CheckoutLineItem {
  code: string;
  qty: number;
  days: number;
}

export async function checkoutQueueItem(
  queue_id: string,
  kcd_code: string,
  line_items: CheckoutLineItem[]
): Promise<QueueItem> {
  const res = await fetch(`${BASE_URL}/api/queue/${queue_id}/checkout`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ kcd_code, line_items }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "청구 저장 실패");
  }
  return res.json();
}
