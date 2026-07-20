const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface DrugMasterItem {
  product_code: string;
  product_name: string;
  ingredient_name: string | null;
  company_name: string | null;
  spec: string | null;
  unit: string | null;
  unit_price: number;
  administration_route: string | null;
  is_prescription: boolean | null;
  effective_date: string | null;
}

export interface DrugListResponse {
  total: number;
  page: number;
  size: number;
  items: DrugMasterItem[];
}

export interface DrugCreateInput {
  product_code: string;
  product_name: string;
  ingredient_code?: string | null;
  ingredient_name?: string | null;
  company_name?: string | null;
  spec?: string | null;
  unit?: string | null;
  unit_price: number;
  administration_route?: string | null;
  classification_code?: string | null;
  is_prescription?: boolean | null;
  effective_date?: string | null;
}

export type DrugUpdateInput = Partial<Omit<DrugCreateInput, "product_code">>;

export async function getDrugs(page = 1, size = 20, search?: string): Promise<DrugListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("size", String(size));
  if (search) params.set("search", search);
  const res = await fetch(`${BASE_URL}/api/drugs?${params.toString()}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("약가 마스터 목록 조회 실패");
  return res.json();
}

export async function createDrug(data: DrugCreateInput): Promise<DrugMasterItem> {
  const res = await fetch(`${BASE_URL}/api/drugs`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "약가 등록 실패");
  return res.json();
}

export async function updateDrug(code: string, data: DrugUpdateInput): Promise<DrugMasterItem> {
  const res = await fetch(`${BASE_URL}/api/drugs/${encodeURIComponent(code)}`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "약가 수정 실패");
  return res.json();
}

export async function deleteDrug(code: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/drugs/${encodeURIComponent(code)}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("약가 삭제 실패");
}
