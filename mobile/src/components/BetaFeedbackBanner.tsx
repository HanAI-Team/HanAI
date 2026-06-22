import React, { useEffect, useState } from "react";
import { Linking, Pressable, Text, View } from "react-native";
import * as SecureStore from "expo-secure-store";
import { MessageCircle, X } from "lucide-react-native";

const FORM_URL = "https://forms.gle/6HANKvSxdvfwKXFP9";
const DISMISS_KEY = "beta-feedback-banner-dismissed";

export function BetaFeedbackBanner() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    SecureStore.getItemAsync(DISMISS_KEY).then((value) => setDismissed(value === "1"));
  }, []);

  const dismiss = () => {
    setDismissed(true);
    SecureStore.setItemAsync(DISMISS_KEY, "1");
  };

  if (dismissed) return null;

  return (
    <View className="flex-row items-center gap-2 bg-panel border border-border rounded-lg px-4 py-3">
      <MessageCircle size={14} color="#8A8480" />
      <Pressable
        onPress={() => Linking.openURL(FORM_URL)}
        className="flex-1 flex-row items-center"
      >
        <Text className="flex-1 text-xs text-subtext">
          사용해보신 소감을 들려주세요{" "}
          <Text className="text-primary font-medium">의견 남기기</Text>
        </Text>
      </Pressable>
      <Pressable onPress={dismiss}>
        <X size={14} color="#B0AAA4" />
      </Pressable>
    </View>
  );
}
