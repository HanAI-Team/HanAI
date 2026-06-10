import React, { useEffect, useRef } from "react";
import { Animated, Pressable, Text, View } from "react-native";
import { Mic, Square } from "lucide-react-native";

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function WaveBar({ height, delay }: { height: number; delay: number }) {
  const anim = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(anim, {
          toValue: 1,
          duration: 300,
          delay,
          useNativeDriver: true,
        }),
        Animated.timing(anim, {
          toValue: 0.4,
          duration: 300,
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [anim, delay]);

  return (
    <Animated.View
      style={{
        width: 3,
        height,
        borderRadius: 2,
        backgroundColor: "#989689",
        transform: [{ scaleY: anim }],
      }}
    />
  );
}

export function RecordingCard({
  isRecording,
  hasRecording,
  durationMillis,
  onToggle,
}: {
  isRecording: boolean;
  hasRecording: boolean;
  durationMillis: number;
  onToggle: () => void;
}) {
  return (
    <View className="bg-white border border-border rounded-lg p-5">
      <Text className="text-xs text-subtext uppercase tracking-wide mb-3">
        음성 녹음
      </Text>
      <View className="items-center p-6 bg-background border border-border rounded-lg">
        <Pressable
          onPress={onToggle}
          className={`w-14 h-14 rounded-full items-center justify-center mb-3 ${
            isRecording ? "bg-avatar" : "bg-primary"
          }`}
        >
          {isRecording ? (
            <Square size={20} color="#FFFFFF" />
          ) : (
            <Mic size={20} color="#FFFFFF" />
          )}
        </Pressable>
        <Text className="text-sm font-medium text-text mb-1">
          {isRecording ? "녹음 중..." : hasRecording ? "녹음 완료" : "녹음 시작"}
        </Text>
        {isRecording && (
          <View className="flex-row items-center justify-center gap-1 h-6 my-2">
            {[10, 18, 24, 16, 22, 14, 20].map((h, i) => (
              <WaveBar key={i} height={h} delay={i * 100} />
            ))}
          </View>
        )}
        <Text className="text-lg font-light text-text">
          {formatTime(durationMillis)}
        </Text>
        <Text className="text-xs text-subtext mt-1">
          {isRecording ? "버튼을 눌러 중지하세요" : "버튼을 눌러 녹음을 시작하세요"}
        </Text>
      </View>
    </View>
  );
}
