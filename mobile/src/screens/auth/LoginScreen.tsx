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
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { login } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { getErrorMessage } from "../../api/client";
import { AuthStackParamList } from "../../navigation/types";

export function LoginScreen() {
  const [licenseNumber, setLicenseNumber] = useState("");
  const [password, setPassword] = useState("");
  const authLogin = useAuthStore((state) => state.login);
  const navigation =
    useNavigation<NativeStackNavigationProp<AuthStackParamList, "Login">>();

  const mutation = useMutation({
    mutationFn: () => login(licenseNumber, password),
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
          <Text className="text-xl font-medium text-text mb-1">로그인</Text>
          <Text className="text-sm text-subtext mb-7">
            면허 한의사 전용 서비스입니다
          </Text>

          <View className="gap-4">
            <Input
              label="면허번호"
              placeholder="면허번호를 입력하세요"
              value={licenseNumber}
              onChangeText={setLicenseNumber}
              autoCapitalize="none"
              keyboardType="number-pad"
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
              disabled={!licenseNumber || !password}
              onPress={() => mutation.mutate()}
              className="mt-1"
            />
            <Button
              label="간호사로 로그인"
              variant="outline"
              onPress={() => navigation.navigate("StaffLogin")}
            />
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
