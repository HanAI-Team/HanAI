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
  approval_no?: string | null;
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

export async function downloadEdi(claimId: string, testMode = false): Promise<void> {
  const token = localStorage.getItem("token");
  const endpoint = `${BASE_URL}/api/billing/claims/${claimId}/edi${testMode ? "?test=true" : ""}`;
  const res = await fetch(endpoint, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("EDI 생성 실패");

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = testMode ? `claim_${claimId}_TEST.sam` : `claim_${claimId}.sam`;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadSamFiles(claimId: string, testMode = false): Promise<void> {
  const token = localStorage.getItem("token");
  const endpoint = `${BASE_URL}/api/billing/claims/${claimId}/sam-files${testMode ? "?test=true" : ""}`;
  const res = await fetch(endpoint, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("SAM File 생성 실패");

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = testMode ? `claim_${claimId}_TEST_sam_files.zip` : `claim_${claimId}_sam_files.zip`;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

export async function bulkDownloadEdi(ids: string[], testMode = false): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/bulk-edi`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ ids, test_mode: testMode }),
  });
  if (!res.ok) throw new Error("일괄 EDI 생성 실패");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = testMode ? "claims_edi_TEST.zip" : "claims_edi.zip";
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

export interface StatementProcedureRow {
  hang: string;
  mok: string;
  code: string;
  name: string;
  unit_price: number;
  count: number;
  amount: number;
  is_non_benefit: boolean;
  copay_rate_label: "A" | "B" | null;
}

export interface ClaimStatement {
  hospital_name: string;
  institution_code: string;
  patient_name: string;
  birth_masked: string;
  disease_names: string[];
  special_code: string | null;
  doctor_name: string;
  license_type: string;
  license_no: string;
  visit_dates: string[];
  visit_count: number;
  procedures: StatementProcedureRow[];
  subtotal: number;
  surcharge_rate: number;
  benefit_total_1: number;
  copayment: number;
  support_fund: number;
  disability_medical_cost: number;
  claim_amount: number;
  upper_limit_excess: number;
  non_benefit_total: number;
  benefit_total_2: number;
  veterans_claim: number;
  full_price_copay_total: number;
  veterans_copay: number;
  under_full_total: number;
  under_full_copay: number;
  under_full_claim: number;
  under_full_veterans_claim: number;
}

export async function getClaimStatement(claimId: string): Promise<ClaimStatement> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/${claimId}/statement`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("명세서 조회 실패");
  return res.json();
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
  items: SelectedBillableItem[],
  visitType: "외래" | "입원" = "외래"
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
      visit_type: visitType,
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

export async function updateClaimApproval(
  claimId: string,
  approvalNo: string | null,
): Promise<{ id: string; approval_no: string | null }> {
  return apiCall(`/api/billing/claims/${claimId}/approval`, {
    method: "PATCH",
    body: JSON.stringify({ approval_no: approvalNo }),
  });
}
