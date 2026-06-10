import React, { useState } from "react";
import { Alert, ScrollView, Text, TextInput, View, Pressable } from "react-native";
import { Pencil } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { PatientStackParamList } from "../../navigation/types";
import { Avatar } from "../../components/Avatar";
import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import { updatePatient } from "../../api/patients";
import { getErrorMessage } from "../../api/client";
import { formatPatientSubtext } from "../../utils/chart";

type Props = NativeStackScreenProps<PatientStackParamList, "PatientDetail">;

export function PatientDetailScreen({ route }: Props) {
  const { patient: initialPatient } = route.params;
  const [patient, setPatient] = useState(initialPatient);
  const [editing, setEditing] = useState(false);
  const [memoDraft, setMemoDraft] = useState(patient.memo || "");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => updatePatient(patient.id, { memo: memoDraft.trim() }),
    onSuccess: (updated) => {
      setPatient(updated);
      setEditing(false);
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
    onError: (error) => {
      Alert.alert("저장 실패", getErrorMessage(error, "메모 저장에 실패했습니다"));
    },
  });

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Card className="items-center py-6">
        <Avatar name={patient.name} size={56} />
        <Text className="text-base font-medium text-text mt-3">{patient.name}</Text>
        <Text className="text-xs text-subtext mt-1">{formatPatientSubtext(patient)}</Text>
        {patient.phone && (
          <Text className="text-xs text-subtext mt-0.5">{patient.phone}</Text>
        )}
      </Card>

      <Card>
        <View className="flex-row items-center justify-between mb-2">
          <Text className="text-xs text-subtext uppercase tracking-wide">메모</Text>
          {!editing && (
            <Pressable onPress={() => { setMemoDraft(patient.memo || ""); setEditing(true); }}>
              <Pencil size={14} color="#8A8480" />
            </Pressable>
          )}
        </View>
        {editing ? (
          <View className="gap-2">
            <TextInput
              value={memoDraft}
              onChangeText={setMemoDraft}
              multiline
              numberOfLines={4}
              autoFocus
              placeholder="메모를 입력하세요"
              placeholderTextColor="#B0AAA4"
              className="bg-background border border-border rounded-md px-3 py-2 text-sm text-text min-h-[90px]"
              style={{ textAlignVertical: "top" }}
            />
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Button label="저장" onPress={() => mutation.mutate()} loading={mutation.isPending} />
              </View>
              <View className="flex-1">
                <Button label="취소" variant="outline" onPress={() => setEditing(false)} />
              </View>
            </View>
          </View>
        ) : (
          <Pressable onPress={() => { setMemoDraft(patient.memo || ""); setEditing(true); }}>
            <Text className={`text-sm ${patient.memo ? "text-text" : "text-muted"}`}>
              {patient.memo || "탭하여 메모 입력..."}
            </Text>
          </Pressable>
        )}
      </Card>
    </ScrollView>
  );
}
