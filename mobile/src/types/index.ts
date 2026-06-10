export interface Patient {
  id: string;
  name: string;
  age?: number;
  gender?: string;
  phone?: string;
  birth_date?: string;
  memo?: string;
  created_at: string;
}

export interface PatientListResponse {
  total: number;
  page: number;
  size: number;
  items: Patient[];
}

export interface MedicalRecord {
  id: string;
  patient_id: string;
  doctor_id: string;
  hospital_id: string;
  raw_transcription?: string | null;
  chart_structured?: string | null;
  audio_file_url?: string | null;
  status: string;
  recorded_at?: string | null;
  created_at?: string | null;
  medical_history?: string | null;
}

export interface PatientRecordsResponse {
  patient: Patient;
  records: {
    id: string;
    recorded_at: string | null;
    chart_structured: string | null;
    raw_transcription: string | null;
    medical_history: string | null;
  }[];
}

export interface SasangConstitution {
  type: string;
  confidence?: "high" | "medium" | "low";
  evidence?: string[];
}

export interface TkmDiagnosis {
  diagnosis_name: string;
  pattern_differentiation?: string;
  etiology_pathogenesis?: string;
}

export interface WesternDiagnosis {
  name: string;
  icd_code?: string | null;
}

export interface HerbalComposition {
  herb: string;
  dosage: string;
}

export interface HerbalPrescription {
  name_kr: string;
  name_cn?: string;
  composition: HerbalComposition[];
  source?: string | null;
  rationale?: string;
  contraindications?: string[];
}

export interface AcupuncturePoint {
  point_kr: string;
  point_code: string;
  location?: string;
  rationale?: string;
}

export interface DiagnosisData {
  emergency_alert?: {
    is_emergency: boolean;
    reason?: string | null;
    recommendation?: string | null;
  };
  sasang_constitution?: SasangConstitution;
  tkm_diagnosis?: TkmDiagnosis;
  western_diagnosis?: WesternDiagnosis;
  herbal_prescription?: HerbalPrescription;
  acupuncture_prescription?: AcupuncturePoint[];
  follow_up_questions?: string[];
  disclaimer?: string;
}

export interface DiagnosisDual {
  dataset_based: DiagnosisData;
  claude_based: DiagnosisData;
}

export type DiagnosisResult = DiagnosisData | DiagnosisDual;

export interface ChartingResponse {
  record_id: string;
  transcription: string;
  diagnosis: DiagnosisResult;
}

export interface DiagnosisRecordResponse {
  record_id: string;
  diagnosis: DiagnosisResult;
}

export interface DiagnosisTextResponse {
  result: DiagnosisResult;
}

export interface AskResponse {
  answer: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Doctor {
  id: string;
  name: string;
  hospital_id: string;
  role: string;
  license_number: string;
}

export interface FeedbackResponse {
  id: string;
  is_helpful: boolean;
  comment?: string | null;
}

export interface StaffAccount {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}
