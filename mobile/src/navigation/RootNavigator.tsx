import React, { useEffect, useState } from "react";
import { AppState, AppStateStatus, StyleSheet, View } from "react-native";
import { Lock } from "lucide-react-native";
import { NavigationContainer } from "@react-navigation/native";
import { useAuthStore } from "../store/authStore";
import { useIdleTimeout } from "../hooks/useIdleTimeout";
import { AuthNavigator } from "./AuthNavigator";
import { MainTabNavigator } from "./MainTabNavigator";

export function RootNavigator() {
  const token = useAuthStore((state) => state.token);
  const { resetTimer } = useIdleTimeout();
  const [isBackgrounded, setIsBackgrounded] = useState(false);

  useEffect(() => {
    if (!token) {
      setIsBackgrounded(false);
      return;
    }

    const subscription = AppState.addEventListener(
      "change",
      (nextState: AppStateStatus) => {
        setIsBackgrounded(nextState !== "active");
      }
    );

    return () => {
      subscription.remove();
    };
  }, [token]);

  return (
    <View className="flex-1" onTouchStart={token ? resetTimer : undefined}>
      <NavigationContainer>
        {token ? <MainTabNavigator /> : <AuthNavigator />}
      </NavigationContainer>
      {token && isBackgrounded && (
        <View
          style={StyleSheet.absoluteFill}
          className="bg-zinc-900 items-center justify-center"
        >
          <Lock size={40} color="#71717a" />
        </View>
      )}
    </View>
  );
}
