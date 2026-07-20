'use client'
import { useEffect, useRef, useState } from 'react'
import { Plus, X } from 'lucide-react'
import {
  getRejectionCodes,
  createRejectionCode,
  deleteRejectionCode,
  RejectionCodeItem,
} from '@/lib/api/rejectionCodes'
import Pagination from './Pagination'

const PAGE_SIZE = 20
const CATEGORIES = ['반송', '심사불능', '수탁기관통보']

const emptyForm = { category: CATEGORIES[0], code: '', detail_code: '', description: '' }

export default function RejectionCodeTab() {
  const [items, setItems] = useState<RejectionCodeItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<RejectionCodeItem | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  async function load(pg: number, cat: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await getRejectionCodes(pg, PAGE_SIZE, cat || undefined)
      setItems(res.items)
      setTotal(res.total)
    } catch (e: any) {
      setError(e.message || '코드 목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(page, category), 200)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, category])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createRejectionCode(form)
      setShowAddModal(false)
      setForm(emptyForm)
      await load(page, category)
    } catch (e: any) {
      setError(e.message || '코드 등록에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setSaving(true)
    try {
      await deleteRejectionCode(deleteTarget.id)
      setDeleteTarget(null)
      await load(page, category)
    } catch (e: any) {
      setError(e.message || '코드 삭제에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value)
            setPage(1)
          }}
          className="bg-fill border border-border rounded-md px-3 py-2 text-xs text-text outline-none"
        >
          <option value="">전체 카테고리</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button
          onClick={() => {
            setForm(emptyForm)
            setShowAddModal(true)
          }}
          className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity"
        >
          <Plus className="w-3.5 h-3.5" /> 코드 추가
        </button>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">등록된 코드가 없습니다</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr className="text-xs text-subtext">
                  <th className="p-3 text-left">카테고리</th>
                  <th className="p-3 text-left">코드</th>
                  <th className="p-3 text-left">상세코드</th>
                  <th className="p-3 text-left">설명</th>
                  <th className="p-3 text-center">액션</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-t border-border hover:bg-fill transition-colors">
                    <td className="p-3 text-subtext">{item.category}</td>
                    <td className="p-3 font-mono text-text">{item.code}</td>
                    <td className="p-3 font-mono text-subtext">{item.detail_code || '-'}</td>
                    <td className="p-3 text-text">{item.description}</td>
                    <td className="p-3">
                      <div className="flex items-center justify-center">
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

      {showAddModal && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">코드 추가</div>
              <button onClick={() => setShowAddModal(false)} className="text-subtext hover:text-text transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">카테고리 *</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">코드 *</label>
                  <input
                    value={form.code}
                    onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                    required
                    maxLength={2}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">상세코드</label>
                  <input
                    value={form.detail_code}
                    onChange={(e) => setForm((f) => ({ ...f, detail_code: e.target.value }))}
                    maxLength={2}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">설명 *</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  required
                  rows={3}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              {error && <div className="text-red-500 text-xs">{error}</div>}
              <button
                type="submit"
                disabled={saving}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm mt-1 disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {saving ? '등록 중...' : '등록'}
              </button>
            </form>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm font-medium text-text mb-2">
              [{deleteTarget.category}] {deleteTarget.code}
              {deleteTarget.detail_code ? `-${deleteTarget.detail_code}` : ''} 코드를 삭제하시겠습니까?
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

      {error && !showAddModal && (
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
