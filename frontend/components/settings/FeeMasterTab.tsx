'use client'
import { useEffect, useRef, useState } from 'react'
import { Plus, Search, X } from 'lucide-react'
import { getFees, createFee, updateFee, deleteFee, FeeItem, FeeCreateInput } from '@/lib/api/fees'
import Pagination from './Pagination'

const PAGE_SIZE = 20

const emptyForm = {
  code: '',
  name: '',
  category: '',
  unit_price: '',
  is_insured: true,
  insured_health: true,
  insured_medical_aid: true,
  insured_veterans: false,
  effective_date: '',
  expired_date: '',
}

export default function FeeMasterTab() {
  const [items, setItems] = useState<FeeItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [editTarget, setEditTarget] = useState<FeeItem | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<FeeItem | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  async function load(pg: number, s: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await getFees(pg, PAGE_SIZE, s || undefined)
      setItems(res.items)
      setTotal(res.total)
    } catch (e: any) {
      setError(e.message || '수가 마스터 목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(page, search), 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search])

  function openEdit(item: FeeItem) {
    setEditTarget(item)
    setForm({
      code: item.code,
      name: item.name,
      category: item.category,
      unit_price: String(item.unit_price),
      is_insured: item.is_insured,
      insured_health: item.insured_health,
      insured_medical_aid: item.insured_medical_aid,
      insured_veterans: item.insured_veterans,
      effective_date: item.effective_date || '',
      expired_date: item.expired_date || '',
    })
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const body: FeeCreateInput = {
        code: form.code,
        name: form.name,
        category: form.category,
        unit_price: Number(form.unit_price),
        is_insured: form.is_insured,
        insured_health: form.insured_health,
        insured_medical_aid: form.insured_medical_aid,
        insured_veterans: form.insured_veterans,
        effective_date: form.effective_date || null,
        expired_date: form.expired_date || null,
      }
      await createFee(body)
      setShowAddModal(false)
      setForm(emptyForm)
      await load(page, search)
    } catch (e: any) {
      setError(e.message || '수가 등록에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  async function handleEditSave(e: React.FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updateFee(editTarget.code, {
        name: form.name,
        category: form.category,
        unit_price: Number(form.unit_price),
        is_insured: form.is_insured,
        insured_health: form.insured_health,
        insured_medical_aid: form.insured_medical_aid,
        insured_veterans: form.insured_veterans,
        effective_date: form.effective_date || null,
        expired_date: form.expired_date || null,
      })
      setItems((prev) => prev.map((i) => (i.code === updated.code ? updated : i)))
      setEditTarget(null)
    } catch (e: any) {
      setError(e.message || '수가 수정에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setSaving(true)
    try {
      await deleteFee(deleteTarget.code)
      setDeleteTarget(null)
      await load(page, search)
    } catch (e: any) {
      setError(e.message || '수가 삭제에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 bg-fill border border-border rounded-md px-3 py-2 flex-1 min-w-[160px] max-w-xs">
          <Search className="w-3.5 h-3.5 text-muted flex-shrink-0" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="코드 또는 명칭 검색..."
            className="flex-1 bg-transparent text-xs text-text outline-none"
          />
        </div>
        <button
          onClick={() => {
            setForm(emptyForm)
            setShowAddModal(true)
          }}
          className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity"
        >
          <Plus className="w-3.5 h-3.5" /> 수가 추가
        </button>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">
            {search ? '검색 결과가 없습니다' : '등록된 수가가 없습니다'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr className="text-xs text-subtext">
                  <th className="p-3 text-left">코드</th>
                  <th className="p-3 text-left">명칭</th>
                  <th className="p-3 text-left">분류</th>
                  <th className="p-3 text-right">단가</th>
                  <th className="p-3 text-left">급여</th>
                  <th className="p-3 text-left">유효기간</th>
                  <th className="p-3 text-center">액션</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.code} className="border-t border-border hover:bg-fill transition-colors">
                    <td className="p-3 font-mono text-text">{item.code}</td>
                    <td className="p-3 text-text font-medium">{item.name}</td>
                    <td className="p-3 text-subtext">{item.category}</td>
                    <td className="p-3 text-subtext text-right">{item.unit_price.toLocaleString()}원</td>
                    <td className="p-3 text-subtext">{item.is_insured ? '급여' : '비급여'}</td>
                    <td className="p-3 text-subtext whitespace-nowrap">
                      {item.effective_date || '-'} ~ {item.expired_date || '-'}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => openEdit(item)}
                          className="px-2.5 py-1 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors"
                        >
                          수정
                        </button>
                        <button
                          onClick={() => setDeleteTarget(item)}
                          className="px-2.5 py-1 text-xs rounded-md border border-red-500/40 text-red-500 hover:bg-red-500/10 transition-colors"
                        >
                          삭제
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} totalPages={totalPages} totalCount={total} onPageChange={setPage} itemLabel="건" />
          </div>
        )}
      </div>

      {(showAddModal || editTarget) && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">{editTarget ? '수가 수정' : '수가 추가'}</div>
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setEditTarget(null)
                }}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={editTarget ? handleEditSave : handleCreate} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">행위코드 *</label>
                <input
                  value={form.code}
                  onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                  required
                  disabled={!!editTarget}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">행위명 *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">분류 * (침술/뜸/부항/추나)</label>
                <input
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">단가(원) *</label>
                <input
                  type="number"
                  value={form.unit_price}
                  onChange={(e) => setForm((f) => ({ ...f, unit_price: e.target.value }))}
                  required
                  min={0}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div className="flex gap-3">
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">적용일</label>
                  <input
                    type="date"
                    value={form.effective_date}
                    onChange={(e) => setForm((f) => ({ ...f, effective_date: e.target.value }))}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">만료일</label>
                  <input
                    type="date"
                    value={form.expired_date}
                    onChange={(e) => setForm((f) => ({ ...f, expired_date: e.target.value }))}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-text">
                {[
                  { key: 'is_insured' as const, label: '급여' },
                  { key: 'insured_health' as const, label: '건강보험' },
                  { key: 'insured_medical_aid' as const, label: '의료급여' },
                  { key: 'insured_veterans' as const, label: '보훈' },
                ].map((opt) => (
                  <label key={opt.key} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form[opt.key]}
                      onChange={(e) => setForm((f) => ({ ...f, [opt.key]: e.target.checked }))}
                      className="accent-[#EF6600]"
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
              {error && <div className="text-red-500 text-xs">{error}</div>}
              <button
                type="submit"
                disabled={saving}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm mt-1 disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {saving ? '저장 중...' : editTarget ? '저장' : '등록'}
              </button>
            </form>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm font-medium text-text mb-2">
              {deleteTarget.name}({deleteTarget.code}) 수가를 삭제하시겠습니까?
            </div>
            <div className="text-xs text-red-500 mb-4">이 작업은 되돌릴 수 없습니다</div>
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 border border-border text-text rounded-md py-2.5 text-sm hover:bg-bg transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={saving}
                className="flex-1 bg-red-500 text-white rounded-md py-2.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {saving ? '처리 중...' : '확인'}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && !showAddModal && !editTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm text-text mb-4">{error}</div>
            <button
              onClick={() => setError(null)}
              className="bg-[#EF6600] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition-opacity"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
