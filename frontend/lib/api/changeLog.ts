const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface ChangeLogItem {
  id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChangeLogListResponse {
  total: number;
  page: number;
  size: number;
  items: ChangeLogItem[];
}

export async function getChangeLog(
  page = 1,
  size = 20,
  dateFrom?: string,
  dateTo?: string
): Promise<ChangeLogListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("size", String(size));
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const res = await fetch(`${BASE_URL}/api/charting/change-log?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("변경일 이력 조회 실패");
  return res.json();
}
