import { useCallback, useEffect, useRef } from "react";
import { Alert, AppState, AppStateStatus } from "react-native";
import { useAuthStore } from "../store/authStore";

const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const WARNING_BEFORE_MS = 5 * 60 * 1000;

export function useIdleTimeout() {
  const token = useAuthStore((state) => state.token);
  const lastActivityRef = useRef(Date.now());
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
  }, []);

  const scheduleTimers = useCallback(
    (remainingMs: number) => {
      clearTimers();
      const warningDelay = remainingMs - WARNING_BEFORE_MS;
      if (warningDelay > 0) {
        warningTimerRef.current = setTimeout(() => {
          Alert.alert("자동 로그아웃 안내", "5분 후 자동으로 로그아웃됩니다.");
        }, warningDelay);
      }
      logoutTimerRef.current = setTimeout(() => {
        useAuthStore.getState().logout();
      }, remainingMs);
    },
    [clearTimers]
  );

  const resetTimer = useCallback(() => {
    if (!useAuthStore.getState().token) return;
    lastActivityRef.current = Date.now();
    scheduleTimers(IDLE_TIMEOUT_MS);
  }, [scheduleTimers]);

  useEffect(() => {
    if (!token) {
      clearTimers();
      return;
    }

    resetTimer();

    const subscription = AppState.addEventListener(
      "change",
      (nextState: AppStateStatus) => {
        if (nextState !== "active") return;
        const elapsed = Date.now() - lastActivityRef.current;
        if (elapsed >= IDLE_TIMEOUT_MS) {
          useAuthStore.getState().logout();
        } else {
          scheduleTimers(IDLE_TIMEOUT_MS - elapsed);
        }
      }
    );

    return () => {
      clearTimers();
      subscription.remove();
    };
  }, [token, resetTimer, scheduleTimers, clearTimers]);

  return { resetTimer };
}
