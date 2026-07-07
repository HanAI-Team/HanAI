import { apiCall } from "./client";
import type { BillableItem, ClaimSummary, SelectedBillableItem } from "@/types/billing";

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

export interface ClaimResubmissionRequest {
  claim_type: "supplement" | "addition";
  original_receipt_no: number;
  original_record_serial: number;
  rejection_reason_code?: string;
}

export async function resubmitClaim(
  claimId: string,
  data: ClaimResubmissionRequest
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/${claimId}/resubmission`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "보완·추가청구 처리 실패");
  }
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

export async function getBillableCatalog(): Promise<BillableItem[]> {
  return apiCall("/api/billing/catalog");
}

function mapClaimSummary(raw: any): ClaimSummary {
  return {
    id: raw.id,
    patientId: raw.patient_id,
    billingMonth: raw.billing_month,
    status: raw.status,
    totalAmount: raw.total_amount,
    lineItems: (raw.line_items ?? []).map((li: any) => ({
      id: li.id,
      name: li.name,
      code: li.code,
      amount: li.amount,
      hyeolmyeongNames: li.hyeolmyeong_names ?? undefined,
      isNonBenefit: li.is_non_benefit ?? false,
    })),
  };
}

export async function submitLineItems(
  medicalRecordId: string,
  items: SelectedBillableItem[]
): Promise<ClaimSummary> {
  const raw = await apiCall(`/api/billing/medical-records/${medicalRecordId}/line-items`, {
    method: "POST",
    body: JSON.stringify({
      medical_record_id: medicalRecordId,
      items: items.map((i) => ({
        item_id: i.itemId,
        hyeolmyeong_names: i.hyeolmyeongNames,
        is_non_benefit: i.isNonBenefit ?? false,
      })),
    }),
  });
  return mapClaimSummary(raw);
}

export async function updateClaimSupportFund(
  claimId: string,
  supportFund: number,
): Promise<ClaimSummary> {
  const raw = await apiCall(`/api/billing/claims/${claimId}/support-fund`, {
    method: "PATCH",
    body: JSON.stringify({ support_fund: supportFund }),
  });
  return mapClaimSummary(raw);
}
