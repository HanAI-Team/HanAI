"use client";

import { useEffect, useState } from "react";
import {
  createPrescription,
  getPrescriptions,
  type PrescriptionInput as PrescriptionInputData,
  type PrescriptionRecord,
  type PrescriptionType,
} from "@/lib/api/diagnosis";

interface PrescriptionInputProps {
  medicalRecordId: string;
  patientBirthDate?: string | null;
}

const PRESCRIPTION_TYPES: PrescriptionType[] = ["기준처방", "가감처방", "가미제", "임의처방"];

const emptyForm = {
  prescription_name: "",
  prescription_type: "기준처방" as PrescriptionType,
  formula_code: "",
  adjustment_type: "",
  ingredients: "",
  dosage: "",
  species_count: "",
  total_weight_g: "",
  unit_price: "",
  daily_dosage_ratio: "1.0",
  total_dosage_days: "",
  low_cost_substitute: false,
  low_cost_surcharge: "",
  dispensing_fee: "",
  notes: "",
};

export default function PrescriptionInput({
  medicalRecordId,
  patientBirthDate,
}: PrescriptionInputProps) {
  const [prescriptions, setPrescriptions] = useState<PrescriptionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getPrescriptions(medicalRecordId)
      .then(setPrescriptions)
      .catch(() => setPrescriptions([]))
      .finally(() => setLoading(false));
  }, [medicalRecordId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.prescription_name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: PrescriptionInputData = {
        prescription_name: form.prescription_name.trim(),
        prescription_type: form.prescription_type,
        formula_code: form.formula_code.trim() || undefined,
        adjustment_type: form.adjustment_type.trim() || undefined,
        ingredients: form.ingredients.trim() || undefined,
        dosage: form.dosage.trim() || undefined,
        species_count: form.species_count ? Number(form.species_count) : undefined,
        total_weight_g: form.total_weight_g ? Number(form.total_weight_g) : undefined,
        unit_price: form.unit_price ? Number(form.unit_price) : undefined,
        daily_dosage_ratio: form.daily_dosage_ratio ? Number(form.daily_dosage_ratio) : undefined,
        total_dosage_days: form.total_dosage_days ? Number(form.total_dosage_days) : undefined,
        low_cost_substitute: form.low_cost_substitute,
        low_cost_surcharge: form.low_cost_surcharge ? Number(form.low_cost_surcharge) : undefined,
        dispensing_fee: form.dispensing_fee ? Number(form.dispensing_fee) : undefined,
        notes: form.notes.trim() || undefined,
        patient_birth_date: patientBirthDate || undefined,
      };
      const created = await createPrescription(medicalRecordId, payload);
      setPrescriptions((prev) => [...prev, created]);
      setForm(emptyForm);
    } catch (e) {
      setError(e instanceof Error ? e.message : "처방 등록에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h3 className="text-sm font-medium text-text mb-3">한약 처방 입력</h3>

      {loading ? (
        <div className="text-xs text-subtext py-2">불러오는 중...</div>
      ) : prescriptions.length > 0 ? (
        <ul className="divide-y divide-border border border-border rounded-md mb-4">
          {prescriptions.map((p) => (
            <li key={p.id} className="p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium text-text">
                  {p.prescription_name} <span className="text-subtext">({p.prescription_type})</span>
                </span>
                <span className="text-text">{(p.total_dosage_price ?? 0).toLocaleString()}원</span>
              </div>
              <div className="text-subtext mt-1">
                {p.species_count ? `${p.species_count}종 · ` : ""}
                {p.total_weight_g ? `${p.total_weight_g}g · ` : ""}
                {p.total_dosage_days ? `${p.total_dosage_days}일분` : ""}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              처방명 *
            </label>
            <input
              value={form.prescription_name}
              onChange={(e) => setForm((f) => ({ ...f, prescription_name: e.target.value }))}
              required
              placeholder="예: 통비탕"
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              처방구분
            </label>
            <select
              value={form.prescription_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, prescription_type: e.target.value as PrescriptionType }))
              }
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            >
              {PRESCRIPTION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              처방코드
            </label>
            <input
              value={form.formula_code}
              onChange={(e) => setForm((f) => ({ ...f, formula_code: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              가감등구분
            </label>
            <input
              value={form.adjustment_type}
              onChange={(e) => setForm((f) => ({ ...f, adjustment_type: e.target.value }))}
              placeholder="B/A/S"
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
            약재 구성
          </label>
          <textarea
            value={form.ingredients}
            onChange={(e) => setForm((f) => ({ ...f, ingredients: e.target.value }))}
            rows={2}
            placeholder="황기 12g, 당귀 10g, ..."
            className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] resize-none bg-card"
          />
        </div>

        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              종수
            </label>
            <input
              type="number"
              min={0}
              value={form.species_count}
              onChange={(e) => setForm((f) => ({ ...f, species_count: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              총중량(g)
            </label>
            <input
              type="number"
              min={0}
              step="0.1"
              value={form.total_weight_g}
              onChange={(e) => setForm((f) => ({ ...f, total_weight_g: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              단가(원)
            </label>
            <input
              type="number"
              min={0}
              value={form.unit_price}
              onChange={(e) => setForm((f) => ({ ...f, unit_price: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              총투약일수
            </label>
            <input
              type="number"
              min={0}
              value={form.total_dosage_days}
              onChange={(e) => setForm((f) => ({ ...f, total_dosage_days: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 items-end">
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              저가대체 가산금
            </label>
            <input
              type="number"
              min={0}
              value={form.low_cost_surcharge}
              onChange={(e) => setForm((f) => ({ ...f, low_cost_surcharge: e.target.value }))}
              disabled={!form.low_cost_substitute}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card disabled:opacity-40"
            />
          </div>
          <div>
            <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">
              조제료(원)
            </label>
            <input
              type="number"
              min={0}
              value={form.dispensing_fee}
              onChange={(e) => setForm((f) => ({ ...f, dispensing_fee: e.target.value }))}
              className="w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card"
            />
          </div>
          <label className="flex items-center gap-1.5 text-xs text-text pb-2.5">
            <input
              type="checkbox"
              checked={form.low_cost_substitute}
              onChange={(e) =>
                setForm((f) => ({ ...f, low_cost_substitute: e.target.checked }))
              }
              className="accent-[#EF6600]"
            />
            저가대체 처방
          </label>
        </div>

        {error && (
          <div className="text-xs text-red-500 whitespace-pre-line border border-red-500/30 rounded-md p-2 bg-red-500/5">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || !form.prescription_name.trim()}
          className="bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "등록 중..." : "처방 등록"}
        </button>
      </form>
    </div>
  );
}
