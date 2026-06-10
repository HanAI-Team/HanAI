import React from "react";
import { View, ViewProps } from "react-native";

export function Card({ className = "", children, ...props }: ViewProps & { className?: string }) {
  return (
    <View
      className={`bg-white border border-border rounded-lg p-4 ${className}`}
      {...props}
    >
      {children}
    </View>
  );
}
