const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface RejectionCodeItem {
  id: number;
  category: string;
  code: string;
  detail_code: string;
  description: string;
}

export interface RejectionCodeListResponse {
  total: number;
  page: number;
  size: number;
  items: RejectionCodeItem[];
}

export interface RejectionCodeCreateInput {
  category: string;
  code: string;
  detail_code?: string;
  description: string;
}

export async function getRejectionCodes(
  page = 1,
  size = 20,
  category?: string
): Promise<RejectionCodeListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("size", String(size));
  if (category) params.set("category", category);
  const res = await fetch(`${BASE_URL}/api/rejection-codes?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("반송·심사불능 코드 목록 조회 실패");
  return res.json();
}

export async function createRejectionCode(
  data: RejectionCodeCreateInput
): Promise<RejectionCodeItem> {
  const res = await fetch(`${BASE_URL}/api/rejection-codes`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "코드 등록 실패");
  return res.json();
}

export async function deleteRejectionCode(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/rejection-codes/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("코드 삭제 실패");
}
