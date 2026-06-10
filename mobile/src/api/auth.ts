import { apiClient } from "./client";
import { Doctor, TokenResponse } from "../types";

export async function login(
  license_number: string,
  password: string
): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/api/auth/login", {
    license_number,
    password,
  });
  return res.data;
}

export async function staffLogin(
  email: string,
  password: string
): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/api/auth/staff/login", {
    email,
    password,
  });
  return res.data;
}

export async function getMe(): Promise<Doctor> {
  // /api/auth/me is doctor-only; staff tokens 401 here, so skip the global
  // 401 -> logout redirect for this request.
  const res = await apiClient.get<Doctor>("/api/auth/me", {
    skipAuthRedirect: true,
  });
  return res.data;
}

export async function changePassword(
  current_password: string,
  new_password: string
): Promise<{ message: string }> {
  const res = await apiClient.put("/api/auth/password", {
    current_password,
    new_password,
  });
  return res.data;
}
