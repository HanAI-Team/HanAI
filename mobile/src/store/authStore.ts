import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import { Doctor } from "../types";
import { getMe } from "../api/auth";
import { setUnauthorizedHandler } from "../api/client";

interface AuthState {
  token: string | null;
  doctor: Doctor | null;
  isHydrated: boolean;
  hydrate: () => Promise<void>;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  doctor: null,
  isHydrated: false,
  hydrate: async () => {
    const token = await SecureStore.getItemAsync("token");
    if (!token) {
      set({ isHydrated: true });
      return;
    }
    set({ token, isHydrated: true });
    try {
      const doctor = await getMe();
      set({ doctor });
    } catch {
      // token may be invalid; the response interceptor will log out on 401
    }
  },
  login: async (token: string) => {
    await SecureStore.setItemAsync("token", token);
    set({ token });
    try {
      const doctor = await getMe();
      set({ doctor });
    } catch {
      // staff accounts have no /api/auth/me profile
    }
  },
  logout: () => {
    SecureStore.deleteItemAsync("token");
    set({ token: null, doctor: null });
  },
}));

setUnauthorizedHandler(() => {
  useAuthStore.getState().logout();
});
