const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface FeeItem {
  code: string;
  name: string;
  category: string;
  insured_health: boolean;
  insured_medical_aid: boolean;
  insured_veterans: boolean;
  unit_price: number;
  is_insured: boolean;
  is_standalone: boolean;
  effective_date: string | null;
  expired_date: string | null;
}

export interface FeeListResponse {
  total: number;
  page: number;
  size: number;
  items: FeeItem[];
}

export interface FeeCreateInput {
  code: string;
  name: string;
  category: string;
  unit_price: number;
  is_insured?: boolean;
  is_standalone?: boolean;
  insured_health?: boolean;
  insured_medical_aid?: boolean;
  insured_veterans?: boolean;
  effective_date?: string | null;
  expired_date?: string | null;
}

export type FeeUpdateInput = Partial<Omit<FeeCreateInput, "code">>;

export async function getFees(page = 1, size = 20, search?: string): Promise<FeeListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("size", String(size));
  if (search) params.set("search", search);
  const res = await fetch(`${BASE_URL}/api/fees?${params.toString()}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("수가 마스터 목록 조회 실패");
  return res.json();
}

export async function createFee(data: FeeCreateInput): Promise<FeeItem> {
  const res = await fetch(`${BASE_URL}/api/fees`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "수가 등록 실패");
  return res.json();
}

export async function updateFee(code: string, data: FeeUpdateInput): Promise<FeeItem> {
  const res = await fetch(`${BASE_URL}/api/fees/${encodeURIComponent(code)}`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "수가 수정 실패");
  return res.json();
}

export async function deleteFee(code: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/fees/${encodeURIComponent(code)}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("수가 삭제 실패");
}
