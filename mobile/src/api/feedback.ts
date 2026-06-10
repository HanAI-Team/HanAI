import { apiClient } from "./client";
import { FeedbackResponse } from "../types";

export async function submitFeedback(data: {
  medical_record_id: string;
  is_helpful: boolean;
  comment?: string;
}): Promise<FeedbackResponse> {
  const res = await apiClient.post<FeedbackResponse>("/api/feedback/", data);
  return res.data;
}
