import { apiCall } from './client'
import { Staff } from '@/types'

export async function getStaffList(): Promise<Staff[]> {
  return apiCall('/api/staff/')
}

export async function createStaff(data: {
  name: string
  email: string
  password: string
  role: string
}): Promise<Staff> {
  return apiCall('/api/staff/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deactivateStaff(id: string): Promise<Staff> {
  return apiCall(`/api/staff/${id}/deactivate`, { method: 'PATCH' })
}

export async function activateStaff(id: string): Promise<Staff> {
  return apiCall(`/api/staff/${id}/activate`, { method: 'PATCH' })
}
