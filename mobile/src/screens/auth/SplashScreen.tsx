import React, { useEffect } from "react";
import { Text, View } from "react-native";

export function SplashScreen({ onFinish }: { onFinish: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onFinish, 2000);
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <View className="flex-1 bg-[#232323] items-center justify-center">
      <Text className="text-white text-5xl tracking-tight" style={{ fontFamily: "serif" }}>
        Zinmac
      </Text>
      <View className="w-12 h-0.5 bg-primary mt-5" />
      <Text className="text-[#A09892] mt-6 text-xs tracking-widest absolute bottom-16">
        AI 한의 진료 보조 시스템
      </Text>
    </View>
  );
}
