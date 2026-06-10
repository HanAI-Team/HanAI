import React from "react";
import { Pressable, Text } from "react-native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { PatientStackParamList } from "./types";
import { PatientListScreen } from "../screens/patients/PatientListScreen";
import { PatientDetailScreen } from "../screens/patients/PatientDetailScreen";
import { AddPatientScreen } from "../screens/patients/AddPatientScreen";
import { HistoryScreen } from "../screens/diagnosis/HistoryScreen";
import { headerStyle } from "./headerStyle";

const Stack = createNativeStackNavigator<PatientStackParamList>();

export function PatientNavigator() {
  return (
    <Stack.Navigator screenOptions={headerStyle}>
      <Stack.Screen
        name="PatientList"
        component={PatientListScreen}
        options={{ title: "환자 목록" }}
      />
      <Stack.Screen
        name="PatientDetail"
        component={PatientDetailScreen}
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
        name="AddPatient"
        component={AddPatientScreen}
        options={{ title: "신규 환자 등록" }}
      />
      <Stack.Screen
        name="History"
        component={HistoryScreen}
        options={{ title: "진료 이력" }}
      />
    </Stack.Navigator>
  );
}
