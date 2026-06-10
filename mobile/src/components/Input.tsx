import React, { useState } from "react";
import { Text, TextInput, TextInputProps, View } from "react-native";

interface InputProps extends TextInputProps {
  label?: string;
}

export function Input({ label, className = "", ...props }: InputProps) {
  const [focused, setFocused] = useState(false);

  return (
    <View>
      {label && (
        <Text className="text-xs text-subtext uppercase tracking-wider mb-1.5">
          {label}
        </Text>
      )}
      <TextInput
        placeholderTextColor="#B0AAA4"
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        className={`w-full bg-white border rounded-md px-4 py-3 text-sm text-text ${
          focused ? "border-primary" : "border-borderStrong"
        } ${className}`}
        {...props}
      />
    </View>
  );
}
