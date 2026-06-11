import { apiClient } from "./client";
import { ChartingResponse, MedicalRecord } from "../types";

export interface AudioFile {
  uri: string;
  name: string;
  type: string;
}

export async function uploadAndAnalyze(
  patientId: string,
  audio: AudioFile,
  medicalHistory?: string
): Promise<ChartingResponse> {
  const formData = new FormData();
  formData.append("patient_id", patientId);
  formData.append("audio", {
    uri: audio.uri,
    name: audio.name,
    type: audio.type,
  } as unknown as Blob);
  if (medicalHistory) formData.append("medical_history", medicalHistory);

  const res = await apiClient.post<ChartingResponse>("/api/charting/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function updateMedicalHistory(
  recordId: string,
  medicalHistory: string
) {
  const res = await apiClient.patch(
    `/api/charting/${recordId}/medical-history`,
    { medical_history: medicalHistory }
  );
  return res.data;
}

export async function finalizeRecord(
  recordId: string,
  chartStructured: string,
  selectedResult?: string
): Promise<MedicalRecord> {
  const res = await apiClient.patch<MedicalRecord>(
    `/api/charting/${recordId}/finalize`,
    { chart_structured: chartStructured, selected_result: selectedResult }
  );
  return res.data;
}
