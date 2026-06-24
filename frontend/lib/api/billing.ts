const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface ClaimListItem {
  id: string;
  patient_name: string;
  claim_period: string;
  status: string;
  total_amount: number;
  patient_copay: number;
  claim_amount: number;
  created_at: string;
}

export async function getClaims(params?: { month?: string; status?: string }): Promise<ClaimListItem[]> {
  const query = new URLSearchParams();
  if (params?.month) query.set("month", params.month);
  if (params?.status) query.set("status", params.status);
  const url = `${BASE_URL}/api/billing/claims${query.toString() ? "?" + query : ""}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("청구 목록 조회 실패");
  return res.json();
}

export async function downloadEdi(claimId: string): Promise<void> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${BASE_URL}/api/billing/claims/${claimId}/edi`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("EDI 생성 실패");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `claim_${claimId}.edi`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function bulkDownloadEdi(ids: string[]): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/bulk-edi`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) throw new Error("일괄 EDI 생성 실패");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "claims_edi.zip";
  a.click();
  URL.revokeObjectURL(url);
}

const STATUS_LABEL: Record<string, string> = {
  draft: "작성중",
  submitted: "제출완료",
  approved: "승인",
  rejected: "반려",
};

export function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}
