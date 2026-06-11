import { DiagnosisData, DiagnosisDual, DiagnosisResult } from "../types";

export function isDualDiagnosis(
  diagnosis: DiagnosisResult
): diagnosis is DiagnosisDual {
  return "dataset_based" in diagnosis && "claude_based" in diagnosis;
}

export function buildChartStructured(diagnosis: DiagnosisData): string {
  const constitution = diagnosis.sasang_constitution?.type || "-";
  const tkm = diagnosis.tkm_diagnosis?.diagnosis_name || "-";
  const western = diagnosis.western_diagnosis?.name || "-";
  const herb = diagnosis.herbal_prescription;
  const herbName = herb?.name_kr || "-";
  const herbStr = (herb?.composition || [])
    .map((c) => `${c.herb} ${c.dosage}`.trim())
    .filter(Boolean)
    .join(", ");
  const acuStr = (diagnosis.acupuncture_prescription || [])
    .map((p) => `${p.point_kr}(${p.point_code})`)
    .filter(Boolean)
    .join(", ");

  return (
    `▶ 사상체질\n${constitution}\n\n` +
    `▶ 한의학적 진단\n${tkm}\n양방 대응: ${western}\n\n` +
    `▶ 한약 처방\n${herbName}\n${herbStr}\n\n` +
    `▶ 침 처방\n${acuStr}`
  );
}

export function formatResultBlock(diagnosis: DiagnosisData, label: string): string {
  return `■ ${label}\n${buildChartStructured(diagnosis)}`;
}

export function buildCopyText(
  diagnosis: DiagnosisData,
  patientName: string
): string {
  const constitution = diagnosis.sasang_constitution?.type || "-";
  const tkm = diagnosis.tkm_diagnosis?.diagnosis_name || "-";
  const western = diagnosis.western_diagnosis?.name || "-";
  const herb = diagnosis.herbal_prescription;
  const herbName = herb?.name_kr || "-";
  const herbStr = (herb?.composition || [])
    .map((c) => `${c.herb} ${c.dosage}`.trim())
    .filter(Boolean)
    .join(", ");
  const acuStr = (diagnosis.acupuncture_prescription || [])
    .map((p) => `${p.point_kr}(${p.point_code})`)
    .filter(Boolean)
    .join(", ");

  return (
    `[${patientName} 진단 결과]\n\n` +
    `▶ 사상체질\n${constitution}\n\n` +
    `▶ 한의학적 진단\n${tkm}\n양방 대응: ${western}\n\n` +
    `▶ 한약 처방\n${herbName}\n${herbStr}\n\n` +
    `▶ 침 처방\n${acuStr}\n\n` +
    `※ AI 참고용 / 최종 판단은 담당 한의사`
  );
}

export function parseChartSections(
  text: string | null | undefined
): Record<string, string> | null {
  if (!text) return null;
  const sections: Record<string, string> = {};
  const parts = text.split(/▶\s+/);
  for (const part of parts) {
    const lines = part.trim().split("\n");
    const title = lines[0]?.trim();
    const joined = lines.slice(1).join("\n");
    const content = (
      joined.includes("※") ? joined.slice(0, joined.indexOf("※")) : joined
    ).trim();
    if (title) sections[title] = content;
  }
  return Object.keys(sections).length > 0 ? sections : null;
}

export function formatPatientSubtext(patient: {
  gender?: string;
  birth_date?: string;
  phone?: string;
}): string {
  const genderMap: Record<string, string> = {
    male: "남",
    female: "여",
    M: "남",
    F: "여",
    남성: "남",
    여성: "여",
  };
  const gender = patient.gender ? genderMap[patient.gender] ?? patient.gender : "";
  let birth: string | null = null;
  let age: string | null = null;
  if (patient.birth_date) {
    birth = patient.birth_date;
    const today = new Date();
    const b = new Date(patient.birth_date);
    let a = today.getFullYear() - b.getFullYear();
    if (
      today <
      new Date(today.getFullYear(), b.getMonth(), b.getDate())
    ) {
      a--;
    }
    age = `만 ${a}세`;
  }
  const parts = [gender, birth && age ? `${birth} (${age})` : birth].filter(
    Boolean
  );
  return parts.join(", ") || patient.phone || "-";
}
