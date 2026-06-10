import { apiClient } from "./client";
import { AskResponse, DiagnosisTextResponse } from "../types";

export async function diagnoseText(
  transcription: string
): Promise<DiagnosisTextResponse> {
  const res = await apiClient.post<DiagnosisTextResponse>("/api/diagnosis/", {
    transcription,
  });
  return res.data;
}

export async function askDiagnosis(question: string): Promise<AskResponse> {
  const res = await apiClient.post<AskResponse>("/api/diagnosis/ask", {
    question,
  });
  return res.data;
}
