import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Stethoscope, Users, Settings } from "lucide-react-native";
import { MainTabParamList } from "./types";
import { DiagnosisNavigator } from "./DiagnosisNavigator";
import { PatientNavigator } from "./PatientNavigator";
import { SettingsNavigator } from "./SettingsNavigator";

const Tab = createBottomTabNavigator<MainTabParamList>();

export function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#EF6600",
        tabBarInactiveTintColor: "#8A8480",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#D4CCC4",
        },
      }}
    >
      <Tab.Screen
        name="DiagnosisTab"
        component={DiagnosisNavigator}
        options={{
          title: "진료",
          tabBarIcon: ({ color, size }) => (
            <Stethoscope color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="PatientTab"
        component={PatientNavigator}
        options={{
          title: "환자",
          tabBarIcon: ({ color, size }) => <Users color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="SettingsTab"
        component={SettingsNavigator}
        options={{
          title: "설정",
          tabBarIcon: ({ color, size }) => (
            <Settings color={color} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}
