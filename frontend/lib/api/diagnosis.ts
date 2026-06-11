import { apiCall } from './client'

export interface ChartingResponse {
  record_id: string
  transcription: string
  diagnosis: Record<string, unknown>
}

export async function uploadAndAnalyze(
  patientId: string,
  audioFile: File,
  medical_history?: string | null,
  symptom_text?: string | null,
): Promise<ChartingResponse> {
  const token = localStorage.getItem('token')
  const formData = new FormData()
  formData.append('patient_id', patientId)
  formData.append('audio', audioFile)
  if (medical_history) formData.append('medical_history', medical_history)
  if (symptom_text) formData.append('symptom_text', symptom_text)

  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const res = await fetch(`${BASE_URL}/api/charting/`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })
  if (!res.ok) throw new Error('분석 실패')
  return res.json()
}

export async function getDiagnosis(recordId: string) {
  return apiCall(`/api/diagnosis/${recordId}`)
}

export async function askDiagnosis(question: string): Promise<{ answer: string }> {
  return apiCall('/api/diagnosis/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}

export async function diagnoseText(
  transcription: string,
  medical_history?: string | null,
): Promise<{ result: Record<string, unknown> }> {
  return apiCall('/api/diagnosis/', {
    method: 'POST',
    body: JSON.stringify({
      transcription,
      ...(medical_history != null ? { medical_history } : {}),
    }),
  })
}
