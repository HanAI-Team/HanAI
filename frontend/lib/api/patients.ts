const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function getPatients(search?: string) {
  const url = search
    ? `${BASE_URL}/api/patients/?search=${search}`
    : `${BASE_URL}/api/patients/`
  const res = await fetch(url, { headers: getHeaders() })
  if (res.status === 404) return []
  if (!res.ok) throw new Error('환자 목록 조회 실패')
  const data = await res.json()
  return Array.isArray(data) ? data : (data.items || [])
}

export async function getPatient(id: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${id}`, { headers: getHeaders() })
  if (!res.ok) throw new Error('환자 조회 실패')
  return res.json()
}

export async function getPatientRecords(patientId: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${patientId}/records`, { headers: getHeaders() })
  if (!res.ok) throw new Error('진료 이력 조회 실패')
  return res.json() as Promise<{
    patient: any
    records: { id: string; recorded_at: string | null; chart_structured: string | null }[]
  }>
}

export async function importPatientsFromCsv(file: File) {
  const token = localStorage.getItem('token')
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE_URL}/api/patients/import/csv`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (!res.ok) throw new Error('CSV 가져오기 실패')
  return res.json() as Promise<{ inserted: number; skipped: number }>
}

export async function createPatient(data: {
  name: string
  birth_date?: string
  gender?: string
  phone?: string
  memo?: string
}) {
  const res = await fetch(`${BASE_URL}/api/patients/register`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '환자 등록 실패')
  }
  return res.json()
}
