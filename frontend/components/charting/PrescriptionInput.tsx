"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
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

const field =
  "w-full border border-border-strong rounded-md px-3 py-2 text-sm outline-none focus:border-[#EF6600] bg-card";
const label = "text-xs text-subtext mb-1 block";

export default function PrescriptionInput({
  medicalRecordId,
  patientBirthDate,
}: PrescriptionInputProps) {
  const [prescriptions, setPrescriptions] = useState<PrescriptionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getPrescriptions(medicalRecordId)
      .then((data) => {
        setPrescriptions(data);
      })
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
    <div className="rounded-lg border border-border bg-card overflow-hidden mb-4">
      {loading ? (
        <div className="text-xs text-subtext p-4">불러오는 중...</div>
      ) : prescriptions.length > 0 ? (
        <ul className="divide-y divide-border border-b border-border">
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

      {/* 헤더: 클릭하면 접기/펼치기 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-fill hover:opacity-90 transition-opacity"
      >
        <span className="text-sm font-medium text-text">한약 처방 입력</span>
        {open ? (
          <ChevronUp size={18} className="text-muted" />
        ) : (
          <ChevronDown size={18} className="text-muted" />
        )}
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="p-4 space-y-5">
          {/* 그룹 1: 기본 정보 */}
          <div>
            <p className="text-xs font-medium text-muted mb-2">기본 정보</p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={label}>처방명 *</label>
                <input
                  value={form.prescription_name}
                  onChange={(e) => setForm((f) => ({ ...f, prescription_name: e.target.value }))}
                  required
                  placeholder="예: 통비탕"
                  className={field}
                />
              </div>
              <div>
                <label className={label}>처방코드</label>
                <input
                  value={form.formula_code}
                  onChange={(e) => setForm((f) => ({ ...f, formula_code: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>처방구분</label>
                <select
                  value={form.prescription_type}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, prescription_type: e.target.value as PrescriptionType }))
                  }
                  className={field}
                >
                  {PRESCRIPTION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="border-t border-border" />

          {/* 그룹 2: 약재 정보 */}
          <div>
            <p className="text-xs font-medium text-muted mb-2">약재 정보</p>
            <div className="mb-3">
              <label className={label}>약재 구성</label>
              <textarea
                value={form.ingredients}
                onChange={(e) => setForm((f) => ({ ...f, ingredients: e.target.value }))}
                rows={2}
                placeholder="황기 12g, 당귀 10g, ..."
                className={`${field} resize-none`}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={label}>종수</label>
                <input
                  type="number"
                  min={0}
                  value={form.species_count}
                  onChange={(e) => setForm((f) => ({ ...f, species_count: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>총중량(g)</label>
                <input
                  type="number"
                  min={0}
                  step="0.1"
                  value={form.total_weight_g}
                  onChange={(e) => setForm((f) => ({ ...f, total_weight_g: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>가감등구분</label>
                <input
                  value={form.adjustment_type}
                  onChange={(e) => setForm((f) => ({ ...f, adjustment_type: e.target.value }))}
                  placeholder="B/A/S"
                  className={field}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-border" />

          {/* 그룹 3: 금액 정보 */}
          <div>
            <p className="text-xs font-medium text-muted mb-2">금액 정보</p>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div>
                <label className={label}>단가(원)</label>
                <input
                  type="number"
                  min={0}
                  value={form.unit_price}
                  onChange={(e) => setForm((f) => ({ ...f, unit_price: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>총투약일수</label>
                <input
                  type="number"
                  min={0}
                  value={form.total_dosage_days}
                  onChange={(e) => setForm((f) => ({ ...f, total_dosage_days: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>조제료(원)</label>
                <input
                  type="number"
                  min={0}
                  value={form.dispensing_fee}
                  onChange={(e) => setForm((f) => ({ ...f, dispensing_fee: e.target.value }))}
                  className={field}
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className={label}>저가대체 가산금</label>
                <input
                  type="number"
                  min={0}
                  value={form.low_cost_surcharge}
                  onChange={(e) => setForm((f) => ({ ...f, low_cost_surcharge: e.target.value }))}
                  disabled={!form.low_cost_substitute}
                  className={`${field} disabled:opacity-40 mt-0`}
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-text mt-4">
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
          </div>

          {error && (
            <div className="text-xs text-red-500 whitespace-pre-line border border-red-500/30 rounded-md p-2 bg-red-500/5">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !form.prescription_name.trim()}
            className="w-full py-2.5 rounded-lg text-white text-sm font-medium bg-[#EF6600] hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {submitting ? "등록 중..." : "처방 등록"}
          </button>
        </form>
      )}
    </div>
  );
}
