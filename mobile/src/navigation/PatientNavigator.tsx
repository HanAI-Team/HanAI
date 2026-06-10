import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { PatientStackParamList } from "./types";
import { PatientListScreen } from "../screens/patients/PatientListScreen";
import { PatientDetailScreen } from "../screens/patients/PatientDetailScreen";
import { AddPatientScreen } from "../screens/patients/AddPatientScreen";
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
        options={({ route }) => ({ title: route.params.patient.name })}
      />
      <Stack.Screen
        name="AddPatient"
        component={AddPatientScreen}
        options={{ title: "신규 환자 등록" }}
      />
    </Stack.Navigator>
  );
}
