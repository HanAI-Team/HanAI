import React, { useState } from "react";
import { Alert, ScrollView, Text, TextInput, View, Pressable } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { FolderOpen } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { DiagnosisStackParamList } from "../../navigation/types";
import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import { RecordingCard } from "../../components/RecordingCard";
import { useVoiceRecorder } from "../../hooks/useVoiceRecorder";
import { uploadAndAnalyze, updateMedicalHistory, AudioFile } from "../../api/charting";
import { diagnoseText } from "../../api/diagnosis";
import { getErrorMessage } from "../../api/client";
import { ChartingResponse, DiagnosisTextResponse } from "../../types";

type Props = NativeStackScreenProps<DiagnosisStackParamList, "Diagnosis">;

export function DiagnosisScreen({ route, navigation }: Props) {
  const { patient } = route.params;
  const [audioFile, setAudioFile] = useState<AudioFile | null>(null);
  const [symptomText, setSymptomText] = useState("");
  const [hasHistory, setHasHistory] = useState(false);
  const [historyText, setHistoryText] = useState("");

  const recorder = useVoiceRecorder();

  const handleToggleRecording = async () => {
    if (recorder.isRecording) {
      const file = await recorder.stop();
      if (file) setAudioFile(file);
    } else {
      setAudioFile(null);
      await recorder.start();
    }
  };

  const handlePickFile = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ["audio/*"],
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    setAudioFile({
      uri: asset.uri,
      name: asset.name,
      type: asset.mimeType || "audio/mpeg",
    });
  };

  const analysisMutation = useMutation({
    mutationFn: async () => {
      const medicalHistory = hasHistory ? historyText.trim() : "";
      if (audioFile) {
        const data: ChartingResponse = await uploadAndAnalyze(
          patient.id,
          audioFile
        );
        if (medicalHistory) {
          await updateMedicalHistory(data.record_id, medicalHistory);
        }
        return {
          recordId: data.record_id,
          diagnosis: data.diagnosis,
          rawTranscription: data.transcription,
          medicalHistory,
        };
      }
      const data: DiagnosisTextResponse = await diagnoseText(symptomText.trim());
      return {
        recordId: "",
        diagnosis: data.result,
        rawTranscription: symptomText.trim(),
        medicalHistory,
      };
    },
    onSuccess: (data) => {
      navigation.navigate("Result", { patient, ...data });
    },
    onError: (error) => {
      Alert.alert("분석 실패", getErrorMessage(error, "AI 분석에 실패했습니다"));
    },
  });

  const canAnalyze = !!audioFile || symptomText.trim().length > 0;

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 16 }}>
      <RecordingCard
        isRecording={recorder.isRecording}
        hasRecording={!!audioFile && !recorder.isRecording}
        durationMillis={recorder.durationMillis}
        onToggle={handleToggleRecording}
      />

      <Card>
        <Text className="text-xs text-subtext uppercase tracking-wide mb-3">
          파일 업로드
        </Text>
        <Pressable
          onPress={handlePickFile}
          className="border border-dashed border-borderStrong rounded-lg p-5 items-center bg-background"
        >
          <FolderOpen size={28} color="#B0AAA4" />
          <Text className="text-xs text-subtext mt-2 text-center">
            {audioFile && !recorder.isRecording
              ? audioFile.name
              : "탭하여 파일 선택"}
          </Text>
          <Text className="text-xs text-muted mt-1">mp3, wav, m4a · 최대 100MB</Text>
        </Pressable>
      </Card>

      <Card>
        <Text className="text-xs text-subtext uppercase tracking-wide mb-3">
          증상 직접 입력{" "}
          <Text className="text-muted">(음성 없이 텍스트로 분석)</Text>
        </Text>
        <TextInput
          value={symptomText}
          onChangeText={setSymptomText}
          placeholder="증상을 자세히 입력하세요"
          placeholderTextColor="#B0AAA4"
          multiline
          numberOfLines={4}
          editable={!audioFile}
          className="bg-background border border-border rounded-md p-3 text-xs text-text min-h-[90px]"
          style={{ textAlignVertical: "top" }}
        />
        {audioFile && (
          <Text className="text-xs text-muted mt-1">
            음성 파일이 있으면 텍스트 입력은 무시됩니다.
          </Text>
        )}
      </Card>

      <Card>
        <Text className="text-xs text-subtext uppercase tracking-wide mb-3">병력</Text>
        <View className="flex-row gap-6 mb-2">
          {[
            { label: "없음", value: false },
            { label: "있음", value: true },
          ].map((opt) => (
            <Pressable
              key={opt.label}
              onPress={() => setHasHistory(opt.value)}
              className="flex-row items-center gap-1.5"
            >
              <View
                className={`w-4 h-4 rounded-full border items-center justify-center ${
                  hasHistory === opt.value ? "border-primary" : "border-borderStrong"
                }`}
              >
                {hasHistory === opt.value && (
                  <View className="w-2 h-2 rounded-full bg-primary" />
                )}
              </View>
              <Text className="text-sm text-text">{opt.label}</Text>
            </Pressable>
          ))}
        </View>
        {hasHistory && (
          <TextInput
            value={historyText}
            onChangeText={setHistoryText}
            placeholder="병력을 입력하세요"
            placeholderTextColor="#B0AAA4"
            multiline
            numberOfLines={3}
            className="bg-background border border-border rounded-md p-3 text-xs text-text min-h-[70px]"
            style={{ textAlignVertical: "top" }}
          />
        )}
      </Card>

      <Button
        label="AI 진단 분석 시작"
        onPress={() => analysisMutation.mutate()}
        loading={analysisMutation.isPending}
        disabled={!canAnalyze}
      />
    </ScrollView>
  );
}
