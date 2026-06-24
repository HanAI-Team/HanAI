import { apiCall } from "./client";

export interface KcdSearchResult {
  code: string;
  korean_name: string;
  hanja?: string | null;
  category?: string | null;
}

export async function searchKcd(query: string): Promise<KcdSearchResult[]> {
  if (!query.trim()) return [];
  return apiCall(`/api/kcd/search?q=${encodeURIComponent(query.trim())}`);
}
