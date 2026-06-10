import React from "react";
import { Text, View } from "react-native";

export function EmptyState({ message }: { message: string }) {
  return (
    <View className="py-16 items-center justify-center">
      <Text className="text-sm text-muted">{message}</Text>
    </View>
  );
}
