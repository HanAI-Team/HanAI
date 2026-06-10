import { NavigatorScreenParams } from "@react-navigation/native";
import { DiagnosisResult, Patient } from "../types";

export type AuthStackParamList = {
  Login: undefined;
  StaffLogin: undefined;
};

export type DiagnosisStackParamList = {
  PatientSelect: undefined;
  Diagnosis: { patient: Patient };
  Result: {
    patient: Patient;
    recordId: string;
    diagnosis: DiagnosisResult;
    rawTranscription?: string;
    medicalHistory?: string;
  };
  History: { patient: Patient };
};

export type PatientStackParamList = {
  PatientList: undefined;
  PatientDetail: { patient: Patient };
  AddPatient: undefined;
  History: { patient: Patient };
};

export type SettingsStackParamList = {
  Settings: undefined;
};

export type MainTabParamList = {
  DiagnosisTab: NavigatorScreenParams<DiagnosisStackParamList>;
  PatientTab: NavigatorScreenParams<PatientStackParamList>;
  SettingsTab: NavigatorScreenParams<SettingsStackParamList>;
};

export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
