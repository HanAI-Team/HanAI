import React from "react";
import { Pressable, Text, View } from "react-native";
import { ChevronRight } from "lucide-react-native";
import { Avatar } from "./Avatar";
import { Patient } from "../types";
import { formatPatientSubtext } from "../utils/chart";

export function PatientListItem({
  patient,
  onPress,
}: {
  patient: Patient;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-row items-center gap-3 px-4 py-3.5 border-b border-panel bg-white active:bg-panel"
    >
      <Avatar name={patient.name} size={36} />
      <View className="flex-1">
        <Text className="text-sm font-medium text-text">{patient.name}</Text>
        <Text className="text-xs text-subtext mt-0.5">
          {formatPatientSubtext(patient)}
        </Text>
      </View>
      <ChevronRight size={16} color="#B0AAA4" />
    </Pressable>
  );
}
