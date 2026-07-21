const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiCall(
  endpoint: string,
  options: RequestInit = {}
) {
  const token = localStorage.getItem('token')
  
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('인증이 만료되었습니다')
  }

  if (!res.ok) {
    const error = await res.json()
    const detail = error.detail
    let message = '오류가 발생했습니다'
    if (typeof detail === 'string' && detail) {
      message = detail
    } else if (detail && typeof detail === 'object') {
      if (Array.isArray(detail.errors) && detail.errors.length > 0) {
        message = detail.errors.map((e: any) => e.message).filter(Boolean).join('\n')
      } else if (detail.message) {
        message = detail.message
      }
    }
    throw new Error(message)
  }

  return res.json()
}
