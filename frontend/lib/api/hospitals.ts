import { apiCall } from './client'
import { Hospital } from '@/types'

export async function updateHospital(
  id: string,
  data: { name?: string; address?: string; phone?: string; institution_code?: string; agency_code?: string }
): Promise<Hospital> {
  return apiCall(`/api/hospitals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
