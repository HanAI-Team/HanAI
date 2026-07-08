const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function getStats(): Promise<{
  total_patients: number
  today_records: number
  recent_records: { patient_id: string; record_id: string; patient_name: string; recorded_at: string | null; chart_structured: string | null }[]
}> {
  const res = await fetch(`${BASE_URL}/api/patients/stats`, { headers: getHeaders() })
  if (!res.ok) throw new Error('통계 조회 실패')
  return res.json()
}
