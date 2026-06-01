const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function login(license_number: string) {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ license_number }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '로그인 실패')
  }
  return res.json()
}

export async function register(data: {
  name: string
  license_number: string
  clinic_name: string
  clinic_address?: string
  clinic_phone?: string
}) {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '회원가입 실패')
  }
  return res.json()
}
