export interface Patient {
  id: string
  name: string
  age: number
  gender: string
  phone?: string
  birth_date?: string
  address?: string
  memo?: string
  created_at: string
  insurance_type?: string
  disability_grade?: string
  medical_aid_grade?: string
  rrn_masked?: string
}

export interface DiagnosisResult {
  id: string
  patient_id: string
  constitution: string        // 사상체질
  diagnosis: string           // 한의학 진단
  western_diagnosis: string   // 양방 진단
  prescription: string        // 한약 처방
  herbs: string[]             // 약재
  acupuncture: string[]       // 침 처방
  created_at: string
  claudeBased?: DiagnosisResult  // 클로드 AI 기반 (일반 지식) 결과
  chiefComplaintSummary?: string // 주소증 핵심 요약
}

export interface Staff {
  id: string
  name: string
  email: string
  role: string
  is_active: boolean
}

export interface Doctor {
  id: string
  name: string
  email: string
  hospital_name: string
  license_number: string
}

export interface Hospital {
  id: string
  name: string
  address?: string
  phone?: string
  institution_code?: string
  agency_code?: string
  approval_no?: string
  session_timeout_minutes?: number | null
}

export interface DoctorWorkDays {
  id: number
  doctor_id: string | null
  claim_period_year: number
  claim_period_month: number
  doctor_birth_date: string
  work_days: number
}

export interface Me {
  id: string
  name: string
  role: string
  hospital_id: string
  hospital_name?: string | null
  institution_code?: string | null
  agency_code?: string | null
  approval_no?: string | null
  session_timeout_minutes?: number | null
  license_number?: string
  username?: string
  email?: string
  birth_date?: string | null
  tier?: "basic" | "premium"
  expired_at?: string | null
  is_expired?: boolean
  chuna_training_certified?: boolean
  chuna_training_banner_seen?: boolean
}
