import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { useAuthStore } from "../store/authStore";
import { AuthNavigator } from "./AuthNavigator";
import { MainTabNavigator } from "./MainTabNavigator";

export function RootNavigator() {
  const token = useAuthStore((state) => state.token);

  return (
    <NavigationContainer>
      {token ? <MainTabNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
