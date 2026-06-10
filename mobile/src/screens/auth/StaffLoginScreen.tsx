import React, { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useMutation } from "@tanstack/react-query";
import { staffLogin } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { getErrorMessage } from "../../api/client";

export function StaffLoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const authLogin = useAuthStore((state) => state.login);

  const mutation = useMutation({
    mutationFn: () => staffLogin(email, password),
    onSuccess: async (data) => {
      await authLogin(data.access_token);
    },
    onError: (error) => {
      Alert.alert("로그인 실패", getErrorMessage(error, "로그인에 실패했습니다"));
    },
  });

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-[#232323]"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1 }}
        keyboardShouldPersistTaps="handled"
      >
        <View className="flex-1 items-center justify-center py-16">
          <Text className="text-white text-5xl tracking-tight">Zinmac</Text>
          <Text className="text-[#A09892] mt-3 text-xs tracking-widest">
            AI 한의 진료 보조 시스템
          </Text>
          <View className="w-12 h-0.5 bg-primary mt-5" />
        </View>

        <View className="bg-panel rounded-t-[28px] px-7 pt-8 pb-12">
          <Text className="text-xl font-medium text-text mb-1">
            간호사 로그인
          </Text>
          <Text className="text-sm text-subtext mb-7">
            병원 직원 계정으로 로그인하세요
          </Text>

          <View className="gap-4">
            <Input
              label="이메일"
              placeholder="이메일을 입력하세요"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <Input
              label="비밀번호"
              placeholder="비밀번호를 입력하세요"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
            />
            <Button
              label="로그인"
              loading={mutation.isPending}
              disabled={!email || !password}
              onPress={() => mutation.mutate()}
              className="mt-1"
            />
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
