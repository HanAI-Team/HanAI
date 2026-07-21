const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type PurchaseRecordType = "purchase" | "compound";

export interface PurchaseRecordItem {
  id: string;
  record_type: PurchaseRecordType;
  item_name: string;
  item_code: string | null;
  spec: string | null;
  quantity: string;
  unit_price: number;
  amount: number;
  supplier_name: string | null;
  transaction_date: string;
  reported: boolean;
  reported_at: string | null;
}

export interface PurchaseRecordCreateInput {
  record_type: PurchaseRecordType;
  item_name: string;
  item_code?: string | null;
  spec?: string | null;
  quantity?: number;
  unit_price?: number;
  amount?: number;
  supplier_name?: string | null;
  transaction_date: string;
}

export type PurchaseRecordUpdateInput = Partial<Omit<PurchaseRecordCreateInput, "record_type">>;

export interface MissingDeclarationItem {
  code: string;
  name: string;
  claim_count: number;
  total_qty: string;
}

export interface MissingDeclarationCheckResponse {
  year: number;
  month: number;
  items: MissingDeclarationItem[];
}

export async function getPurchaseRecords(
  recordType?: PurchaseRecordType,
  year?: number,
  month?: number
): Promise<PurchaseRecordItem[]> {
  const params = new URLSearchParams();
  if (recordType) params.set("record_type", recordType);
  if (year) params.set("year", String(year));
  if (month) params.set("month", String(month));
  const res = await fetch(`${BASE_URL}/api/billing/purchase-records?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("구입내역 조회 실패");
  return res.json();
}

export async function createPurchaseRecord(
  data: PurchaseRecordCreateInput
): Promise<PurchaseRecordItem> {
  const res = await fetch(`${BASE_URL}/api/billing/purchase-records`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "구입내역 등록 실패");
  return res.json();
}

export async function updatePurchaseRecord(
  id: string,
  data: PurchaseRecordUpdateInput
): Promise<PurchaseRecordItem> {
  const res = await fetch(`${BASE_URL}/api/billing/purchase-records/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "구입내역 수정 실패");
  return res.json();
}

export async function deletePurchaseRecord(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/billing/purchase-records/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("구입내역 삭제 실패");
}

export async function reportPurchaseRecord(id: string): Promise<PurchaseRecordItem> {
  const res = await fetch(`${BASE_URL}/api/billing/purchase-records/${id}/report`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("신고(송신) 처리 실패");
  return res.json();
}

export async function checkMissingDeclarations(
  year: number,
  month: number
): Promise<MissingDeclarationCheckResponse> {
  const res = await fetch(
    `${BASE_URL}/api/billing/purchase-records/missing-check?year=${year}&month=${month}`,
    { headers: getHeaders() }
  );
  if (!res.ok) throw new Error("누락 점검 실패");
  return res.json();
}
