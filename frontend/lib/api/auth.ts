import { apiCall } from './client'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export type LoginLog = {
  id: string
  account_type: string
  success: boolean
  ip_address: string | null
  attempted_at: string
}
export async function getMe() {
  return apiCall('/api/auth/me')
}
export type AccountHistory = {
  id: string
  account_type: string
  action: string
  started_at: string
}

export async function getLoginLogs(): Promise<LoginLog[]> {
  return apiCall('/api/auth/login-logs')
}

export async function getAccountHistories(): Promise<AccountHistory[]> {
  return apiCall('/api/auth/account-histories')
}

export async function updateMyProfile(data: { birth_date?: string; chuna_training_certified?: boolean }) {
  return apiCall('/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  force_password_change: boolean
}

export async function login(license_number: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ license_number, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    const detail = err.detail
    throw new Error(typeof detail === 'string' ? detail : '로그인 실패')
  }
  return res.json()
}

export async function staffLogin(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/staff/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    const detail = err.detail
    throw new Error(typeof detail === 'string' ? detail : '로그인 실패')
  }
  return res.json()
}

export async function register(data: {
  name: string
  license_number: string
  password: string
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
    const detail = err.detail
    throw new Error(typeof detail === 'string' ? detail : '회원가입 실패')
  }
  return res.json()
}
