import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SettingsStackParamList } from "./types";
import { SettingsScreen } from "../screens/settings/SettingsScreen";
import { headerStyle } from "./headerStyle";

const Stack = createNativeStackNavigator<SettingsStackParamList>();

export function SettingsNavigator() {
  return (
    <Stack.Navigator screenOptions={headerStyle}>
      <Stack.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ title: "설정" }}
      />
    </Stack.Navigator>
  );
}
