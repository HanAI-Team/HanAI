import { apiClient } from "./client";
import { ChartingResponse } from "../types";

export interface AudioFile {
  uri: string;
  name: string;
  type: string;
}

export async function uploadAndAnalyze(
  patientId: string,
  audio: AudioFile
): Promise<ChartingResponse> {
  const formData = new FormData();
  formData.append("patient_id", patientId);
  formData.append("audio", {
    uri: audio.uri,
    name: audio.name,
    type: audio.type,
  } as unknown as Blob);

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
