const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface AuditLogItem {
  id: number;
  table_name: string;
  record_id: string;
  action: string;
  actor_id: string | null;
  actor_type: string | null;
  changed_at: string;
  detail: string | null;
}

export interface AuditLogFilters {
  table_name?: string;
  action?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}

export async function getAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogItem[]> {
  const params = new URLSearchParams();
  if (filters.table_name) params.set("table_name", filters.table_name);
  if (filters.action) params.set("action", filters.action);
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);
  if (filters.limit) params.set("limit", String(filters.limit));
  const res = await fetch(`${BASE_URL}/api/auth/audit-logs?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("접근 로그 조회 실패");
  return res.json();
}
