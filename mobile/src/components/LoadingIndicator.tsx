import React from "react";
import { ActivityIndicator, View } from "react-native";

export function LoadingIndicator({ className = "" }: { className?: string }) {
  return (
    <View className={`py-16 items-center justify-center ${className}`}>
      <ActivityIndicator color="#EF6600" />
    </View>
  );
}
