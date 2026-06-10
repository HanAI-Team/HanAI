import React, { useEffect, useState } from "react";
import { ActivityIndicator, AppState, Linking, Text, View } from "react-native";
import { Mic, FolderOpen, Settings } from "lucide-react-native";
import {
  getRecordingPermissionsAsync,
  requestRecordingPermissionsAsync,
} from "expo-audio";
import { Button } from "../components/Button";

type Status = "loading" | "prompt" | "denied" | "granted";

export function PermissionsScreen({ onGranted }: { onGranted: () => void }) {
  const [status, setStatus] = useState<Status>("loading");
  const [requesting, setRequesting] = useState(false);

  const checkStatus = async () => {
    const result = await getRecordingPermissionsAsync();
    if (result.granted) {
      setStatus("granted");
      onGranted();
    } else if (!result.canAskAgain) {
      setStatus("denied");
    } else {
      setStatus("prompt");
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && status === "denied") {
        checkStatus();
      }
    });
    return () => subscription.remove();
  }, [status]);

  const handleRequest = async () => {
    setRequesting(true);
    const result = await requestRecordingPermissionsAsync();
    setRequesting(false);
    if (result.granted) {
      setStatus("granted");
      onGranted();
    } else if (!result.canAskAgain) {
      setStatus("denied");
    }
  };

  if (status === "granted") return null;

  if (status === "loading") {
    return (
      <View className="flex-1 bg-background items-center justify-center">
        <ActivityIndicator color="#EF6600" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-background items-center justify-center px-8">
      <View className="flex-row gap-4 mb-6">
        <View className="w-16 h-16 rounded-full bg-white border border-border items-center justify-center">
          <Mic size={28} color="#EF6600" />
        </View>
        <View className="w-16 h-16 rounded-full bg-white border border-border items-center justify-center">
          <FolderOpen size={28} color="#EF6600" />
        </View>
      </View>

      <Text className="text-lg font-medium text-text mb-2 text-center">
        권한이 필요합니다
      </Text>
      <Text className="text-sm text-subtext text-center mb-8 leading-5">
        Zinmac은 진료 음성 녹음을 위해 마이크 권한이,{"\n"}
        진료 자료 업로드를 위해 파일 접근 권한이 필요합니다.
      </Text>

      {status === "prompt" && (
        <Button
          label="권한 허용하기"
          onPress={handleRequest}
          loading={requesting}
        />
      )}

      {status === "denied" && (
        <View className="w-full gap-3">
          <Text className="text-sm text-primary text-center">
            설정에서 권한을 허용해주세요
          </Text>
          <Button
            label="설정으로 이동"
            onPress={() => Linking.openSettings()}
          />
          <View className="flex-row items-center justify-center gap-1.5 mt-1">
            <Settings size={12} color="#8A8480" />
            <Text className="text-xs text-muted">
              설정 &gt; Zinmac &gt; 마이크 권한을 허용해주세요
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}
