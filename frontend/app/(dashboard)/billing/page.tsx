"use client";
import {
  ClaimListItem,
  ClaimPrescription,
  ClaimStatement,
  RejectionCodeSearchResult,
  StatementProcedureRow,
  bulkDownloadEdi,
  claimTypeLabel,
  createClaimPayment,
  deleteLineItem,
  downloadSamFiles,
  getClaimLineItems,
  getClaimPrescription,
  getClaimStatement,
  getClaims,
  resubmitClaim,
  searchRejectionCodes,
  statusLabel,
  updateClaimApproval,
  updateClaimBillingAgent,
} from "@/lib/api/billing";
import type { ClaimSummary } from "@/types/billing";
import { useIsExpired } from "@/contexts/SubscriptionContext";
import PaymentHistoryModal from "@/components/billing/PaymentHistoryModal";
import { Fragment, useEffect, useState } from "react";
import ReviewResultsTab from "./ReviewResultsTab";

const STATUS_FILTERS = [
  { key: "", label: "전체" },
  { key: "draft", label: "작성중" },
  { key: "submitted", label: "제출완료" },
  { key: "approved", label: "승인" },
  { key: "rejected", label: "반려" },
];

function getCurrentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function BillingPage() {
  const isExpired = useIsExpired();
  const [activeTab, setActiveTab] = useState<"submit" | "review">("submit");
  const [claims, setClaims] = useState<ClaimListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(getCurrentMonth());
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState<string | null>(null);
  const [resubmitTarget, setResubmitTarget] = useState<ClaimListItem | null>(null);
  const [billingAgentTarget, setBillingAgentTarget] = useState<ClaimListItem | null>(null);
  const [testMode, setTestMode] = useState(false);
  const [editingApprovalId, setEditingApprovalId] = useState<string | null>(null);
  const [approvalDraft, setApprovalDraft] = useState("");
  const [paymentMethodDraft, setPaymentMethodDraft] = useState<Record<string, "cash" | "card" | "transfer">>({});
  const [payingId, setPayingId] = useState<string | null>(null);
  const [paymentHistoryOpen, setPaymentHistoryOpen] = useState(false);
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(null);
  const [lineItemsCache, setLineItemsCache] = useState<Record<string, ClaimSummary>>({});
  const [expandLoading, setExpandLoading] = useState<string | null>(null);
  const [deletingItemId, setDeletingItemId] = useState<string | null>(null);

  async function toggleExpand(claimId: string) {
    if (expandedClaimId === claimId) {
      setExpandedClaimId(null);
      return;
    }
    setExpandedClaimId(claimId);
    if (!lineItemsCache[claimId]) {
      setExpandLoading(claimId);
      try {
        const detail = await getClaimLineItems(claimId);
        setLineItemsCache((prev) => ({ ...prev, [claimId]: detail }));
      } catch (e) {
        alert(e instanceof Error ? e.message : "청구 항목을 불러오지 못했습니다.");
      } finally {
        setExpandLoading(null);
      }
    }
  }

  async function handleDeleteLineItem(claimId: string, lineItemId: string) {
    setDeletingItemId(lineItemId);
    try {
      const result = await deleteLineItem(lineItemId);
      if ("deletedClaim" in result) {
        setExpandedClaimId(null);
        setLineItemsCache((prev) => {
          const next = { ...prev };
          delete next[claimId];
          return next;
        });
      } else {
        setLineItemsCache((prev) => ({ ...prev, [claimId]: result }));
      }
      reload();
    } catch (e) {
      alert(e instanceof Error ? e.message : "항목 삭제에 실패했습니다.");
    } finally {
      setDeletingItemId(null);
    }
  }

  async function handleCompletePayment(claim: ClaimListItem) {
    const method = paymentMethodDraft[claim.id] || "cash";
    setPayingId(claim.id);
    try {
      await createClaimPayment(claim.id, method, claim.claim_amount);
      setClaims((prev) => prev.map((c) => (c.id === claim.id ? { ...c, is_paid: true } : c)));
    } catch (e) {
      alert(e instanceof Error ? e.message : "수납 처리에 실패했습니다.");
    } finally {
      setPayingId(null);
    }
  }

  async function saveApproval(claimId: string) {
    const trimmed = approvalDraft.trim();
    setEditingApprovalId(null);
    try {
      const res = await updateClaimApproval(claimId, trimmed || null);
      setClaims((prev) =>
        prev.map((c) => (c.id === claimId ? { ...c, approval_no: res.approval_no } : c))
      );
    } catch {
      // 저장 실패 시 값은 그대로 두고 다음 클릭에서 재시도
    }
  }

  function reload() {
    setLoading(true);
    setSelected(new Set());
    getClaims({ month: month || undefined, status: statusFilter || undefined })
      .then(setClaims)
      .catch(() => setClaims([]))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [month, statusFilter]);

  const counts = {
    전체: claims.length,
    작성중: claims.filter((c) => c.status === "draft").length,
    제출완료: claims.filter((c) => c.status === "submitted").length,
    승인: claims.filter((c) => c.status === "approved").length,
    반려: claims.filter((c) => c.status === "rejected").length,
  };

  function toggleAll() {
    if (selected.size === claims.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(claims.map((c) => c.id)));
    }
  }

  function toggleOne(id: string) {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  }

  async function handleDownload(id: string) {
    setDownloading(id);
    try {
      await downloadSamFiles(id, testMode);
    } catch (e) {
      alert(e instanceof Error ? e.message : "SAM File 다운로드에 실패했습니다.");
    } finally {
      setDownloading(null);
    }
  }

  async function handleBulkDownload() {
    if (selected.size === 0) return;
    setDownloading("bulk");
    try {
      await bulkDownloadEdi([...selected], testMode);
    } catch (e) {
      alert(e instanceof Error ? e.message : "일괄 EDI 다운로드에 실패했습니다.");
    } finally {
      setDownloading(null);
    }
  }

  async function handleReceiptPrint(claim: ClaimListItem) {
    const printWindow = window.open("", "_blank", "width=600,height=860");
    if (!printWindow) {
      alert("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = localStorage.getItem("token");
    const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

    let hospitalName = "-";
    let institutionCode = "-";
    try {
      const meRes = await fetch(`${base}/api/auth/me`, { headers: authHeaders });
      if (meRes.ok) {
        const me = await meRes.json();
        if (me.institution_code) institutionCode = me.institution_code;
        if (me.hospital_name) hospitalName = me.hospital_name;
      }
    } catch {}

    // 급여 공단부담금 = 청구금액(claim_amount), 본인부담금 = patient_copay
    // 비급여 = total_amount - patient_copay - claim_amount (0원인 경우가 일반적)
    const nonCovered = Math.max(0, claim.total_amount - claim.patient_copay - claim.claim_amount);
    const grandTotal = claim.patient_copay + claim.claim_amount + nonCovered;

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>영수증 - ${claim.patient_name}</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:28px 36px;max-width:560px;margin:0 auto}`
      + `h1{font-size:18px;font-weight:bold;text-align:center;letter-spacing:6px;margin-bottom:3px}`
      + `.subtitle{text-align:center;font-size:11px;color:#555;margin-bottom:12px}`
      + `hr{border:none;border-top:1.5px solid #000;margin:10px 0}`
      + `hr.thin{border-top:1px solid #ccc;margin:8px 0}`
      + `.grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px 16px;font-size:13px;margin:8px 0}`
      + `.item{display:flex;gap:6px;align-items:baseline}`
      + `.lbl{color:#444;min-width:72px;font-weight:500;flex-shrink:0}`
      + `table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}`
      + `th{border:1px solid #999;padding:6px 10px;background:#f0f0f0;font-weight:500}`
      + `th.left{text-align:left}`
      + `th.right{text-align:right}`
      + `td{border:1px solid #ccc;padding:6px 10px}`
      + `td.item-name{text-align:left}`
      + `td.amount{text-align:right}`
      + `.totals{font-size:13px;margin-top:4px}`
      + `.t-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee}`
      + `.t-row.bold{font-weight:bold;font-size:14px;border-top:1.5px solid #000;border-bottom:none;padding-top:10px;margin-top:4px}`
      + `.notice{margin-top:14px;font-size:11px;color:#888;border-top:1px dashed #bbb;padding-top:8px;text-align:center}`
      + `@media print{body{padding:0}@page{margin:12mm;size:A4}}`
      + `</style></head><body>`
      + `<h1>진료비 계산서·영수증</h1>`
      + `<div class="subtitle">「국민건강보험 요양급여의 기준에 관한 규칙」별지 제9호 서식</div>`
      + `<hr/>`
      + `<div class="grid2">`
      + `<div class="item"><span class="lbl">요양기관명</span><span>${hospitalName}</span></div>`
      + `<div class="item"><span class="lbl">요양기관기호</span><span>${institutionCode}</span></div>`
      + `<div class="item"><span class="lbl">환자명</span><span>${claim.patient_name}</span></div>`
      + `<div class="item"><span class="lbl">진료기간</span><span>${claim.claim_period}</span></div>`
      + `</div>`
      + `<hr/>`
      + `<table>`
      + `<thead><tr><th class="left">항목</th><th class="right">금액</th></tr></thead>`
      + `<tbody>`
      + `<tr><td class="item-name">급여 - 본인부담금</td><td class="amount">${claim.patient_copay.toLocaleString()}원</td></tr>`
      + `<tr><td class="item-name">급여 - 공단부담금</td><td class="amount">${claim.claim_amount.toLocaleString()}원</td></tr>`
      + `<tr><td class="item-name">비급여</td><td class="amount">${nonCovered.toLocaleString()}원</td></tr>`
      + `</tbody></table>`
      + `<hr class="thin"/>`
      + `<div class="totals">`
      + `<div class="t-row"><span>합계</span><span>${grandTotal.toLocaleString()}원</span></div>`
      + `<div class="t-row bold"><span>본인부담금 합계</span><span>${claim.patient_copay.toLocaleString()}원</span></div>`
      + `</div>`
      + `<div class="notice">본 영수증은 보험 청구 목적으로 발급된 것입니다.</div>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  async function handleStatementPrint(claim: ClaimListItem) {
    const printWindow = window.open("", "_blank", "width=900,height=1000");
    if (!printWindow) {
      alert("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    let s: ClaimStatement;
    try {
      s = await getClaimStatement(claim.id);
    } catch {
      printWindow.close();
      alert("명세서 데이터를 불러오지 못했습니다.");
      return;
    }

    const won = (n: number) => n.toLocaleString() + "원";

    // 진찰료(01) / 투약료(11) / 시술및처치료(04, mok별) / 검사료(05) / 비급여(09) 로 재분류
    const exam = s.procedures.filter((p) => p.hang === "01");
    const med = s.procedures.filter((p) => p.hang === "11");
    const treat = s.procedures.filter((p) => p.hang === "04");
    const test = s.procedures.filter((p) => p.hang === "05");
    const nonBenefit = s.procedures.filter((p) => p.hang === "09" || p.is_non_benefit);

    const treatByMok: Record<string, { label: string; rows: StatementProcedureRow[] }> = {
      "01": { label: "침술", rows: [] },
      "02": { label: "구술", rows: [] },
      "03": { label: "부항술", rows: [] },
      "04": { label: "처치료", rows: [] },
      기타: { label: "기타", rows: [] },
    };
    for (const p of treat) {
      (treatByMok[p.mok] ?? treatByMok["기타"]).rows.push(p);
    }

    const rowHtml = (label: string, p: StatementProcedureRow) =>
      `<tr><td class="left">${label}</td><td>${p.count}</td><td>${won(p.unit_price)}</td><td>${won(p.amount)}</td></tr>`;

    const sectionRows = (rows: StatementProcedureRow[]) =>
      rows.length === 0
        ? `<tr><td class="left">-</td><td>-</td><td>-</td><td>-</td></tr>`
        : rows.map((p) => rowHtml(p.name, p)).join("");

    const treatSectionHtml = Object.values(treatByMok)
      .filter((g) => g.rows.length > 0)
      .map((g) => `<tr class="group"><td class="left" colspan="4">${g.label}</td></tr>` + sectionRows(g.rows))
      .join("") || `<tr><td class="left">-</td><td>-</td><td>-</td><td>-</td></tr>`;

    const copayRows: { label: string; amount: number }[] = [
      { label: "A. 100분의50 본인부담", amount: s.procedures.filter((p) => p.copay_rate_label === "A").reduce((a, p) => a + p.amount, 0) },
      { label: "B. 100분의80 본인부담", amount: s.procedures.filter((p) => p.copay_rate_label === "B").reduce((a, p) => a + p.amount, 0) },
      { label: "D. 100분의30 본인부담", amount: 0 },
      { label: "E. 100분의90 본인부담", amount: 0 },
      { label: "U. 건강보험(의료급여) 100분의100 본인부담", amount: 0 },
      { label: "V. 보훈 등 100분의100 본인부담", amount: 0 },
      { label: "W. 비급여", amount: nonBenefit.reduce((a, p) => a + p.amount, 0) },
    ];

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>요양급여비용명세서 - ${s.patient_name}</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:20px 28px;font-size:12px}`
      + `h1{font-size:16px;font-weight:bold;text-align:center;margin-bottom:2px}`
      + `.subtitle{text-align:center;font-size:10px;color:#555;margin-bottom:10px}`
      + `table{width:100%;border-collapse:collapse;font-size:11px;margin:6px 0}`
      + `th,td{border:1px solid #999;padding:4px 6px;text-align:center}`
      + `th{background:#f0f0f0;font-weight:500}`
      + `td.left{text-align:left}`
      + `tr.group td{background:#fafafa;font-weight:600;text-align:left}`
      + `.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:2px 20px;margin-bottom:8px}`
      + `.info-item{display:flex;gap:6px}`
      + `.info-item span.lbl{color:#444;min-width:80px;font-weight:500}`
      + `.section-title{font-weight:bold;margin:10px 0 2px;font-size:12px}`
      + `@media print{body{padding:0}@page{margin:10mm;size:A4}}`
      + `</style></head><body>`
      + `<h1>요양급여비용명세서 (한방외래)</h1>`
      + `<div class="subtitle">별지 제18호서식 (서식번호 GI013)</div>`
      + `<div class="info-grid">`
      + `<div class="info-item"><span class="lbl">요양기관명</span><span>${s.hospital_name}</span></div>`
      + `<div class="info-item"><span class="lbl">요양기관기호</span><span>${s.institution_code}</span></div>`
      + `<div class="info-item"><span class="lbl">환자성명</span><span>${s.patient_name}</span></div>`
      + `<div class="info-item"><span class="lbl">주민등록번호</span><span>${s.birth_masked}</span></div>`
      + `<div class="info-item"><span class="lbl">상병명</span><span>${s.disease_names.join(", ") || "-"}</span></div>`
      + `<div class="info-item"><span class="lbl">특정기호</span><span>${s.special_code || "-"}</span></div>`
      + `<div class="info-item"><span class="lbl">진료과목</span><span>한방</span></div>`
      + `<div class="info-item"><span class="lbl">청구기간</span><span>${claim.claim_period}</span></div>`
      + `<div class="info-item"><span class="lbl">면허종류/번호</span><span>${s.license_type} / ${s.license_no}</span></div>`
      + `<div class="info-item"><span class="lbl">내원일수</span><span>${s.visit_count}일 (${s.visit_dates.join(", ")})</span></div>`
      + `</div>`

      + `<div class="section-title">1. 진찰료</div>`
      + `<table><thead><tr><th class="left">구분</th><th>실시횟수</th><th>단가</th><th>금액</th></tr></thead><tbody>${sectionRows(exam)}</tbody></table>`

      + `<div class="section-title">3. 투약료</div>`
      + `<table><thead><tr><th class="left">구분</th><th>실시횟수</th><th>단가</th><th>금액</th></tr></thead><tbody>${sectionRows(med)}</tbody></table>`

      + `<div class="section-title">4. 시술 및 처치료</div>`
      + `<table><thead><tr><th class="left">구분</th><th>실시횟수</th><th>단가</th><th>금액</th></tr></thead><tbody>${treatSectionHtml}</tbody></table>`

      + `<div class="section-title">5. 검사료</div>`
      + `<table><thead><tr><th class="left">구분</th><th>실시횟수</th><th>단가</th><th>금액</th></tr></thead><tbody>${sectionRows(test)}</tbody></table>`

      + (nonBenefit.length > 0
        ? `<div class="section-title">비급여</div>`
          + `<table><thead><tr><th class="left">구분</th><th>실시횟수</th><th>단가</th><th>금액</th></tr></thead><tbody>${sectionRows(nonBenefit)}</tbody></table>`
        : "")

      + `<div class="section-title">본인부담구분별 금액</div>`
      + `<table><thead><tr><th class="left">구분</th><th>진료행위 금액</th></tr></thead><tbody>`
      + copayRows.map((r) => `<tr><td class="left">${r.label}</td><td>${won(r.amount)}</td></tr>`).join("")
      + `</tbody></table>`

      + `<div class="section-title">심사내역</div>`
      + `<table><tbody>`
      + `<tr><td class="left">11. 소계</td><td>${won(s.subtotal)}</td><td class="left">19. 요양급여비용총액2·진료비총액</td><td>${won(s.benefit_total_2)}</td></tr>`
      + `<tr><td class="left">12. 가산율</td><td>${(s.surcharge_rate * 100).toFixed(0)}%</td><td class="left">20. 보훈청구액</td><td>${won(s.veterans_claim)}</td></tr>`
      + `<tr><td class="left">13. 요양급여비용총액1</td><td>${won(s.benefit_total_1)}</td><td class="left">21. 건강보험 100분의100본인부담금총액</td><td>${won(s.full_price_copay_total)}</td></tr>`
      + `<tr><td class="left">14. 본인일부부담금</td><td>${won(s.copayment)}</td><td class="left">22. 보훈본인일부부담금</td><td>${won(s.veterans_copay)}</td></tr>`
      + `<tr><td class="left">15. 지원금</td><td>${won(s.support_fund)}</td><td class="left">23. 100분의100미만 총액</td><td>${won(s.under_full_total)}</td></tr>`
      + `<tr><td class="left">16. 장애인의료비</td><td>${won(s.disability_medical_cost)}</td><td class="left">24. 100분의100미만 본인일부부담금</td><td>${won(s.under_full_copay)}</td></tr>`
      + `<tr><td class="left">17. 청구액</td><td>${won(s.claim_amount)}</td><td class="left">25. 100분의100미만 청구액</td><td>${won(s.under_full_claim)}</td></tr>`
      + `<tr><td class="left">18. 본인부담상한액초과금</td><td>${won(s.upper_limit_excess)}</td><td class="left">26. 100분의100미만 보훈청구액</td><td>${won(s.under_full_veterans_claim)}</td></tr>`
      + `<tr><td class="left">비급여총액</td><td>${won(s.non_benefit_total)}</td><td></td><td></td></tr>`
      + `</tbody></table>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  async function handlePrescriptionPrint(claim: ClaimListItem) {
    const printWindow = window.open("", "_blank", "width=900,height=1000");
    if (!printWindow) {
      alert("팝업이 차단되어 인쇄할 수 없습니다. 팝업 차단을 해제해주세요.");
      return;
    }

    let p: ClaimPrescription;
    try {
      p = await getClaimPrescription(claim.id);
    } catch (e) {
      printWindow.close();
      alert(e instanceof Error ? e.message : "처방전 데이터를 불러오지 못했습니다.");
      return;
    }

    // 약품 항목 입력 기능이 없어 표는 빈 줄로 출력 — 수기로 작성
    const blankDrugRows = Array.from({ length: 6 })
      .map(() => `<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr>`)
      .join("");

    const html = "<!DOCTYPE html>"
      + `<html lang="ko"><head><meta charset="UTF-8"/>`
      + `<title>처방전 - ${p.patient_name}</title>`
      + `<style>`
      + `*{margin:0;padding:0;box-sizing:border-box}`
      + `body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;color:#000;background:#fff;padding:20px 28px;font-size:12px}`
      + `h1{font-size:18px;font-weight:bold;text-align:center;letter-spacing:6px;margin-bottom:2px}`
      + `.subtitle{text-align:center;font-size:10px;color:#555;margin-bottom:4px}`
      + `.checks{text-align:center;font-size:11px;margin-bottom:10px}`
      + `table{width:100%;border-collapse:collapse;font-size:11px;margin:6px 0}`
      + `th,td{border:1px solid #999;padding:5px 8px;text-align:center}`
      + `th{background:#f0f0f0;font-weight:500}`
      + `td.left{text-align:left}`
      + `td.label{background:#f7f7f7;font-weight:500;text-align:left;white-space:nowrap}`
      + `.section-title{font-weight:bold;margin:10px 0 2px;font-size:11px}`
      + `.notice{margin-top:4px;font-size:10px;color:#666}`
      + `@media print{body{padding:0}@page{margin:10mm;size:A4}}`
      + `</style></head><body>`
      + `<h1>처 방 전</h1>`
      + `<div class="checks">[✔]건강보험 [ ]의료급여 [ ]산업재해보험 [ ]자동차보험 [ ]기타( &nbsp;&nbsp;&nbsp; )</div>`

      + `<table><tbody>`
      + `<tr><td class="label" style="width:120px">요양기관기호</td><td colspan="5" class="left">${p.institution_code}</td></tr>`
      + `<tr>`
      + `<td class="label">발급 연월일 및 번호</td><td class="left" colspan="2">${p.issue_date} - 제 ${p.issue_no} 호</td>`
      + `<td class="label" style="width:70px">명칭</td><td class="left" colspan="2">${p.hospital_name}</td>`
      + `</tr>`
      + `<tr>`
      + `<td class="label" rowspan="2">환자</td><td class="left">성명</td><td class="left">${p.patient_name}</td>`
      + `<td class="label">전화번호</td><td class="left" colspan="2">${p.hospital_phone}</td>`
      + `</tr>`
      + `<tr>`
      + `<td class="left">주민등록번호</td><td class="left">${p.patient_birth_masked}</td>`
      + `<td class="label">전자우편</td><td class="left" colspan="2"></td>`
      + `</tr>`
      + `<tr>`
      + `<td class="label">질병분류기호</td><td class="left" colspan="2">${p.disease_names.join(", ") || ""}</td>`
      + `<td class="label">처방 의료인의 성명</td><td class="left">${p.doctor_name}<br/>(서명 또는 날인)</td>`
      + `<td class="left">면허종류: ${p.license_type}<br/>면허번호: 제 ${p.license_no} 호</td>`
      + `</tr>`
      + `</tbody></table>`
      + `<div class="notice">※ 환자가 요구하면 질병분류기호를 적지 않습니다.</div>`

      + `<div class="section-title">처방 의약품</div>`
      + `<table><thead><tr>`
      + `<th class="left">처방 의약품의 명칭 및 코드</th><th>1회 투약량</th><th>1일 투여횟수</th>`
      + `<th>총 투약일수</th><th>본인부담률<br/>구분코드</th><th>용법</th>`
      + `</tr></thead><tbody>${blankDrugRows}</tbody></table>`

      + `<table><tbody>`
      + `<tr><td class="label" style="width:260px">주사제 처방명세 ([ ]원내조제, [ ]원외처방)</td><td class="left"></td><td class="label" style="width:120px">본인부담 구분기호</td><td class="left"></td></tr>`
      + `<tr><td class="label">사용기간</td><td class="left" colspan="3">발급일부터 ( 2 )일간 — 사용기간 내에 약국에 제출하여야 합니다.</td></tr>`
      + `</tbody></table>`

      + `<div class="notice">※ 의료법 시행규칙 [별지 제9호서식]</div>`
      + `</body></html>`;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onafterprint = () => printWindow.close();
    printWindow.print();
  }

  return (
    <div className="p-6 md:p-8 max-w-[1100px] mx-auto">
      {/* 헤더 */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl text-text">보험 청구</h1>
          <p className="text-xs text-subtext mt-1">EDI 파일 생성 및 심사결과 조회</p>
        </div>
        {activeTab === "submit" && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setPaymentHistoryOpen(true)}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-subtext hover:text-text hover:border-text transition-all"
            >
              수납 내역
            </button>
            <button
              onClick={() => setTestMode((v) => !v)}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-all ${
                testMode
                  ? "border-amber-400 bg-amber-50 text-amber-700 hover:bg-amber-100"
                  : "border-border text-subtext hover:text-text"
              }`}
            >
              {testMode ? "테스트 모드 ON" : "테스트 모드"}
            </button>
          </div>
        )}
      </div>

      {/* 송신/수신 서브탭 */}
      <div className="flex border-b border-border mb-6">
        {([
          { id: "submit" as const, label: "송신 이력" },
          { id: "review" as const, label: "심사결과" },
        ]).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-5 py-2.5 text-xs transition-all border-b-2 ${
              activeTab === id
                ? "text-[#EF6600] border-[#EF6600]"
                : "text-subtext border-transparent hover:text-text"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "review" && <ReviewResultsTab />}

      {activeTab === "submit" && (
      <>
      {/* 테스트 모드 배너 */}
      {testMode && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-400 bg-amber-50 px-4 py-3">
          <span className="text-sm font-semibold text-amber-700">⚠ 테스트 모드</span>
          <span className="text-xs text-amber-700">
            다운로드되는 EDI 파일의 작성자란에 <strong>「상시점검」</strong>이 기재됩니다. 심평원 인증에 영향 없이 레이아웃 오류만 검증합니다.
          </span>
        </div>
      )}

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          { label: "전체", value: counts["전체"], color: "text-text" },
          { label: "작성중", value: counts["작성중"], color: "text-subtext" },
          { label: "제출완료", value: counts["제출완료"], color: "text-blue-500" },
          { label: "승인", value: counts["승인"], color: "text-green-500" },
          { label: "반려", value: counts["반려"], color: "text-red-500" },
        ].map((s) => (
          <div key={s.label} className="bg-card border border-border rounded-lg p-4">
            <div className="text-xs text-subtext uppercase tracking-wide mb-1">{s.label}</div>
            <div className={`text-3xl font-light ${s.color}`}>{loading ? "-" : s.value}</div>
          </div>
        ))}
      </div>

      {/* 필터 영역 */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-sm text-text"
        />
        <div className="flex gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                statusFilter === f.key
                  ? "bg-[#EF6600] border-[#EF6600] text-white"
                  : "border-border text-subtext hover:text-text"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        {selected.size > 0 && (
          <button
            onClick={() => {
              if (isExpired) {
                alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                return;
              }
              handleBulkDownload();
            }}
            disabled={downloading === "bulk"}
            className={`ml-auto px-4 py-1.5 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] disabled:opacity-50 transition-all ${
              isExpired ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            {downloading === "bulk" ? "생성 중..." : `EDI 일괄 다운로드 (${selected.size}건)`}
          </button>
        )}
      </div>

      {/* 테이블 */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr className="text-xs text-subtext">
              <th className="p-3 w-8">
                <input
                  type="checkbox"
                  checked={claims.length > 0 && selected.size === claims.length}
                  onChange={toggleAll}
                  className="cursor-pointer"
                />
              </th>
              <th className="p-3 text-left">환자명</th>
              <th className="p-3 text-left">청구월</th>
              <th className="p-3 text-left">상태</th>
              <th className="p-3 text-left">청구구분</th>
              <th className="p-3 text-right">급여합계</th>
              <th className="p-3 text-right">본인부담</th>
              <th className="p-3 text-right">청구금액</th>
              <th className="p-3 text-left">검사승인번호</th>
              <th className="p-3 text-center">수납</th>
              <th className="p-3 text-center">대행청구</th>
              <th className="p-3 text-center">EDI</th>
              <th className="p-3 text-center">영수증</th>
              <th className="p-3 text-center">명세서</th>
              <th className="p-3 text-center">처방전</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={15} className="p-8 text-center text-subtext text-xs">
                  불러오는 중...
                </td>
              </tr>
            ) : claims.length === 0 ? (
              <tr>
                <td colSpan={15} className="p-8 text-center text-subtext text-xs">
                  청구 내역이 없습니다.
                </td>
              </tr>
            ) : (
              claims.map((claim) => {
                const locked = claim.from_reception && !claim.is_paid;
                return (
                <Fragment key={claim.id}>
                <tr
                  className={`border-t border-border hover:bg-fill transition-colors ${
                    selected.has(claim.id) ? "bg-fill" : ""
                  }`}
                >
                  <td className="p-3 text-center">
                    <input
                      type="checkbox"
                      checked={selected.has(claim.id)}
                      onChange={() => toggleOne(claim.id)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td
                    className="p-3 text-text font-medium cursor-pointer select-none"
                    onClick={() => toggleExpand(claim.id)}
                  >
                    <span className="text-subtext mr-1">
                      {expandedClaimId === claim.id ? "▾" : "▸"}
                    </span>
                    {claim.patient_name}
                  </td>
                  <td className="p-3 text-subtext">{claim.claim_period}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        claim.status === "rejected"
                          ? "bg-red-500/10 text-red-500"
                          : claim.status === "approved"
                          ? "bg-green-500/10 text-green-500"
                          : claim.status === "submitted"
                          ? "bg-blue-500/10 text-blue-500"
                          : "bg-fill text-subtext"
                      }`}
                    >
                      {statusLabel(claim.status)}
                    </span>
                  </td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        claim.claim_type
                          ? "bg-blue-500/10 text-blue-500"
                          : "bg-fill text-subtext"
                      }`}
                    >
                      {claimTypeLabel(claim.claim_type)}
                    </span>
                  </td>
                  <td className="p-3 text-right text-text">
                    {claim.total_amount.toLocaleString()}원
                  </td>
                  <td className="p-3 text-right text-text">
                    {claim.patient_copay.toLocaleString()}원
                  </td>
                  <td className="p-3 text-right text-text font-medium">
                    {claim.claim_amount.toLocaleString()}원
                  </td>
                  <td className="p-3">
                    {editingApprovalId === claim.id ? (
                      <input
                        autoFocus
                        type="text"
                        maxLength={35}
                        value={approvalDraft}
                        onChange={(e) => setApprovalDraft(e.target.value)}
                        onBlur={() => saveApproval(claim.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") e.currentTarget.blur();
                        }}
                        className="w-full bg-fill border border-[#EF6600] rounded-md px-2 py-1 text-xs text-text outline-none"
                      />
                    ) : (
                      <button
                        onClick={() => {
                          setEditingApprovalId(claim.id);
                          setApprovalDraft(claim.approval_no || "");
                        }}
                        className="w-full text-left px-2 py-1 text-xs text-subtext hover:text-text hover:bg-fill rounded-md transition-colors"
                      >
                        {claim.approval_no || "-"}
                      </button>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    {!claim.from_reception ? (
                      <span className="text-xs text-muted">-</span>
                    ) : claim.is_paid ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/10 text-green-500">
                        수납완료
                      </span>
                    ) : (
                      <div className="flex items-center justify-center gap-1">
                        <select
                          value={paymentMethodDraft[claim.id] || "cash"}
                          onChange={(e) =>
                            setPaymentMethodDraft((prev) => ({
                              ...prev,
                              [claim.id]: e.target.value as "cash" | "card" | "transfer",
                            }))
                          }
                          className="bg-fill border border-border rounded-md px-1.5 py-1 text-xs text-text outline-none"
                        >
                          <option value="cash">현금</option>
                          <option value="card">카드</option>
                          <option value="transfer">계좌이체</option>
                        </select>
                        <button
                          onClick={() => handleCompletePayment(claim)}
                          disabled={payingId === claim.id}
                          className="px-2 py-1 text-xs rounded-md bg-[#EF6600] text-white hover:opacity-90 disabled:opacity-50 transition-all"
                        >
                          {payingId === claim.id ? "처리 중..." : "수납완료처리"}
                        </button>
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    <button
                      onClick={() => setBillingAgentTarget(claim)}
                      className={`px-2 py-0.5 rounded-full text-xs transition-colors ${
                        claim.billing_agent_code
                          ? "bg-blue-500/10 text-blue-500 hover:bg-blue-500/20"
                          : "border border-border text-subtext hover:text-text"
                      }`}
                      title={claim.billing_agent_name || undefined}
                    >
                      {claim.billing_agent_code ? claim.billing_agent_code : "미사용"}
                    </button>
                  </td>
                  <td className="p-3 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <button
                        onClick={() => {
                          if (isExpired) {
                            alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                            return;
                          }
                          handleDownload(claim.id);
                        }}
                        disabled={downloading === claim.id || locked}
                        className={`px-3 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text disabled:opacity-50 transition-all ${
                          isExpired || locked ? "opacity-50 cursor-not-allowed" : ""
                        }`}
                      >
                        {downloading === claim.id ? "생성 중..." : "다운로드"}
                      </button>
                      {claim.status === "rejected" && (
                        <button
                          onClick={() => {
                            if (isExpired) {
                              alert("구독이 만료됐습니다. 멤버십 페이지에서 갱신해주세요.");
                              return;
                            }
                            setResubmitTarget(claim);
                          }}
                          className={`px-3 py-1 text-xs rounded-md border border-[#EF6600] text-[#EF6600] hover:bg-[#EF6600] hover:text-white transition-all ${
                            isExpired ? "opacity-50 cursor-not-allowed" : ""
                          }`}
                        >
                          보완·추가청구
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="p-3 text-center">
                    {locked ? (
                      <span className="text-xs text-muted">수납 후 이용 가능</span>
                    ) : (
                      <button
                        onClick={() => handleReceiptPrint(claim)}
                        className="px-3 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-all"
                      >
                        출력
                      </button>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    {locked ? (
                      <span className="text-xs text-muted">수납 후 이용 가능</span>
                    ) : (
                      <button
                        onClick={() => handleStatementPrint(claim)}
                        className="px-3 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-all"
                      >
                        출력
                      </button>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    {locked ? (
                      <span className="text-xs text-muted">수납 후 이용 가능</span>
                    ) : (
                      <button
                        onClick={() => handlePrescriptionPrint(claim)}
                        className="px-3 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-all"
                      >
                        출력
                      </button>
                    )}
                  </td>
                </tr>
                {expandedClaimId === claim.id && (
                  <tr className="border-t border-border bg-fill">
                    <td colSpan={15} className="p-4">
                      {expandLoading === claim.id ? (
                        <div className="text-xs text-subtext py-2">불러오는 중...</div>
                      ) : !lineItemsCache[claim.id] ? (
                        <div className="text-xs text-subtext py-2">항목을 불러오지 못했습니다.</div>
                      ) : lineItemsCache[claim.id].lineItems.length === 0 ? (
                        <div className="text-xs text-subtext py-2">청구 항목이 없습니다.</div>
                      ) : (
                        <ul className="divide-y divide-border">
                          {lineItemsCache[claim.id].lineItems.map((li) => (
                            <li
                              key={li.id}
                              className="flex items-center justify-between py-2 text-xs"
                            >
                              <span className="text-text">
                                {li.name}{" "}
                                <span className="text-subtext">
                                  {li.amount.toLocaleString()}원
                                </span>
                              </span>
                              {claim.status === "draft" ? (
                                <button
                                  onClick={() => handleDeleteLineItem(claim.id, li.id)}
                                  disabled={deletingItemId === li.id}
                                  className="text-red-500 hover:underline disabled:opacity-40"
                                >
                                  {deletingItemId === li.id ? "삭제 중..." : "삭제"}
                                </button>
                              ) : (
                                <span className="text-muted">작성중 상태만 삭제 가능</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                )}
                </Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {resubmitTarget && (
        <ResubmissionModal
          claim={resubmitTarget}
          onClose={() => setResubmitTarget(null)}
          onDone={() => {
            setResubmitTarget(null);
            reload();
          }}
        />
      )}

      {paymentHistoryOpen && (
        <PaymentHistoryModal onClose={() => setPaymentHistoryOpen(false)} />
      )}
      {billingAgentTarget && (
        <BillingAgentModal
          claim={billingAgentTarget}
          onClose={() => setBillingAgentTarget(null)}
          onSaved={(code, name) => {
            setClaims((prev) =>
              prev.map((c) =>
                c.id === billingAgentTarget.id
                  ? { ...c, billing_agent_code: code, billing_agent_name: name }
                  : c
              )
            );
            setBillingAgentTarget(null);
          }}
        />
      )}
      </>
      )}
    </div>
  );
}

function ResubmissionModal({
  claim,
  onClose,
  onDone,
}: {
  claim: ClaimListItem;
  onClose: () => void;
  onDone: () => void;
}) {
  const [claimType, setClaimType] = useState<"supplement" | "addition">("supplement");
  const [receiptNo, setReceiptNo] = useState("");
  const [recordSerial, setRecordSerial] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [reasonQuery, setReasonQuery] = useState("");
  const [reasonResults, setReasonResults] = useState<RejectionCodeSearchResult[]>([]);
  const [reasonOpen, setReasonOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reasonQuery.trim()) {
      setReasonResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchRejectionCodes(reasonQuery, "심사불능")
        .then(setReasonResults)
        .catch(() => setReasonResults([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [reasonQuery]);

  function selectReason(item: RejectionCodeSearchResult) {
    setReasonCode(item.code);
    setReasonQuery(`${item.code} ${item.description}`);
    setReasonOpen(false);
    setReasonResults([]);
  }

  async function handleSubmit() {
    setError(null);
    if (!receiptNo || !recordSerial) {
      setError("접수번호와 명일련을 입력해주세요.");
      return;
    }
    if (claimType === "supplement" && !reasonCode) {
      setError("보완청구는 심사불능사유코드를 입력해주세요.");
      return;
    }
    setSubmitting(true);
    try {
      await resubmitClaim(claim.id, {
        claim_type: claimType,
        original_receipt_no: Number(receiptNo),
        original_record_serial: Number(recordSerial),
        rejection_reason_code: claimType === "supplement" ? reasonCode : undefined,
      });
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "처리에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div role="button" tabIndex={0} className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div role="button" tabIndex={0}
        className="bg-card border border-border rounded-lg p-6 w-[380px]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-lg text-text mb-1">보완·추가청구</h2>
        <p className="text-xs text-subtext mb-4">
          {claim.patient_name} · {claim.claim_period}
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-subtext mb-1">청구구분</label>
            <select
              value={claimType}
              onChange={(e) => setClaimType(e.target.value as "supplement" | "addition")}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            >
              <option value="supplement">보완청구</option>
              <option value="addition">추가청구</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-subtext mb-1">당초 청구명세서 접수번호</label>
            <input
              type="number"
              value={receiptNo}
              onChange={(e) => setReceiptNo(e.target.value)}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext mb-1">명일련</label>
            <input
              type="number"
              value={recordSerial}
              onChange={(e) => setRecordSerial(e.target.value)}
              className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
            />
          </div>
          {claimType === "supplement" && (
            <div className="relative">
              <label className="block text-xs text-subtext mb-1">심사불능사유코드</label>
              <input
                type="text"
                value={reasonQuery}
                onChange={(e) => {
                  setReasonQuery(e.target.value);
                  setReasonCode("");
                  setReasonOpen(true);
                }}
                onFocus={() => setReasonOpen(true)}
                onBlur={() => setTimeout(() => setReasonOpen(false), 150)}
                placeholder="코드 또는 사유 내용 검색"
                className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
              />
              {reasonOpen && reasonResults.length > 0 && (
                <ul className="absolute z-10 mt-1 w-full bg-card border border-border rounded-md max-h-48 overflow-y-auto shadow-lg">
                  {reasonResults.map((item) => (
                    <li key={`${item.code}-${item.detail_code}`}>
                      <button
                        type="button"
                        onMouseDown={() => selectReason(item)}
                        className="w-full text-left px-3 py-1.5 text-xs text-text hover:bg-fill transition-colors"
                      >
                        <span className="font-medium">{item.code}</span> {item.description}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 text-xs rounded-md border border-border text-subtext hover:text-text transition-all"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-3 py-2 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] disabled:opacity-50 transition-all"
          >
            {submitting ? "처리 중..." : "제출"}
          </button>
        </div>
      </div>
    </div>
  );
}

function BillingAgentModal({
  claim,
  onClose,
  onSaved,
}: {
  claim: ClaimListItem;
  onClose: () => void;
  onSaved: (code: string | null, name: string | null) => void;
}) {
  const [useAgent, setUseAgent] = useState(!!claim.billing_agent_code);
  const [code, setCode] = useState(claim.billing_agent_code || "");
  const [name, setName] = useState(claim.billing_agent_name || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    const finalCode = useAgent ? code.trim() || null : null;
    const finalName = useAgent ? name.trim() || null : null;
    setSubmitting(true);
    try {
      const res = await updateClaimBillingAgent(claim.id, finalCode, finalName);
      onSaved(res.billing_agent_code, res.billing_agent_name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div role="button" tabIndex={0} className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div role="button" tabIndex={0}
        className="bg-card border border-border rounded-lg p-6 w-[380px]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-lg text-text mb-1">대행청구</h2>
        <p className="text-xs text-subtext mb-4">
          {claim.patient_name} · {claim.claim_period}
        </p>

        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
            <input
              type="checkbox"
              checked={useAgent}
              onChange={(e) => setUseAgent(e.target.checked)}
              className="cursor-pointer"
            />
            대행청구 사용
          </label>
          {useAgent && (
            <>
              <div>
                <label className="block text-xs text-subtext mb-1">대행청구단체 코드</label>
                <input
                  type="text"
                  maxLength={5}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
                />
              </div>
              <div>
                <label className="block text-xs text-subtext mb-1">대행청구단체명</label>
                <input
                  type="text"
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-fill border border-border rounded-md px-3 py-1.5 text-sm text-text"
                />
              </div>
            </>
          )}
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 text-xs rounded-md border border-border text-subtext hover:text-text transition-all"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-3 py-2 text-xs rounded-md bg-[#EF6600] text-white hover:bg-[#d45a00] disabled:opacity-50 transition-all"
          >
            {submitting ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
