import "./global.css";
import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SplashScreenNative from "expo-splash-screen";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "./src/store/authStore";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { PermissionsScreen } from "./src/screens/PermissionsScreen";
import { SplashScreen } from "./src/screens/auth/SplashScreen";

SplashScreenNative.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1 },
  },
});

export default function App() {
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const hydrate = useAuthStore((state) => state.hydrate);
  const [permissionsGranted, setPermissionsGranted] = useState(false);
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    SplashScreenNative.hideAsync();
  }, []);

  if (showSplash || !isHydrated) {
    return (
      <View className="flex-1">
        <SplashScreen onFinish={() => setShowSplash(false)} />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <SafeAreaProvider>
          {permissionsGranted ? (
            <RootNavigator />
          ) : (
            <PermissionsScreen onGranted={() => setPermissionsGranted(true)} />
          )}
          <StatusBar style="auto" />
        </SafeAreaProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
