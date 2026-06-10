import React from "react";
import { Modal, Text, View } from "react-native";
import { Button } from "./Button";

interface ConfirmModalProps {
  visible: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel?: () => void;
}

export function ConfirmModal({
  visible,
  title,
  message,
  confirmLabel = "확인",
  cancelLabel,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View className="flex-1 bg-black/50 items-center justify-center px-6">
        <View className="bg-white rounded-xl w-full max-w-sm p-6">
          {title && (
            <Text className="text-sm font-medium text-text mb-2 text-center">
              {title}
            </Text>
          )}
          <Text className="text-sm text-text mb-5 text-center">{message}</Text>
          <View className="flex-row gap-2">
            {cancelLabel && onCancel && (
              <View className="flex-1">
                <Button label={cancelLabel} variant="outline" onPress={onCancel} />
              </View>
            )}
            <View className="flex-1">
              <Button label={confirmLabel} onPress={onConfirm} />
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}
