"use client";
import { useState } from "react";
import { ShieldCheck, X } from "lucide-react";
import type { Patient } from "@/types";

interface InsuranceEligibilityModalProps {
  patient: Patient;
  onClose: () => void;
}

export default function InsuranceEligibilityModal({ patient, onClose }: InsuranceEligibilityModalProps) {
  const [checking, setChecking] = useState(false);
  const [checked, setChecked] = useState(false);

  function handleCheck() {
    setChecking(true);
    setTimeout(() => {
      setChecking(false);
      setChecked(true);
    }, 600);
  }

  return (
    <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="text-sm font-medium text-text">건강보험 자격조회</div>
          <button onClick={onClose} className="text-subtext hover:text-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 flex flex-col gap-4">
          <div>
            <div className="text-xs text-subtext mb-1">환자</div>
            <div className="text-sm text-text">{patient.name}</div>
          </div>
          {!checked ? (
            <button
              onClick={handleCheck}
              disabled={checking}
              className="w-full flex items-center justify-center gap-1.5 bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-60"
            >
              <ShieldCheck className="w-4 h-4" />
              {checking ? "조회 중..." : "자격조회"}
            </button>
          ) : (
            <div className="rounded-md border border-dashed border-border bg-fill p-4 text-center">
              <div className="text-sm text-text font-medium mb-1">연동 준비 중입니다</div>
              <div className="text-xs text-subtext leading-relaxed">
                요양기관업무포털 EDI 자격조회 연동 규격서를 확보하는 대로
                <br />
                실제 자격 조회 결과가 여기에 표시됩니다.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
