import React from "react";
import { Pressable, Text } from "react-native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { DiagnosisStackParamList } from "./types";
import { PatientSelectScreen } from "../screens/diagnosis/PatientSelectScreen";
import { DiagnosisScreen } from "../screens/diagnosis/DiagnosisScreen";
import { ResultScreen } from "../screens/diagnosis/ResultScreen";
import { HistoryScreen } from "../screens/diagnosis/HistoryScreen";
import { headerStyle } from "./headerStyle";

const Stack = createNativeStackNavigator<DiagnosisStackParamList>();

export function DiagnosisNavigator() {
  return (
    <Stack.Navigator screenOptions={headerStyle}>
      <Stack.Screen
        name="PatientSelect"
        component={PatientSelectScreen}
        options={{ title: "환자 선택" }}
      />
      <Stack.Screen
        name="Diagnosis"
        component={DiagnosisScreen}
        options={({ route, navigation }) => ({
          title: route.params.patient.name,
          headerRight: () => (
            <Pressable
              onPress={() =>
                navigation.navigate("History", { patient: route.params.patient })
              }
            >
              <Text className="text-primary text-sm">진료 이력</Text>
            </Pressable>
          ),
        })}
      />
      <Stack.Screen
        name="Result"
        component={ResultScreen}
        options={{ title: "진단 결과" }}
      />
      <Stack.Screen
        name="History"
        component={HistoryScreen}
        options={{ title: "진료 이력" }}
      />
    </Stack.Navigator>
  );
}
