import { apiClient } from "./client";
import { StaffAccount } from "../types";

export async function getStaffList(): Promise<StaffAccount[]> {
  const res = await apiClient.get<StaffAccount[]>("/api/staff/");
  return res.data;
}
