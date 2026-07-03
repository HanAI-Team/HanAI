import { apiCall } from './client'

export const getMe = async () => {
  try {
    const me = await apiCall('/api/auth/me')
    return me
  } catch (error) {
    console.error('내 정보를 가져오는데 실패했습니다:', error)
  }
}