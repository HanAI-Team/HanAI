import React, { useState } from "react";
import { Alert, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import * as Clipboard from "expo-clipboard";
import {
  User,
  Stethoscope,
  Leaf,
  MapPin,
  FileText,
  CircleCheck,
} from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { DiagnosisStackParamList } from "../../navigation/types";
import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import { Tag } from "../../components/Tag";
import { saveRecord } from "../../api/patients";
import { finalizeRecord } from "../../api/charting";
import { submitFeedback } from "../../api/feedback";
import { getErrorMessage } from "../../api/client";
import { buildCopyText, formatResultBlock, isDualDiagnosis } from "../../utils/chart";

type Props = NativeStackScreenProps<DiagnosisStackParamList, "Result">;

const TABS = [
  { key: "dataset_based" as const, label: "데이터셋 기반" },
  { key: "claude_based" as const, label: "AI 종합 소견" },
];

export function ResultScreen({ route }: Props) {
  const { patient, recordId, diagnosis, rawTranscription, medicalHistory } = route.params;

  const isDual = isDualDiagnosis(diagnosis);
  const [activeTab, setActiveTab] = useState<"dataset_based" | "claude_based">(
    "dataset_based"
  );
  const result = isDual ? diagnosis[activeTab] : diagnosis;

  const [saved, setSaved] = useState(false);
  const [savedRecordId, setSavedRecordId] = useState(recordId || "");
  const [saveSelection, setSaveSelection] = useState<"both" | "result1" | "result2">("both");
  const [feedbackHelpful, setFeedbackHelpful] = useState<boolean | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      setSaved(false);
      setSavedRecordId(recordId || "");
      setSaveSelection("both");
      setFeedbackHelpful(null);
      setFeedbackComment("");
      setFeedbackSubmitted(false);
    }, [recordId])
  );

  const saveMutation = useMutation({
    mutationFn: () => {
      const chartStructured = isDual
        ? saveSelection === "result1"
          ? formatResultBlock(diagnosis.dataset_based, "결과 1")
          : saveSelection === "result2"
            ? formatResultBlock(diagnosis.claude_based, "결과 2")
            : `${formatResultBlock(diagnosis.dataset_based, "결과 1")}\n\n${formatResultBlock(diagnosis.claude_based, "결과 2")}`
        : formatResultBlock(diagnosis, "진단 결과");

      return recordId
        ? finalizeRecord(recordId, chartStructured, saveSelection)
        : saveRecord(patient.id, chartStructured, rawTranscription, medicalHistory, saveSelection);
    },
    onSuccess: (data) => {
      setSaved(true);
      setSavedRecordId(data.id);
      Alert.alert("저장 완료", "진료 기록이 저장되었습니다.");
    },
    onError: (error) => {
      Alert.alert("저장 실패", getErrorMessage(error, "저장에 실패했습니다"));
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: () =>
      submitFeedback({
        medical_record_id: savedRecordId,
        is_helpful: feedbackHelpful as boolean,
        comment: feedbackComment.trim() || undefined,
      }),
    onSuccess: () => setFeedbackSubmitted(true),
    onError: (error) => {
      Alert.alert("전송 실패", getErrorMessage(error, "피드백 전송에 실패했습니다"));
    },
  });

  const handleCopyAll = async () => {
    await Clipboard.setStringAsync(buildCopyText(result, patient.name));
    Alert.alert("복사 완료", "진단 결과가 클립보드에 복사되었습니다.");
  };

  const cards = [
    {
      label: "사상체질",
      Icon: User,
      value: result.sasang_constitution?.type || "-",
    },
    {
      label: "한의학적 진단",
      Icon: Stethoscope,
      value: result.tkm_diagnosis?.diagnosis_name || "-",
      sub: `양방: ${result.western_diagnosis?.name || "-"}`,
    },
    {
      label: "한약 처방",
      Icon: Leaf,
      value: result.herbal_prescription?.name_kr || "-",
      tags: (result.herbal_prescription?.composition || []).map(
        (c) => `${c.herb} ${c.dosage}`
      ),
    },
    {
      label: "침 처방",
      Icon: MapPin,
      value: (result.acupuncture_prescription || [])
        .map((p) => `${p.point_kr}(${p.point_code})`)
        .join(" · ") || "-",
    },
  ];

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 12 }}>
      {rawTranscription && (
        <Card>
          <View className="flex-row items-center gap-1.5 mb-2">
            <FileText size={14} color="#8A8480" />
            <Text className="text-xs text-subtext uppercase tracking-wide">주소증</Text>
          </View>
          <Text className="text-sm text-text">{rawTranscription}</Text>
        </Card>
      )}

      {isDual && (
        <View className="flex-row gap-2">
          {TABS.map(({ key, label }) => (
            <View key={key} className="flex-1">
              <Button
                label={label}
                variant={activeTab === key ? "primary" : "outline"}
                onPress={() => setActiveTab(key)}
              />
            </View>
          ))}
        </View>
      )}

      {cards.map(({ label, Icon, value, sub, tags }) => (
        <Card key={label}>
          <View className="flex-row items-center gap-1.5 mb-2">
            <Icon size={14} color="#8A8480" />
            <Text className="text-xs text-subtext uppercase tracking-wide">
              {label}
            </Text>
          </View>
          <Text className={`text-sm font-semibold ${tags ? "text-primary" : "text-text"}`}>
            {value}
          </Text>
          {sub && <Text className="text-xs text-subtext mt-1">{sub}</Text>}
          {tags && (
            <View className="flex-row flex-wrap mt-2">
              {tags.map((t, i) => (
                <Tag key={i} label={t} />
              ))}
            </View>
          )}
        </Card>
      ))}

      {isDual && !saved && (
        <Card>
          <Text className="text-xs text-subtext uppercase tracking-wide mb-2">
            저장할 결과 선택
          </Text>
          <View className="gap-2">
            {(
              [
                { value: "both", label: "결과 1 + 결과 2 모두 저장" },
                { value: "result1", label: "결과 1만 저장" },
                { value: "result2", label: "결과 2만 저장" },
              ] as const
            ).map((opt) => (
              <Pressable
                key={opt.value}
                onPress={() => setSaveSelection(opt.value)}
                className="flex-row items-center gap-1.5"
              >
                <View
                  className={`w-4 h-4 rounded-full border items-center justify-center ${
                    saveSelection === opt.value ? "border-primary" : "border-borderStrong"
                  }`}
                >
                  {saveSelection === opt.value && (
                    <View className="w-2 h-2 rounded-full bg-primary" />
                  )}
                </View>
                <Text className="text-sm text-text">{opt.label}</Text>
              </Pressable>
            ))}
          </View>
        </Card>
      )}

      <View className="flex-row gap-2">
        <View className="flex-1">
          <Button
            label="전체 복사"
            variant="outline"
            onPress={handleCopyAll}
          />
        </View>
        <View className="flex-1">
          <Button
            label={saved ? "저장됨" : "저장"}
            onPress={() => saveMutation.mutate()}
            loading={saveMutation.isPending}
            disabled={saved}
          />
        </View>
      </View>

      {saved && (
        <Card>
          {feedbackSubmitted ? (
            <View className="flex-row items-center justify-center gap-2 py-1">
              <CircleCheck size={16} color="#EF6600" />
              <Text className="text-sm text-subtext">피드백 감사합니다</Text>
            </View>
          ) : (
            <>
              <Text className="text-xs text-subtext mb-3 text-center">
                이 진단이 도움이 됐나요?
              </Text>
              <View className="flex-row gap-2 justify-center mb-3">
                <Button
                  label="👍 도움됨"
                  variant={feedbackHelpful === true ? "primary" : "outline"}
                  onPress={() => setFeedbackHelpful(true)}
                  className="flex-1"
                />
                <Button
                  label="👎 도움 안 됨"
                  variant={feedbackHelpful === false ? "danger" : "outline"}
                  onPress={() => setFeedbackHelpful(false)}
                  className="flex-1"
                />
              </View>
              {feedbackHelpful !== null && (
                <>
                  <TextInput
                    value={feedbackComment}
                    onChangeText={setFeedbackComment}
                    placeholder="추가 의견이 있으시면 입력해주세요 (선택)"
                    placeholderTextColor="#B0AAA4"
                    multiline
                    numberOfLines={2}
                    className="bg-background border border-border rounded-md px-3 py-2 text-xs text-text mb-2 min-h-[60px]"
                    style={{ textAlignVertical: "top" }}
                  />
                  <Button
                    label="피드백 제출"
                    onPress={() => feedbackMutation.mutate()}
                    loading={feedbackMutation.isPending}
                  />
                </>
              )}
            </>
          )}
        </Card>
      )}
    </ScrollView>
  );
}
