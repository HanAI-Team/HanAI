import React, { useState } from "react";
import { Alert, ScrollView, Text, View, Pressable } from "react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { PatientStackParamList } from "../../navigation/types";
import { Input } from "../../components/Input";
import { Button } from "../../components/Button";
import { createPatient } from "../../api/patients";
import { getErrorMessage } from "../../api/client";

type Props = NativeStackScreenProps<PatientStackParamList, "AddPatient">;

const GENDER_OPTIONS = [
  { value: "male", label: "남" },
  { value: "female", label: "여" },
];

export function AddPatientScreen({ navigation }: Props) {
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      createPatient({
        name: name.trim(),
        birth_date: birthDate.trim() || undefined,
        gender: gender || undefined,
        phone: phone.trim() || undefined,
      }),
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      navigation.replace("PatientDetail", { patient });
    },
    onError: (error) => {
      Alert.alert("등록 실패", getErrorMessage(error, "환자 등록에 실패했습니다"));
    },
  });

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 16 }}>
      <Input label="이름 *" value={name} onChangeText={setName} placeholder="환자 이름" />
      <Input
        label="생년월일"
        value={birthDate}
        onChangeText={setBirthDate}
        placeholder="YYYY-MM-DD"
        keyboardType="numbers-and-punctuation"
      />
      <View>
        <Text className="text-xs text-subtext uppercase tracking-wider mb-1.5">성별</Text>
        <View className="flex-row gap-6">
          {GENDER_OPTIONS.map((opt) => (
            <Pressable
              key={opt.value}
              onPress={() => setGender(opt.value)}
              className="flex-row items-center gap-1.5"
            >
              <View
                className={`w-4 h-4 rounded-full border items-center justify-center ${
                  gender === opt.value ? "border-primary" : "border-borderStrong"
                }`}
              >
                {gender === opt.value && (
                  <View className="w-2 h-2 rounded-full bg-primary" />
                )}
              </View>
              <Text className="text-sm text-text">{opt.label}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      <Input
        label="전화번호"
        value={phone}
        onChangeText={setPhone}
        placeholder="010-0000-0000"
        keyboardType="phone-pad"
      />
      <Button
        label="등록"
        onPress={() => mutation.mutate()}
        loading={mutation.isPending}
        disabled={!name.trim()}
      />
    </ScrollView>
  );
}
