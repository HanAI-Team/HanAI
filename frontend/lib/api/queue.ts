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
  status: "waiting" | "in_progress" | "done";
  source: "manual" | "record_created" | "reservation";
}

export async function getTodayQueue(): Promise<QueueItem[]> {
  const res = await fetch(`${BASE_URL}/api/queue/today`, { headers: getHeaders() });
  if (!res.ok) throw new Error("접수 목록 조회 실패");
  return res.json();
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
