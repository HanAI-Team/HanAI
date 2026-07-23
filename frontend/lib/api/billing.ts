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
  from_reception: boolean;
  is_paid: boolean;
  claim_type?: "supplement" | "addition" | null;
  original_receipt_no?: number | null;
  original_record_serial?: number | null;
  rejection_reason_code?: string | null;
  billing_agent_code?: string | null;
  billing_agent_name?: string | null;
}

const CLAIM_TYPE_LABEL: Record<string, string> = {
  supplement: "보완",
  addition: "추가",
};

export function claimTypeLabel(claimType: string | null | undefined): string {
  return claimType ? CLAIM_TYPE_LABEL[claimType] ?? claimType : "당초";
}

export interface RejectionCodeSearchResult {
  category: string;
  code: string;
  detail_code: string;
  description: string;
}

export async function searchRejectionCodes(
  query: string,
  category?: string,
  limit = 20
): Promise<RejectionCodeSearchResult[]> {
  if (!query.trim()) return [];
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (category) params.set("category", category);
  const res = await fetch(`${BASE_URL}/api/billing/rejection-codes?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("심사불능사유코드 검색 실패");
  return res.json();
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
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "EDI 생성 실패");
  }

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
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "SAM File 생성 실패");
  }

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
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "일괄 EDI 생성 실패");
  }

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

export interface AcupuncturePointSearchResult {
  code: string;
  korean_name: string;
  meridian: string | null;
  location: string | null;
  is_standalone: boolean;
}

export async function searchAcupuncturePoints(
  query: string,
  limit = 20
): Promise<AcupuncturePointSearchResult[]> {
  if (!query.trim()) return [];
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiCall(`/api/acupuncture/search?${params}`);
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

export interface ClaimPrescription {
  hospital_name: string;
  institution_code: string;
  hospital_phone: string;
  issue_date: string;
  issue_no: string;
  patient_name: string;
  patient_birth_masked: string;
  disease_names: string[];
  doctor_name: string;
  license_type: string;
  license_no: string;
}

export async function getClaimPrescription(claimId: string): Promise<ClaimPrescription> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/${claimId}/prescription`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "처방전 조회 실패");
  }
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
      acupoints: (li.acupoints ?? []).map((a: any) => ({ code: a.code, koreanName: a.korean_name })),
      isNonBenefit: li.is_non_benefit ?? false,
      performedByDoctorId: li.performed_by_doctor_id ?? null,
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
        acupoint_codes: i.acupointCodes,
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

export async function getClaimLineItems(claimId: string): Promise<ClaimSummary> {
  const raw = await apiCall(`/api/billing/claims/${claimId}/line-items`, {
    method: "GET",
  });
  return mapClaimSummary(raw);
}

export async function deleteLineItem(
  lineItemId: string,
): Promise<ClaimSummary | { deletedClaim: true }> {
  const raw = await apiCall(`/api/billing/line-items/${lineItemId}`, {
    method: "DELETE",
  });
  if (raw?.deleted_claim) return { deletedClaim: true };
  return mapClaimSummary(raw);
}

export interface HospitalDoctor {
  id: string;
  name: string;
  licenseKind: string | null;
  licenseNumber: string | null;
}

export async function getHospitalDoctors(): Promise<HospitalDoctor[]> {
  const raw = await apiCall("/api/billing/doctors", { method: "GET" });
  return (raw ?? []).map((d: any) => ({
    id: d.id,
    name: d.name,
    licenseKind: d.license_kind,
    licenseNumber: d.license_number,
  }));
}

export async function updateLineItemDoctor(
  lineItemId: string,
  performedByDoctorId: string | null,
): Promise<void> {
  await apiCall(`/api/billing/line-items/${lineItemId}/doctor`, {
    method: "PATCH",
    body: JSON.stringify({ performed_by_doctor_id: performedByDoctorId }),
  });
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

export interface QuickFeeItem {
  code: string;
  name: string;
  category: string;
  unit_price: number;
}

export interface QuickFeeItems {
  categories: string[];
  favorites: QuickFeeItem[];
  by_category: Record<string, QuickFeeItem[]>;
}

export async function getQuickFeeItems(): Promise<QuickFeeItems> {
  return apiCall("/api/billing/fee-quick-items");
}

export interface CheckoutPreviewLineItem {
  code: string;
  qty: number;
  days: number;
}

export interface CheckoutPreviewResult {
  total_amount: number;
  patient_copay: number;
  claim_amount: number;
  special_code: string | null;
}

export interface ClaimPayment {
  id: string;
  claim_id: string;
  patient_name: string;
  method: "cash" | "card" | "transfer";
  claim_amount: number;
  amount: number;
  paid_at: string;
  processed_by_name: string;
}

export async function createClaimPayment(
  claimId: string,
  method: "cash" | "card" | "transfer",
  amount: number
): Promise<ClaimPayment> {
  return apiCall(`/api/billing/claims/${claimId}/payments`, {
    method: "POST",
    body: JSON.stringify({ method, amount }),
  });
}

export interface ClaimPaymentListResult {
  total: number;
  page: number;
  size: number;
  items: ClaimPayment[];
}

export interface ClaimPaymentSummary {
  today_total: number;
  month_total: number;
  cash_ratio: number;
  card_ratio: number;
}

export async function listClaimPayments(params: {
  start_date?: string;
  end_date?: string;
  method?: string;
  patient_id?: string;
  page?: number;
  size?: number;
}): Promise<ClaimPaymentListResult> {
  const qs = new URLSearchParams();
  if (params.start_date) qs.set("start_date", params.start_date);
  if (params.end_date) qs.set("end_date", params.end_date);
  if (params.method) qs.set("method", params.method);
  if (params.patient_id) qs.set("patient_id", params.patient_id);
  qs.set("page", String(params.page ?? 1));
  qs.set("size", String(params.size ?? 20));
  return apiCall(`/api/billing/payments?${qs.toString()}`);
}

export async function getClaimPaymentSummary(params: {
  start_date?: string;
  end_date?: string;
  method?: string;
}): Promise<ClaimPaymentSummary> {
  const qs = new URLSearchParams();
  if (params.start_date) qs.set("start_date", params.start_date);
  if (params.end_date) qs.set("end_date", params.end_date);
  if (params.method) qs.set("method", params.method);
  return apiCall(`/api/billing/payments/summary?${qs.toString()}`);
}

export async function previewCheckoutBilling(
  patientId: string,
  lineItems: CheckoutPreviewLineItem[]
): Promise<CheckoutPreviewResult> {
  return apiCall("/api/billing/checkout-preview", {
    method: "POST",
    body: JSON.stringify({ patient_id: patientId, line_items: lineItems }),
  });
}

export async function updateClaimBillingAgent(
  claimId: string,
  billingAgentCode: string | null,
  billingAgentName: string | null,
): Promise<{ id: string; billing_agent_code: string | null; billing_agent_name: string | null }> {
  return apiCall(`/api/billing/claims/${claimId}/billing-agent`, {
    method: "PATCH",
    body: JSON.stringify({ billing_agent_code: billingAgentCode, billing_agent_name: billingAgentName }),
  });
}

export interface ClaimReviewResult {
  id: string;
  claim_id: string | null;
  receipt_number: string;
  review_type: string;
  result_code: string;
  original_amount: number;
  approved_amount: number;
  reduced_amount: number;
  reduce_reason: string | null;
  review_date: string;
  received_at: string;
  raw_content: string | null;
}

export interface ClaimReviewResultListResponse {
  total: number;
  page: number;
  size: number;
  items: ClaimReviewResult[];
}

export async function uploadReviewResults(file: File): Promise<{ inserted: number; skipped: number }> {
  const token = localStorage.getItem("token");
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/api/billing/claims/review-results/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "심사결과 업로드 실패");
  }
  return res.json();
}

export async function getReviewResults(params?: {
  startDate?: string;
  endDate?: string;
  resultCode?: string;
  page?: number;
  size?: number;
}): Promise<ClaimReviewResultListResponse> {
  const query = new URLSearchParams();
  if (params?.startDate) query.set("start_date", params.startDate);
  if (params?.endDate) query.set("end_date", params.endDate);
  if (params?.resultCode) query.set("result_code", params.resultCode);
  query.set("page", String(params?.page ?? 1));
  query.set("size", String(params?.size ?? 20));
  const url = `${BASE_URL}/api/billing/claims/review-results?${query.toString()}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("심사결과 목록 조회 실패");
  return res.json();
}

export async function getReviewResult(id: string): Promise<ClaimReviewResult> {
  const res = await fetch(`${BASE_URL}/api/billing/claims/review-results/${id}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("심사결과 상세 조회 실패");
  return res.json();
}
