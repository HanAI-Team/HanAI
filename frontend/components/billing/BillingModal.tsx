"use client";
import { QueueItem } from "@/lib/api/queue";
import { X } from "lucide-react";

interface BillingModalProps {
  queueItem: QueueItem;
  onClose: () => void;
  onComplete: (updated: QueueItem) => void;
}

// TODO(Phase 3): 진단 검색 + 빠른입력 그리드 + 처방/시술 표 + 저장 및 청구.
// 지금은 접수 카드 클릭 → 모달 오픈 흐름만 연결된 뼈대(Phase 2).
export default function BillingModal({ queueItem, onClose }: BillingModalProps) {
  return (
    <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl w-full max-w-2xl shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="text-sm font-medium text-text">{queueItem.patient_name} — 청구</div>
          <button onClick={onClose} className="text-subtext hover:text-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-8 text-center text-sm text-muted">
          청구 모달 구현 예정 (Phase 3)
        </div>
      </div>
    </div>
  );
}
