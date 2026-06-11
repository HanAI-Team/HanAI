import { apiClient } from "./client";
import { AskResponse, DiagnosisTextResponse } from "../types";

export async function diagnoseText(
  transcription: string,
  medicalHistory?: string
): Promise<DiagnosisTextResponse> {
  const res = await apiClient.post<DiagnosisTextResponse>("/api/diagnosis/", {
    transcription,
    ...(medicalHistory ? { medical_history: medicalHistory } : {}),
  });
  return res.data;
}

export async function askDiagnosis(question: string): Promise<AskResponse> {
  const res = await apiClient.post<AskResponse>("/api/diagnosis/ask", {
    question,
  });
  return res.data;
}
