import React from "react";
import { Text, View } from "react-native";

export function Tag({ label }: { label: string }) {
  return (
    <View className="px-2 py-0.5 bg-panel border border-border rounded mr-1 mb-1">
      <Text className="text-xs text-tag">{label}</Text>
    </View>
  );
}
