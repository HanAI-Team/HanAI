export interface Patient {
  id: string
  name: string
  age: number
  gender: string
  phone?: string
  created_at: string
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
}

export interface Doctor {
  id: string
  name: string
  email: string
  hospital_name: string
  license_number: string
}
