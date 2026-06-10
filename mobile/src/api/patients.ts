import { apiClient } from "./client";
import { Patient, PatientListResponse, PatientRecordsResponse } from "../types";

export async function getPatients(
  page: number,
  search?: string
): Promise<PatientListResponse> {
  try {
    const res = await apiClient.get<PatientListResponse>("/api/patients/", {
      params: { page, size: 20, ...(search ? { search } : {}) },
    });
    return res.data;
  } catch (error: any) {
    if (error.response?.status === 404) {
      return { total: 0, page, size: 20, items: [] };
    }
    throw error;
  }
}

export async function getPatient(id: string): Promise<Patient> {
  const res = await apiClient.get<Patient>(`/api/patients/${id}`);
  return res.data;
}

export async function createPatient(data: {
  name: string;
  birth_date?: string;
  gender?: string;
  phone?: string;
  memo?: string;
}): Promise<Patient> {
  const res = await apiClient.post<Patient>("/api/patients/register", data);
  return res.data;
}

export async function updatePatient(
  id: string,
  data: { phone?: string; memo?: string }
): Promise<Patient> {
  const res = await apiClient.put<Patient>(`/api/patients/${id}`, data);
  return res.data;
}

export async function getPatientRecords(
  patientId: string
): Promise<PatientRecordsResponse> {
  const res = await apiClient.get<PatientRecordsResponse>(
    `/api/patients/${patientId}/records`
  );
  return res.data;
}

export async function saveRecord(
  patientId: string,
  chartStructured: string,
  rawTranscription?: string
) {
  const res = await apiClient.post(`/api/patients/${patientId}/records`, {
    chart_structured: chartStructured,
    raw_transcription: rawTranscription,
  });
  return res.data;
}
