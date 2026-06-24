export interface BillableItem {
  id: string;
  name: string;
  sub: string;
  requiresHyeolmyeong: boolean;
}

export interface ClaimLineItem {
  id: string;
  name: string;
  code: string;
  amount: number;
  hyeolmyeongNames?: string[];
}

export interface ClaimSummary {
  id: string;
  patientId: string;
  billingMonth: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  totalAmount: number;
  lineItems: ClaimLineItem[];
}

export interface SelectedBillableItem {
  itemId: string;
  hyeolmyeongNames: string[];
}
