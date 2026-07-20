'use client'
import { useEffect, useState } from 'react'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type PendingDoctor = {
  doctor_id: string
  name: string
  license_number: string
  clinic_name: string
  created_at: string
}

type FeeItem = {
  code: string
  name: string
  category: string
  unit_price: number
  is_insured: boolean
  is_standalone: boolean
  insured_health: boolean
  insured_medical_aid: boolean
  insured_veterans: boolean
  effective_date: string | null
  expired_date: string | null
}

const EMPTY_FEE: Omit<FeeItem, 'effective_date' | 'expired_date'> & { effective_date: string; expired_date: string } = {
  code: '', name: '', category: '', unit_price: 0,
  is_insured: true, is_standalone: false,
  insured_health: true, insured_medical_aid: true, insured_veterans: false,
  effective_date: '', expired_date: '',
}

type DrugItem = {
  product_code: string
  product_name: string
  ingredient_code: string | null
  ingredient_name: string | null
  company_name: string | null
  spec: string | null
  unit: string | null
  unit_price: number
  administration_route: string | null
  classification_code: string | null
  is_prescription: boolean | null
  effective_date: string | null
}

const EMPTY_DRUG = {
  product_code: '', product_name: '', ingredient_code: '', ingredient_name: '',
  company_name: '', spec: '', unit: '', unit_price: 0,
  administration_route: '', classification_code: '',
  is_prescription: true, effective_date: '',
}

type MaterialItem = {
  code: string
  name: string
  category: string | null
  unit_price: number
  effective_date: string | null
  expired_date: string | null
}

const EMPTY_MATERIAL = {
  code: '', name: '', category: '', unit_price: 0,
  effective_date: '', expired_date: '',
}

export default function AdminPage() {
  const [key, setKey] = useState('')
  const [authed, setAuthed] = useState(false)
  const [tab, setTab] = useState<'doctors' | 'fees' | 'drugs' | 'materials'>('doctors')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 의사 승인
  const [doctors, setDoctors] = useState<PendingDoctor[]>([])
  const [approving, setApproving] = useState<string | null>(null)

  // 수가 관리
  const [fees, setFees] = useState<FeeItem[]>([])
  const [feeForm, setFeeForm] = useState({ ...EMPTY_FEE })
  const [editCode, setEditCode] = useState<string | null>(null)
  const [feeError, setFeeError] = useState('')
  const [feeLoading, setFeeLoading] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('')

  // 약가 관리
  const [drugs, setDrugs] = useState<DrugItem[]>([])
  const [drugQuery, setDrugQuery] = useState('')
  const [drugForm, setDrugForm] = useState({ ...EMPTY_DRUG })
  const [editDrugCode, setEditDrugCode] = useState<string | null>(null)
  const [drugError, setDrugError] = useState('')
  const [drugLoading, setDrugLoading] = useState(false)

  // 치료재료대 관리
  const [materials, setMaterials] = useState<MaterialItem[]>([])
  const [materialForm, setMaterialForm] = useState({ ...EMPTY_MATERIAL })
  const [editMaterialCode, setEditMaterialCode] = useState<string | null>(null)
  const [materialError, setMaterialError] = useState('')
  const [materialLoading, setMaterialLoading] = useState(false)

  async function fetchPending(adminKey: string) {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${BASE_URL}/api/auth/admin/pending`, {
        headers: { 'X-Admin-Key': adminKey },
      })
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      if (!res.ok) throw new Error()
      setDoctors(await res.json())
      setAuthed(true)
    } catch {
      setError('목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function approve(doctorId: string) {
    setApproving(doctorId)
    try {
      const res = await fetch(`${BASE_URL}/api/auth/admin/approve/${doctorId}`, {
        method: 'POST',
        headers: { 'X-Admin-Key': key },
      })
      if (!res.ok) throw new Error()
      setDoctors((prev) => prev.filter((d) => d.doctor_id !== doctorId))
    } catch {
      alert('승인에 실패했습니다.')
    } finally {
      setApproving(null)
    }
  }

  async function fetchFees() {
    setFeeLoading(true)
    try {
      const token = localStorage.getItem('token')
      const q = categoryFilter ? `?category=${encodeURIComponent(categoryFilter)}` : ''
      const res = await fetch(`${BASE_URL}/api/billing/fees${q}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) setFees(await res.json())
    } finally {
      setFeeLoading(false)
    }
  }

  useEffect(() => {
    if (authed && tab === 'fees') fetchFees()
  }, [authed, tab, categoryFilter])

  useEffect(() => {
    if (authed && tab === 'materials') fetchMaterials()
  }, [authed, tab])

  async function submitFee() {
    setFeeError('')
    const payload = {
      ...feeForm,
      unit_price: Number(feeForm.unit_price),
      effective_date: feeForm.effective_date || null,
      expired_date: feeForm.expired_date || null,
    }
    const isEdit = editCode !== null
    const url = isEdit
      ? `${BASE_URL}/api/billing/fees/${editCode}`
      : `${BASE_URL}/api/billing/fees`
    const res = await fetch(url, {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key },
      body: JSON.stringify(payload),
    })
    if (res.status === 409) { setFeeError('이미 존재하는 행위코드입니다.'); return }
    if (!res.ok) { setFeeError('저장에 실패했습니다.'); return }
    setFeeForm({ ...EMPTY_FEE })
    setEditCode(null)
    fetchFees()
  }

  function startEdit(fee: FeeItem) {
    setEditCode(fee.code)
    setFeeForm({
      code: fee.code,
      name: fee.name,
      category: fee.category,
      unit_price: fee.unit_price,
      is_insured: fee.is_insured,
      is_standalone: fee.is_standalone,
      insured_health: fee.insured_health,
      insured_medical_aid: fee.insured_medical_aid,
      insured_veterans: fee.insured_veterans,
      effective_date: fee.effective_date ?? '',
      expired_date: fee.expired_date ?? '',
    })
    setFeeError('')
  }

  async function deleteFee(code: string) {
    if (!confirm(`${code} 코드를 삭제하시겠습니까?`)) return
    const res = await fetch(`${BASE_URL}/api/billing/fees/${code}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    })
    if (!res.ok) { alert('삭제에 실패했습니다.'); return }
    fetchFees()
  }

  async function searchDrugs() {
    if (!drugQuery.trim()) { setDrugs([]); return }
    setDrugLoading(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(
        `${BASE_URL}/api/billing/drugs?q=${encodeURIComponent(drugQuery.trim())}&limit=100`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      )
      if (res.ok) setDrugs(await res.json())
    } finally {
      setDrugLoading(false)
    }
  }

  async function submitDrug() {
    setDrugError('')
    const payload = {
      ...drugForm,
      unit_price: Number(drugForm.unit_price),
      ingredient_code: drugForm.ingredient_code || null,
      ingredient_name: drugForm.ingredient_name || null,
      company_name: drugForm.company_name || null,
      spec: drugForm.spec || null,
      unit: drugForm.unit || null,
      administration_route: drugForm.administration_route || null,
      classification_code: drugForm.classification_code || null,
      effective_date: drugForm.effective_date || null,
    }
    const isEdit = editDrugCode !== null
    const url = isEdit
      ? `${BASE_URL}/api/billing/drugs/${editDrugCode}`
      : `${BASE_URL}/api/billing/drugs`
    if (isEdit) delete (payload as { product_code?: string }).product_code
    const res = await fetch(url, {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key },
      body: JSON.stringify(payload),
    })
    if (res.status === 409) { setDrugError('이미 존재하는 제품코드입니다.'); return }
    if (!res.ok) { setDrugError('저장에 실패했습니다.'); return }
    setDrugForm({ ...EMPTY_DRUG })
    setEditDrugCode(null)
    searchDrugs()
  }

  function startEditDrug(drug: DrugItem) {
    setEditDrugCode(drug.product_code)
    setDrugForm({
      product_code: drug.product_code,
      product_name: drug.product_name,
      ingredient_code: drug.ingredient_code ?? '',
      ingredient_name: drug.ingredient_name ?? '',
      company_name: drug.company_name ?? '',
      spec: drug.spec ?? '',
      unit: drug.unit ?? '',
      unit_price: drug.unit_price,
      administration_route: drug.administration_route ?? '',
      classification_code: drug.classification_code ?? '',
      is_prescription: drug.is_prescription ?? true,
      effective_date: drug.effective_date ?? '',
    })
    setDrugError('')
  }

  async function deleteDrug(product_code: string) {
    if (!confirm(`${product_code} 제품코드를 삭제하시겠습니까?`)) return
    const res = await fetch(`${BASE_URL}/api/billing/drugs/${product_code}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    })
    if (!res.ok) { alert('삭제에 실패했습니다.'); return }
    searchDrugs()
  }

  async function fetchMaterials() {
    setMaterialLoading(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${BASE_URL}/api/billing/materials`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) setMaterials(await res.json())
    } finally {
      setMaterialLoading(false)
    }
  }

  async function submitMaterial() {
    setMaterialError('')
    const payload = {
      ...materialForm,
      unit_price: Number(materialForm.unit_price),
      category: materialForm.category || null,
      effective_date: materialForm.effective_date || null,
      expired_date: materialForm.expired_date || null,
    }
    const isEdit = editMaterialCode !== null
    const url = isEdit
      ? `${BASE_URL}/api/billing/materials/${editMaterialCode}`
      : `${BASE_URL}/api/billing/materials`
    if (isEdit) delete (payload as { code?: string }).code
    const res = await fetch(url, {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key },
      body: JSON.stringify(payload),
    })
    if (res.status === 409) { setMaterialError('이미 존재하는 치료재료 코드입니다.'); return }
    if (!res.ok) { setMaterialError('저장에 실패했습니다.'); return }
    setMaterialForm({ ...EMPTY_MATERIAL })
    setEditMaterialCode(null)
    fetchMaterials()
  }

  function startEditMaterial(material: MaterialItem) {
    setEditMaterialCode(material.code)
    setMaterialForm({
      code: material.code,
      name: material.name,
      category: material.category ?? '',
      unit_price: material.unit_price,
      effective_date: material.effective_date ?? '',
      expired_date: material.expired_date ?? '',
    })
    setMaterialError('')
  }

  async function deleteMaterial(code: string) {
    if (!confirm(`${code} 코드를 삭제하시겠습니까?`)) return
    const res = await fetch(`${BASE_URL}/api/billing/materials/${code}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    })
    if (!res.ok) { alert('삭제에 실패했습니다.'); return }
    fetchMaterials()
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="bg-card rounded-xl border border-border p-8 w-full max-w-sm">
          <h1 className="text-lg font-medium text-text mb-1">관리자 페이지</h1>
          <p className="text-sm text-subtext mb-6">관리자 키를 입력하세요</p>
          {error && <p className="text-sm text-red-500 mb-3">{error}</p>}
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchPending(key)}
            placeholder="Admin Key"
            className="w-full border border-border-strong rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600] mb-3"
          />
          <button
            onClick={() => fetchPending(key)}
            disabled={loading || !key}
            className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {loading ? '확인 중...' : '접속'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg p-8">
      <div className="max-w-4xl mx-auto">
        {/* 탭 */}
        <div className="flex gap-1 mb-6 border-b border-border">
          {(['doctors', 'fees', 'drugs', 'materials'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t
                  ? 'border-[#EF6600] text-[#EF6600]'
                  : 'border-transparent text-subtext hover:text-text'
              }`}
            >
              {t === 'doctors' ? '의사 승인' : t === 'fees' ? '수가 관리' : t === 'drugs' ? '약가 관리' : '치료재료대 관리'}
            </button>
          ))}
        </div>

        {/* 의사 승인 탭 */}
        {tab === 'doctors' && (
          <>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl font-medium text-text">승인 대기 한의사</h1>
                <p className="text-sm text-subtext mt-0.5">{doctors.length}명 대기 중</p>
              </div>
              <button
                onClick={() => fetchPending(key)}
                className="text-sm text-subtext border border-border-strong rounded-md px-3 py-1.5 hover:border-text hover:text-text"
              >
                새로고침
              </button>
            </div>
            {doctors.length === 0 ? (
              <div className="bg-card border border-border rounded-xl p-12 text-center text-sm text-subtext">
                승인 대기 중인 한의사가 없습니다
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {doctors.map((d) => (
                  <div
                    key={d.doctor_id}
                    className="bg-card border border-border rounded-xl px-5 py-4 flex items-center justify-between gap-4"
                  >
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="text-sm font-medium text-text">{d.name}</span>
                      <span className="text-xs text-subtext">{d.clinic_name} · 면허 {d.license_number}</span>
                      <span className="text-xs text-muted">가입일 {new Date(d.created_at).toLocaleDateString('ko-KR')}</span>
                    </div>
                    <button
                      onClick={() => approve(d.doctor_id)}
                      disabled={approving === d.doctor_id}
                      className="flex-shrink-0 bg-[#EF6600] text-white rounded-md px-4 py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
                    >
                      {approving === d.doctor_id ? '처리 중...' : '승인'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* 수가 관리 탭 */}
        {tab === 'fees' && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-medium text-text">수가 코드 관리</h1>
              <div className="flex gap-2">
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="border border-border-strong rounded-md px-3 py-1.5 text-sm bg-bg text-text"
                >
                  <option value="">전체 카테고리</option>
                  {['침술', '뜸', '부항', '추나', '분구침술'].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <button
                  onClick={fetchFees}
                  className="text-sm text-subtext border border-border-strong rounded-md px-3 py-1.5 hover:border-text hover:text-text"
                >
                  새로고침
                </button>
              </div>
            </div>

            {/* 추가/수정 폼 */}
            <div className="bg-card border border-border rounded-xl p-5 mb-5">
              <h2 className="text-sm font-medium text-text mb-4">
                {editCode ? `수정 중: ${editCode}` : '새 수가 코드 추가'}
              </h2>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <input
                  disabled={!!editCode}
                  placeholder="행위코드 (예: AA159)"
                  value={feeForm.code}
                  onChange={(e) => setFeeForm((p) => ({ ...p, code: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm disabled:opacity-50"
                />
                <input
                  placeholder="행위명"
                  value={feeForm.name}
                  onChange={(e) => setFeeForm((p) => ({ ...p, name: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <select
                  value={feeForm.category}
                  onChange={(e) => setFeeForm((p) => ({ ...p, category: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm bg-bg text-text"
                >
                  <option value="">카테고리 선택</option>
                  {['침술', '뜸', '부항', '추나', '분구침술'].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="수가 (원)"
                  value={feeForm.unit_price}
                  onChange={(e) => setFeeForm((p) => ({ ...p, unit_price: Number(e.target.value) }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  placeholder="시작일"
                  value={feeForm.effective_date}
                  onChange={(e) => setFeeForm((p) => ({ ...p, effective_date: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  placeholder="종료일"
                  value={feeForm.expired_date}
                  onChange={(e) => setFeeForm((p) => ({ ...p, expired_date: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div className="flex gap-4 text-sm text-subtext mb-4">
                {(
                  [
                    ['is_insured', '급여'],
                    ['is_standalone', '단독산정'],
                    ['insured_health', '건강보험'],
                    ['insured_medical_aid', '의료급여'],
                    ['insured_veterans', '보훈'],
                  ] as const
                ).map(([field, label]) => (
                  <label key={field} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={feeForm[field]}
                      onChange={(e) => setFeeForm((p) => ({ ...p, [field]: e.target.checked }))}
                    />
                    {label}
                  </label>
                ))}
              </div>
              {feeError && <p className="text-sm text-red-500 mb-3">{feeError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={submitFee}
                  disabled={!feeForm.code || !feeForm.name || !feeForm.category}
                  className="bg-[#EF6600] text-white rounded-md px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {editCode ? '수정 저장' : '추가'}
                </button>
                {editCode && (
                  <button
                    onClick={() => { setEditCode(null); setFeeForm({ ...EMPTY_FEE }); setFeeError('') }}
                    className="border border-border-strong rounded-md px-4 py-2 text-sm text-subtext hover:text-text"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>

            {/* 수가 목록 테이블 */}
            {feeLoading ? (
              <p className="text-sm text-subtext">불러오는 중...</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-left text-subtext">
                      <th className="py-2 pr-4 font-medium">코드</th>
                      <th className="py-2 pr-4 font-medium">행위명</th>
                      <th className="py-2 pr-4 font-medium">카테고리</th>
                      <th className="py-2 pr-4 font-medium text-right">수가(원)</th>
                      <th className="py-2 pr-4 font-medium">급여</th>
                      <th className="py-2 font-medium">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fees.map((f) => (
                      <tr key={f.code} className="border-b border-border hover:bg-card">
                        <td className="py-2.5 pr-4 font-mono text-xs">{f.code}</td>
                        <td className="py-2.5 pr-4">{f.name}</td>
                        <td className="py-2.5 pr-4 text-subtext">{f.category}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">{f.unit_price.toLocaleString()}</td>
                        <td className="py-2.5 pr-4 text-subtext">{f.is_insured ? '급여' : '비급여'}</td>
                        <td className="py-2.5">
                          <div className="flex gap-2">
                            <button
                              onClick={() => startEdit(f)}
                              className="text-xs text-[#EF6600] hover:underline"
                            >
                              수정
                            </button>
                            <button
                              onClick={() => deleteFee(f.code)}
                              className="text-xs text-red-500 hover:underline"
                            >
                              삭제
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {fees.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-10 text-center text-subtext">
                          등록된 수가 코드가 없습니다
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* 약가 관리 탭 */}
        {tab === 'drugs' && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-medium text-text">약가 코드 관리</h1>
              <p className="text-sm text-subtext">
                전체 건수가 많아 검색으로만 조회됩니다 — 제품코드/제품명/주성분명
              </p>
            </div>

            {/* 추가/수정 폼 */}
            <div className="bg-card border border-border rounded-xl p-5 mb-5">
              <h2 className="text-sm font-medium text-text mb-4">
                {editDrugCode ? `수정 중: ${editDrugCode}` : '새 약가 코드 추가'}
              </h2>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <input
                  disabled={!!editDrugCode}
                  placeholder="제품코드"
                  value={drugForm.product_code}
                  onChange={(e) => setDrugForm((p) => ({ ...p, product_code: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm disabled:opacity-50"
                />
                <input
                  placeholder="제품명"
                  value={drugForm.product_name}
                  onChange={(e) => setDrugForm((p) => ({ ...p, product_name: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="주성분코드"
                  value={drugForm.ingredient_code}
                  onChange={(e) => setDrugForm((p) => ({ ...p, ingredient_code: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="주성분명"
                  value={drugForm.ingredient_name}
                  onChange={(e) => setDrugForm((p) => ({ ...p, ingredient_name: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="업체명"
                  value={drugForm.company_name}
                  onChange={(e) => setDrugForm((p) => ({ ...p, company_name: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="규격"
                  value={drugForm.spec}
                  onChange={(e) => setDrugForm((p) => ({ ...p, spec: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="단위"
                  value={drugForm.unit}
                  onChange={(e) => setDrugForm((p) => ({ ...p, unit: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="상한금액(원)"
                  value={drugForm.unit_price}
                  onChange={(e) => setDrugForm((p) => ({ ...p, unit_price: Number(e.target.value) }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="투여(내복/외용/주사/기타)"
                  value={drugForm.administration_route}
                  onChange={(e) => setDrugForm((p) => ({ ...p, administration_route: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="분류(식약분류) 코드"
                  value={drugForm.classification_code}
                  onChange={(e) => setDrugForm((p) => ({ ...p, classification_code: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  placeholder="고시 적용일"
                  value={drugForm.effective_date}
                  onChange={(e) => setDrugForm((p) => ({ ...p, effective_date: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div className="flex gap-4 text-sm text-subtext mb-4">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={drugForm.is_prescription}
                    onChange={(e) => setDrugForm((p) => ({ ...p, is_prescription: e.target.checked }))}
                  />
                  전문의약품
                </label>
              </div>
              {drugError && <p className="text-sm text-red-500 mb-3">{drugError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={submitDrug}
                  disabled={!drugForm.product_code || !drugForm.product_name}
                  className="bg-[#EF6600] text-white rounded-md px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {editDrugCode ? '수정 저장' : '추가'}
                </button>
                {editDrugCode && (
                  <button
                    onClick={() => { setEditDrugCode(null); setDrugForm({ ...EMPTY_DRUG }); setDrugError('') }}
                    className="border border-border-strong rounded-md px-4 py-2 text-sm text-subtext hover:text-text"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>

            {/* 검색 */}
            <div className="flex gap-2 mb-4">
              <input
                placeholder="제품코드, 제품명 또는 주성분명으로 검색"
                value={drugQuery}
                onKeyDown={(e) => e.key === 'Enter' && searchDrugs()}
                onChange={(e) => setDrugQuery(e.target.value)}
                className="flex-1 border border-border-strong rounded-md px-3 py-2 text-sm"
              />
              <button
                onClick={searchDrugs}
                className="bg-[#EF6600] text-white rounded-md px-4 py-2 text-sm font-medium hover:opacity-90"
              >
                검색
              </button>
            </div>

            {/* 약가 목록 테이블 */}
            {drugLoading ? (
              <p className="text-sm text-subtext">불러오는 중...</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-left text-subtext">
                      <th className="py-2 pr-4 font-medium">제품코드</th>
                      <th className="py-2 pr-4 font-medium">제품명</th>
                      <th className="py-2 pr-4 font-medium">주성분명</th>
                      <th className="py-2 pr-4 font-medium">업체명</th>
                      <th className="py-2 pr-4 font-medium text-right">상한금액(원)</th>
                      <th className="py-2 font-medium">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drugs.map((d) => (
                      <tr key={d.product_code} className="border-b border-border hover:bg-card">
                        <td className="py-2.5 pr-4 font-mono text-xs">{d.product_code}</td>
                        <td className="py-2.5 pr-4">{d.product_name}</td>
                        <td className="py-2.5 pr-4 text-subtext">{d.ingredient_name}</td>
                        <td className="py-2.5 pr-4 text-subtext">{d.company_name}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">{d.unit_price.toLocaleString()}</td>
                        <td className="py-2.5">
                          <div className="flex gap-2">
                            <button
                              onClick={() => startEditDrug(d)}
                              className="text-xs text-[#EF6600] hover:underline"
                            >
                              수정
                            </button>
                            <button
                              onClick={() => deleteDrug(d.product_code)}
                              className="text-xs text-red-500 hover:underline"
                            >
                              삭제
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {drugs.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-10 text-center text-subtext">
                          {drugQuery ? '검색 결과가 없습니다' : '검색어를 입력하세요 (전체 목록은 너무 많아 검색으로만 조회됩니다)'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* 치료재료대 관리 탭 */}
        {tab === 'materials' && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-medium text-text">치료재료대 관리</h1>
              <button
                onClick={fetchMaterials}
                className="text-sm text-subtext border border-border-strong rounded-md px-3 py-1.5 hover:border-text hover:text-text"
              >
                새로고침
              </button>
            </div>

            {/* 추가/수정 폼 */}
            <div className="bg-card border border-border rounded-xl p-5 mb-5">
              <h2 className="text-sm font-medium text-text mb-4">
                {editMaterialCode ? `수정 중: ${editMaterialCode}` : '새 치료재료 코드 추가'}
              </h2>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <input
                  disabled={!!editMaterialCode}
                  placeholder="치료재료 코드"
                  value={materialForm.code}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, code: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm disabled:opacity-50"
                />
                <input
                  placeholder="치료재료명"
                  value={materialForm.name}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, name: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  placeholder="분류"
                  value={materialForm.category}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, category: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="number"
                  placeholder="상한금액(원)"
                  value={materialForm.unit_price}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, unit_price: Number(e.target.value) }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  placeholder="시작일"
                  value={materialForm.effective_date}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, effective_date: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="date"
                  placeholder="종료일"
                  value={materialForm.expired_date}
                  onChange={(e) => setMaterialForm((p) => ({ ...p, expired_date: e.target.value }))}
                  className="border border-border-strong rounded-md px-3 py-2 text-sm"
                />
              </div>
              {materialError && <p className="text-sm text-red-500 mb-3">{materialError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={submitMaterial}
                  disabled={!materialForm.code || !materialForm.name}
                  className="bg-[#EF6600] text-white rounded-md px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {editMaterialCode ? '수정 저장' : '추가'}
                </button>
                {editMaterialCode && (
                  <button
                    onClick={() => { setEditMaterialCode(null); setMaterialForm({ ...EMPTY_MATERIAL }); setMaterialError('') }}
                    className="border border-border-strong rounded-md px-4 py-2 text-sm text-subtext hover:text-text"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>

            {/* 치료재료 목록 테이블 */}
            {materialLoading ? (
              <p className="text-sm text-subtext">불러오는 중...</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-left text-subtext">
                      <th className="py-2 pr-4 font-medium">코드</th>
                      <th className="py-2 pr-4 font-medium">치료재료명</th>
                      <th className="py-2 pr-4 font-medium">분류</th>
                      <th className="py-2 pr-4 font-medium text-right">상한금액(원)</th>
                      <th className="py-2 font-medium">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {materials.map((m) => (
                      <tr key={m.code} className="border-b border-border hover:bg-card">
                        <td className="py-2.5 pr-4 font-mono text-xs">{m.code}</td>
                        <td className="py-2.5 pr-4">{m.name}</td>
                        <td className="py-2.5 pr-4 text-subtext">{m.category}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">{m.unit_price.toLocaleString()}</td>
                        <td className="py-2.5">
                          <div className="flex gap-2">
                            <button
                              onClick={() => startEditMaterial(m)}
                              className="text-xs text-[#EF6600] hover:underline"
                            >
                              수정
                            </button>
                            <button
                              onClick={() => deleteMaterial(m.code)}
                              className="text-xs text-red-500 hover:underline"
                            >
                              삭제
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {materials.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-10 text-center text-subtext">
                          등록된 치료재료 코드가 없습니다
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
