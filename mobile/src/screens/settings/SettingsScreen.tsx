import React, { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react-native";
import { useAuthStore } from "../../store/authStore";
import { Card } from "../../components/Card";
import { Input } from "../../components/Input";
import { Button } from "../../components/Button";
import { changePassword } from "../../api/auth";
import { getErrorMessage } from "../../api/client";

const BETA_FEEDBACK_FORM_URL = "https://forms.gle/6HANKvSxdvfwKXFP9";

export function SettingsScreen() {
  const doctor = useAuthStore((state) => state.doctor);
  const logout = useAuthStore((state) => state.logout);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: (error) => {
      Alert.alert("변경 실패", getErrorMessage(error, "비밀번호 변경에 실패했습니다"));
    },
  });

  const handleSubmit = () => {
    if (newPassword !== confirmPassword) {
      Alert.alert("오류", "새 비밀번호가 일치하지 않습니다.");
      return;
    }
    const hasLetter = /[a-zA-Z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
    if (newPassword.length < 8 || !hasLetter || !hasNumber || !hasSpecial) {
      Alert.alert("오류", "비밀번호는 8자 이상, 영문/숫자/특수문자를 포함해야 합니다.");
      return;
    }
    mutation.mutate();
  };

  const handleLogout = () => {
    Alert.alert("로그아웃", "로그아웃 하시겠습니까?", [
      { text: "취소", style: "cancel" },
      { text: "로그아웃", style: "destructive", onPress: logout },
    ]);
  };

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 16 }}>
      <Card>
        <Text className="text-xs font-medium text-text uppercase tracking-wide mb-3">
          프로필 정보
        </Text>
        <View className="gap-1">
          <Text className="text-xs text-subtext">이름</Text>
          <Text className="text-sm text-text mb-2">{doctor?.name || "-"}</Text>
          <Text className="text-xs text-subtext">면허번호</Text>
          <Text className="text-sm text-text mb-2">{doctor?.license_number || "-"}</Text>
          <Text className="text-xs text-subtext">권한</Text>
          <Text className="text-sm text-text">{doctor?.role || "-"}</Text>
        </View>
      </Card>

      <Card>
        <Text className="text-xs font-medium text-text uppercase tracking-wide mb-4">
          비밀번호 변경
        </Text>
        <View className="gap-3">
          <Input
            label="현재 비밀번호"
            value={currentPassword}
            onChangeText={setCurrentPassword}
            secureTextEntry
          />
          <Input
            label="새 비밀번호"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry
          />
          <Input
            label="새 비밀번호 확인"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
          />
          <Button
            label={success ? "✓ 변경되었습니다" : "비밀번호 변경"}
            onPress={handleSubmit}
            loading={mutation.isPending}
            disabled={!currentPassword || !newPassword || !confirmPassword}
          />
        </View>
      </Card>

      <Card>
        <Text className="text-xs font-medium text-text uppercase tracking-wide mb-4">계정</Text>
        <Button label="로그아웃" variant="outline" onPress={handleLogout} />
      </Card>

      <Card>
        <Pressable
          onPress={() => Linking.openURL(BETA_FEEDBACK_FORM_URL)}
          className="flex-row items-center justify-between"
        >
          <Text className="text-sm text-text">베타 피드백 남기기</Text>
          <MessageSquare size={18} color="#8A8480" />
        </Pressable>
      </Card>
    </ScrollView>
  );
}
