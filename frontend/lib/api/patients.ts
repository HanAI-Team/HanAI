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
  if (!res.ok) throw new Error('환자 목록 조회 실패')
  const data = await res.json()
  return Array.isArray(data) ? data : (data.items || [])
}

export async function getPatient(id: string) {
  const res = await fetch(`${BASE_URL}/api/patients/${id}`, { headers: getHeaders() })
  if (!res.ok) throw new Error('환자 조회 실패')
  return res.json()
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
