import React, { useEffect, useRef } from "react";
import { Animated, Text, View } from "react-native";

export function SplashScreen({ onFinish }: { onFinish: () => void }) {
  const logoOpacity = useRef(new Animated.Value(0)).current;
  const logoTranslateY = useRef(new Animated.Value(20)).current;
  const lineScaleX = useRef(new Animated.Value(0)).current;
  const textOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(logoOpacity, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(logoTranslateY, {
        toValue: 0,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(lineScaleX, {
        toValue: 1,
        duration: 600,
        delay: 400,
        useNativeDriver: true,
      }),
      Animated.timing(textOpacity, {
        toValue: 1,
        duration: 500,
        delay: 700,
        useNativeDriver: true,
      }),
    ]).start(() => onFinish());
  }, [logoOpacity, logoTranslateY, lineScaleX, textOpacity, onFinish]);

  return (
    <View className="flex-1 bg-[#232323] items-center justify-center">
      <Animated.Text
        className="text-white text-5xl tracking-tight"
        style={{
          fontFamily: "serif",
          opacity: logoOpacity,
          transform: [{ translateY: logoTranslateY }],
        }}
      >
        Zinmac
      </Animated.Text>
      <Animated.View
        className="w-12 h-0.5 bg-primary mt-5"
        style={{
          transform: [{ scaleX: lineScaleX }],
          transformOrigin: "left",
        }}
      />
      <Animated.Text
        className="text-[#A09892] mt-6 text-xs tracking-widest absolute bottom-16"
        style={{ opacity: textOpacity }}
      >
        AI 한의 진료 보조 시스템
      </Animated.Text>
    </View>
  );
}
