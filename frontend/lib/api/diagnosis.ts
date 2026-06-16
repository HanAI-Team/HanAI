import { apiCall } from './client'

export type ChartingEvent =
  | { type: 'transcription'; transcription: string }
  | { type: 'dataset_based'; data: Record<string, unknown> }
  | { type: 'claude_based'; data: Record<string, unknown> }
  | { type: 'done'; record_id: string }
  | { type: 'error'; detail: string }

export async function uploadAndAnalyze(
  patientId: string,
  audioFiles: File[],
  medical_history: string | null | undefined,
  symptom_text: string | null | undefined,
  onEvent: (event: ChartingEvent) => void,
): Promise<void> {
  const token = localStorage.getItem('token')
  const formData = new FormData()
  formData.append('patient_id', patientId)
  audioFiles.forEach((file) => formData.append('audios', file))
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
  if (!res.ok || !res.body) throw new Error('분석 실패')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let newlineIndex
    while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim()
      buffer = buffer.slice(newlineIndex + 1)
      if (line) onEvent(JSON.parse(line) as ChartingEvent)
    }
  }
  const last = buffer.trim()
  if (last) onEvent(JSON.parse(last) as ChartingEvent)
}

export async function getDiagnosis(recordId: string) {
  return apiCall(`/api/diagnosis/${recordId}`)
}

export async function finalizeRecord(
  recordId: string,
  chartStructured: string,
  selectedResult?: string,
) {
  return apiCall(`/api/charting/${recordId}/finalize`, {
    method: 'PATCH',
    body: JSON.stringify({
      chart_structured: chartStructured,
      selected_result: selectedResult,
    }),
  })
}

export async function askDiagnosis(question: string): Promise<{ answer: string }> {
  return apiCall('/api/diagnosis/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}

export async function askDiagnosisStream(
  question: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = localStorage.getItem('token')
  const res = await fetch(`${BASE_URL}/api/diagnosis/ask-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question }),
  })
  if (!res.ok || !res.body) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || '오류가 발생했습니다')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }
}

export async function publicAskStream(
  question: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const res = await fetch(`${BASE_URL}/api/diagnosis/public-ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok || !res.body) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || '오류가 발생했습니다')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }
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
