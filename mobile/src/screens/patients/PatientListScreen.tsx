import React, { useState } from "react";
import { FlatList, RefreshControl, TextInput, View } from "react-native";
import { Search } from "lucide-react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { PatientStackParamList } from "../../navigation/types";
import { usePatients } from "../../hooks/usePatients";
import { PatientListItem } from "../../components/PatientListItem";
import { EmptyState } from "../../components/EmptyState";
import { LoadingIndicator } from "../../components/LoadingIndicator";
import { Button } from "../../components/Button";
import { Patient } from "../../types";

type Props = NativeStackScreenProps<PatientStackParamList, "PatientList">;

export function PatientListScreen({ navigation }: Props) {
  const [search, setSearch] = useState("");
  const {
    data,
    isLoading,
    isRefetching,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePatients(search);

  const patients: Patient[] = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <View className="flex-1 bg-background">
      <View className="bg-white border-b border-border px-4 pt-4 pb-3">
        <View className="flex-row items-center gap-2 bg-background border border-border rounded-md px-3 py-2.5">
          <Search size={14} color="#B0AAA4" />
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="이름 검색..."
            placeholderTextColor="#B0AAA4"
            className="flex-1 text-xs text-text"
          />
        </View>
      </View>

      {isLoading ? (
        <LoadingIndicator />
      ) : (
        <FlatList
          data={patients}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <PatientListItem
              patient={item}
              onPress={() => navigation.navigate("PatientDetail", { patient: item })}
            />
          )}
          refreshControl={
            <RefreshControl refreshing={isRefetching} onRefresh={refetch} />
          }
          onEndReached={() => {
            if (hasNextPage && !isFetchingNextPage) fetchNextPage();
          }}
          onEndReachedThreshold={0.4}
          ListEmptyComponent={
            <EmptyState
              message={search ? "검색 결과가 없습니다" : "등록된 환자가 없습니다"}
            />
          }
          ListFooterComponent={isFetchingNextPage ? <LoadingIndicator /> : null}
        />
      )}

      <View className="p-4 bg-white border-t border-border">
        <Button
          label="+ 신규 환자 등록"
          onPress={() => navigation.navigate("AddPatient")}
        />
      </View>
    </View>
  );
}
