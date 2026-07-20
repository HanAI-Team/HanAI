import { apiCall } from "./client";

export interface KcdSearchResult {
  code: string;
  korean_name: string;
  hanja?: string | null;
  category?: string | null;
  sex_restriction?: string | null;
  is_notifiable?: boolean;
}

export async function searchKcd(query: string): Promise<KcdSearchResult[]> {
  if (!query.trim()) return [];
  return apiCall(`/api/kcd/search?q=${encodeURIComponent(query.trim())}`);
}

export interface KcdValidateResult {
  code: string;
  is_valid: boolean;
  korean_name?: string | null;
  is_notifiable?: boolean | null;
  sex_restriction?: string | null;
  reason?: "not_found" | "expired" | "gender_mismatch" | null;
  error?: string | null;
}

export interface KcdValidateResponse {
  results: KcdValidateResult[];
  has_error: boolean;
}

export async function validateKcdCodes(
  codes: string[],
  patientGender?: "M" | "F"
): Promise<KcdValidateResponse> {
  if (codes.length === 0) return { results: [], has_error: false };
  return apiCall(`/api/kcd/validate`, {
    method: "POST",
    body: JSON.stringify({ codes, patient_gender: patientGender }),
  });
}
