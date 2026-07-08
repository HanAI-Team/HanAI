import { useEffect, useRef } from "react";
import { Animated, useColorScheme, View } from "react-native";

const LOGO_SIZE = 96;

// 로고를 이루는 7개 막대의 x좌표 구간 (원본 500x500 PNG 기준)
// 순서: 왼쪽 짧은 막대 → 왼쪽 긴 막대 → M 왼쪽 → M 가운데 → M 오른쪽 → 오른쪽 긴 막대 → 오른쪽 짧은 막대
const BAR_RANGES: [number, number][] = [
  [75, 104],
  [131, 166],
  [191, 230],
  [230, 269],
  [269, 308],
  [333, 368],
  [394, 423],
];

export function SplashScreen({ onFinish }: { onFinish: () => void }) {
  const isDark = useColorScheme() === "dark";
  const logoSource = isDark
    ? require("../../../assets/logo-dark.png")
    : require("../../../assets/logo-light.png");

  const barValues = useRef(BAR_RANGES.map(() => new Animated.Value(0))).current;
  const textOpacity = useRef(new Animated.Value(0)).current;
  const containerOpacity = useRef(new Animated.Value(1)).current;

  const textColor = isDark ? "#7FFFD4" : "#FF9500";

  useEffect(() => {
    Animated.sequence([
      Animated.stagger(
        100,
        barValues.map((v) =>
          Animated.timing(v, {
            toValue: 1,
            duration: 400,
            useNativeDriver: true,
          }),
        ),
      ),
      Animated.timing(textOpacity, {
        toValue: 1,
        duration: 400,
        useNativeDriver: true,
      }),
      Animated.delay(100),
      Animated.timing(containerOpacity, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start(() => onFinish());
  }, [barValues, textOpacity, containerOpacity, onFinish]);

  return (
    <Animated.View
      style={{
        flex: 1,
        backgroundColor: "#232323",
        alignItems: "center",
        justifyContent: "center",
        opacity: containerOpacity,
      }}
    >
      <View style={{ width: LOGO_SIZE, height: LOGO_SIZE }}>
        {BAR_RANGES.map(([x0, x1], i) => {
          const left = (x0 / 500) * LOGO_SIZE;
          const width = ((x1 - x0) / 500) * LOGO_SIZE;
          const translateY = barValues[i].interpolate({
            inputRange: [0, 1],
            outputRange: [24, 0],
          });
          return (
            <View
              key={i}
              style={{
                position: "absolute",
                left,
                width,
                top: 0,
                height: LOGO_SIZE,
                overflow: "hidden",
              }}
            >
              <Animated.Image
                source={logoSource}
                resizeMode="contain"
                style={{
                  position: "absolute",
                  left: -left,
                  width: LOGO_SIZE,
                  height: LOGO_SIZE,
                  opacity: barValues[i],
                  transform: [{ translateY }],
                }}
              />
            </View>
          );
        })}
      </View>
      <Animated.Text
        className="text-5xl tracking-tight mt-5"
        style={{
          
          color: textColor,
          opacity: textOpacity,
        }}
      >
        Zinmac
      </Animated.Text>
      <Animated.Text
        className="text-[#A09892] mt-6 text-xs tracking-widest absolute bottom-16"
        style={{ opacity: textOpacity }}
      >
        AI 한의 진료 보조 시스템
      </Animated.Text>
    </Animated.View>
  );
}
