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

export default function AdminPage() {
  const [key, setKey] = useState('')
  const [authed, setAuthed] = useState(false)
  const [tab, setTab] = useState<'doctors' | 'fees'>('doctors')
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
          {(['doctors', 'fees'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t
                  ? 'border-[#EF6600] text-[#EF6600]'
                  : 'border-transparent text-subtext hover:text-text'
              }`}
            >
              {t === 'doctors' ? '의사 승인' : '수가 관리'}
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
      </div>
    </div>
  )
}
