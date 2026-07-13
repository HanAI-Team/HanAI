import React from "react";
import { View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { useAuthStore } from "../store/authStore";
import { useIdleTimeout } from "../hooks/useIdleTimeout";
import { AuthNavigator } from "./AuthNavigator";
import { MainTabNavigator } from "./MainTabNavigator";

export function RootNavigator() {
  const token = useAuthStore((state) => state.token);
  const { resetTimer } = useIdleTimeout();

  return (
    <View className="flex-1" onTouchStart={token ? resetTimer : undefined}>
      <NavigationContainer>
        {token ? <MainTabNavigator /> : <AuthNavigator />}
      </NavigationContainer>
    </View>
  );
}
