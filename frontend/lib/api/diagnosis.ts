import { apiCall } from './client'

export async function uploadAndAnalyze(
  patientId: string,
  audioFile: File
) {
  const token = localStorage.getItem('token')
  const formData = new FormData()
  formData.append('patient_id', patientId)
  formData.append('audio', audioFile)

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/charting/`,
    {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    }
  )
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

export async function diagnoseText(transcription: string): Promise<{ result: Record<string, unknown> }> {
  return apiCall('/api/diagnosis/', {
    method: 'POST',
    body: JSON.stringify({ transcription }),
  })
}
