import { apiCall } from './client'
import { DoctorWorkDays } from '@/types'

export async function listDoctorWorkDays(hospitalId: string): Promise<DoctorWorkDays[]> {
  return apiCall(`/api/hospitals/${hospitalId}/doctor-work-days`)
}

export async function createDoctorWorkDays(
  hospitalId: string,
  data: { doctor_id: string; claim_period_year: number; claim_period_month: number; work_days: number }
): Promise<DoctorWorkDays> {
  return apiCall(`/api/hospitals/${hospitalId}/doctor-work-days`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
