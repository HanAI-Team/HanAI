import React from "react";
import { Text, View } from "react-native";

export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  return (
    <View
      style={{ width: size, height: size, borderRadius: size / 2 }}
      className="bg-avatar items-center justify-center flex-shrink-0"
    >
      <Text className="text-white text-xs font-medium">{name[0]}</Text>
    </View>
  );
}
