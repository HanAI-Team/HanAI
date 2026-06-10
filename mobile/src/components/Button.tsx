import React from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  PressableProps,
} from "react-native";

type Variant = "primary" | "outline" | "danger";

interface ButtonProps extends Omit<PressableProps, "children"> {
  label: string;
  variant?: Variant;
  loading?: boolean;
  className?: string;
}

const variantStyles: Record<Variant, string> = {
  primary: "bg-primary border-primary",
  outline: "bg-white border-borderStrong",
  danger: "bg-[#232323] border-[#232323]",
};

const variantTextStyles: Record<Variant, string> = {
  primary: "text-white",
  outline: "text-subtext",
  danger: "text-white",
};

export function Button({
  label,
  variant = "primary",
  loading = false,
  disabled,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      disabled={isDisabled}
      className={`w-full rounded-md py-3 border items-center justify-center flex-row gap-2 ${
        variantStyles[variant]
      } ${isDisabled ? "opacity-50" : ""} ${className}`}
      {...props}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === "outline" ? "#8A8480" : "#FFFFFF"}
          size="small"
        />
      ) : (
        <Text
          className={`text-sm font-medium ${variantTextStyles[variant]}`}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}
