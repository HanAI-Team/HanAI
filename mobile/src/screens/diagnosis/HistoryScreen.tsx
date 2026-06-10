import React, { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { ChevronDown, ChevronUp, User, Stethoscope, Leaf, MapPin, FileText, Clipboard } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { DiagnosisStackParamList } from "../../navigation/types";
import { getPatientRecords } from "../../api/patients";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { LoadingIndicator } from "../../components/LoadingIndicator";
import { parseChartSections } from "../../utils/chart";

type Props = NativeStackScreenProps<DiagnosisStackParamList, "History">;

const SECTIONS = [
  { key: "사상체질", Icon: User },
  { key: "한의학적 진단", Icon: Stethoscope },
  { key: "한약 처방", Icon: Leaf },
  { key: "침 처방", Icon: MapPin },
];

export function HistoryScreen({ route }: Props) {
  const { patient } = route.params;
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["patientRecords", patient.id],
    queryFn: () => getPatientRecords(patient.id),
  });

  if (isLoading) return <LoadingIndicator />;

  const records = (data?.records ?? [])
    .slice()
    .sort((a, b) => {
      const da = a.recorded_at ? new Date(a.recorded_at).getTime() : 0;
      const db = b.recorded_at ? new Date(b.recorded_at).getTime() : 0;
      return db - da;
    });

  if (records.length === 0) {
    return (
      <View className="flex-1 bg-background">
        <EmptyState message="진료 이력이 없습니다" />
      </View>
    );
  }

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, gap: 8 }}>
      {records.map((record) => {
        const sections = parseChartSections(record.chart_structured);
        const isOpen = expandedId === record.id;
        return (
          <Card key={record.id} className="p-0 overflow-hidden">
            <Pressable
              onPress={() => setExpandedId(isOpen ? null : record.id)}
              className="flex-row items-center justify-between px-4 py-3"
            >
              <Text className="text-sm text-text">
                {record.recorded_at
                  ? new Date(record.recorded_at).toLocaleString("ko-KR")
                  : "-"}
              </Text>
              {isOpen ? (
                <ChevronUp size={16} color="#B0AAA4" />
              ) : (
                <ChevronDown size={16} color="#B0AAA4" />
              )}
            </Pressable>
            {isOpen && (
              <View className="border-t border-border px-4 py-3 gap-3">
                {sections ? (
                  SECTIONS.map(({ key, Icon }) => (
                    <View key={key}>
                      <View className="flex-row items-center gap-1.5 mb-1">
                        <Icon size={12} color="#8A8480" />
                        <Text className="text-xs text-subtext uppercase tracking-wide">
                          {key}
                        </Text>
                      </View>
                      <Text className="text-sm text-text">
                        {sections[key] || "-"}
                      </Text>
                    </View>
                  ))
                ) : (
                  <Text className="text-sm text-text">
                    {record.raw_transcription || "-"}
                  </Text>
                )}
                {record.medical_history && (
                  <View>
                    <View className="flex-row items-center gap-1.5 mb-1">
                      <Clipboard size={12} color="#8A8480" />
                      <Text className="text-xs text-subtext uppercase tracking-wide">병력</Text>
                    </View>
                    <Text className="text-sm text-text">{record.medical_history}</Text>
                  </View>
                )}
                {record.raw_transcription && (
                  <View>
                    <View className="flex-row items-center gap-1.5 mb-1">
                      <FileText size={12} color="#8A8480" />
                      <Text className="text-xs text-subtext uppercase tracking-wide">원본 텍스트</Text>
                    </View>
                    <Text className="text-xs text-subtext">{record.raw_transcription}</Text>
                  </View>
                )}
              </View>
            )}
          </Card>
        );
      })}
    </ScrollView>
  );
}
