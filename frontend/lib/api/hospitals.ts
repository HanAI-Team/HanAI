import { apiCall } from './client'
import { Hospital } from '@/types'

export async function updateHospital(
  id: string,
  data: { name?: string; address?: string; phone?: string; institution_code?: string; agency_code?: string; approval_no?: string; session_timeout_minutes?: number }
): Promise<Hospital> {
  return apiCall(`/api/hospitals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
