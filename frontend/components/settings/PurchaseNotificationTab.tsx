'use client'
import { useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import {
  getPurchaseRecords,
  createPurchaseRecord,
  updatePurchaseRecord,
  deletePurchaseRecord,
  reportPurchaseRecord,
  checkMissingDeclarations,
  PurchaseRecordItem,
  PurchaseRecordType,
  PurchaseRecordCreateInput,
  MissingDeclarationItem,
} from '@/lib/api/purchaseRecords'

const emptyForm = {
  record_type: 'purchase' as PurchaseRecordType,
  item_name: '',
  item_code: '',
  spec: '',
  quantity: '1',
  unit_price: '',
  amount: '',
  supplier_name: '',
  transaction_date: '',
}

const today = new Date()

export default function PurchaseNotificationTab() {
  const [recordType, setRecordType] = useState<PurchaseRecordType>('purchase')
  const [items, setItems] = useState<PurchaseRecordItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAddModal, setShowAddModal] = useState(false)
  const [editTarget, setEditTarget] = useState<PurchaseRecordItem | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<PurchaseRecordItem | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const [checkYear, setCheckYear] = useState(today.getFullYear())
  const [checkMonth, setCheckMonth] = useState(today.getMonth() + 1)
  const [missingItems, setMissingItems] = useState<MissingDeclarationItem[] | null>(null)
  const [checking, setChecking] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await getPurchaseRecords(recordType)
      setItems(res)
    } catch (e: any) {
      setError(e.message || '목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordType])

  function openEdit(item: PurchaseRecordItem) {
    setEditTarget(item)
    setForm({
      record_type: item.record_type,
      item_name: item.item_name,
      item_code: item.item_code || '',
      spec: item.spec || '',
      quantity: item.quantity,
      unit_price: String(item.unit_price),
      amount: String(item.amount),
      supplier_name: item.supplier_name || '',
      transaction_date: item.transaction_date,
    })
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const body: PurchaseRecordCreateInput = {
        record_type: recordType,
        item_name: form.item_name,
        item_code: form.item_code || null,
        spec: form.spec || null,
        quantity: Number(form.quantity) || 1,
        unit_price: Number(form.unit_price) || 0,
        amount: Number(form.amount) || 0,
        supplier_name: form.supplier_name || null,
        transaction_date: form.transaction_date,
      }
      await createPurchaseRecord(body)
      setShowAddModal(false)
      setForm(emptyForm)
      await load()
    } catch (e: any) {
      setError(e.message || '등록에 실패했습니다.')
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
      const updated = await updatePurchaseRecord(editTarget.id, {
        item_name: form.item_name,
        item_code: form.item_code || null,
        spec: form.spec || null,
        quantity: Number(form.quantity) || 1,
        unit_price: Number(form.unit_price) || 0,
        amount: Number(form.amount) || 0,
        supplier_name: form.supplier_name || null,
        transaction_date: form.transaction_date,
      })
      setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
      setEditTarget(null)
    } catch (e: any) {
      setError(e.message || '수정에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setSaving(true)
    try {
      await deletePurchaseRecord(deleteTarget.id)
      setDeleteTarget(null)
      await load()
    } catch (e: any) {
      setError(e.message || '삭제에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  async function handleReport(item: PurchaseRecordItem) {
    try {
      const updated = await reportPurchaseRecord(item.id)
      setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
    } catch (e: any) {
      setError(e.message || '신고(송신) 처리에 실패했습니다.')
    }
  }

  async function handleCheck() {
    setChecking(true)
    setError(null)
    try {
      const res = await checkMissingDeclarations(checkYear, checkMonth)
      setMissingItems(res.items)
    } catch (e: any) {
      setError(e.message || '누락 점검에 실패했습니다.')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
          <div className="flex bg-fill border border-border rounded-md p-1">
            {(['purchase', 'compound'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setRecordType(t)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  recordType === t ? 'bg-card text-text shadow-sm' : 'text-subtext'
                }`}
              >
                {t === 'purchase' ? '치료재료·원료약 구입내역' : '자체 조제(제제)약 내역'}
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              setForm(emptyForm)
              setShowAddModal(true)
            }}
            className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3.5 h-3.5" /> 내역 추가
          </button>
        </div>

        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          {loading ? (
            <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
          ) : items.length === 0 ? (
            <div className="text-sm text-muted text-center py-16">등록된 내역이 없습니다</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border">
                  <tr className="text-xs text-subtext">
                    <th className="p-3 text-left">품목명</th>
                    <th className="p-3 text-left">규격</th>
                    <th className="p-3 text-right">수량</th>
                    <th className="p-3 text-right">금액</th>
                    <th className="p-3 text-left">{recordType === 'purchase' ? '거래처' : '조제일'}</th>
                    <th className="p-3 text-left">거래일자</th>
                    <th className="p-3 text-left">신고상태</th>
                    <th className="p-3 text-center">액션</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border hover:bg-fill transition-colors">
                      <td className="p-3 text-text font-medium">{item.item_name}</td>
                      <td className="p-3 text-subtext">{item.spec || '-'}</td>
                      <td className="p-3 text-subtext text-right">{item.quantity}</td>
                      <td className="p-3 text-subtext text-right">{item.amount.toLocaleString()}원</td>
                      <td className="p-3 text-subtext">{item.supplier_name || '-'}</td>
                      <td className="p-3 text-subtext whitespace-nowrap">{item.transaction_date}</td>
                      <td className="p-3">
                        {item.reported ? (
                          <span className="text-xs text-green-600">신고완료</span>
                        ) : (
                          <span className="text-xs text-amber-500">미신고</span>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center justify-center gap-1.5">
                          {!item.reported && (
                            <button
                              onClick={() => handleReport(item)}
                              className="px-2.5 py-1 text-xs rounded-md border border-[#EF6600]/40 text-[#EF6600] hover:bg-[#EF6600]/10 transition-colors"
                            >
                              송신
                            </button>
                          )}
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
            </div>
          )}
        </div>
      </div>

      <div>
        <div className="text-sm font-medium text-text mb-2">청구 시 신고 누락 점검</div>
        <p className="text-xs text-subtext mb-3">
          해당 월 청구에 사용된 치료재료 중, 같은 달에 신고(송신) 처리된 구입내역이 없는 코드를 점검합니다.
        </p>
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <input
            type="number"
            value={checkYear}
            onChange={(e) => setCheckYear(Number(e.target.value))}
            className="w-24 bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
          />
          <span className="text-sm text-subtext">년</span>
          <input
            type="number"
            min={1}
            max={12}
            value={checkMonth}
            onChange={(e) => setCheckMonth(Number(e.target.value))}
            className="w-20 bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
          />
          <span className="text-sm text-subtext">월</span>
          <button
            onClick={handleCheck}
            disabled={checking}
            className="bg-[#EF6600] text-white rounded-md px-3 py-2 text-xs hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {checking ? '점검 중...' : '점검하기'}
          </button>
        </div>
        {missingItems !== null && (
          <div className="bg-card border border-border rounded-2xl overflow-hidden">
            {missingItems.length === 0 ? (
              <div className="text-sm text-muted text-center py-10">누락된 신고 내역이 없습니다</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-border">
                  <tr className="text-xs text-subtext">
                    <th className="p-3 text-left">코드</th>
                    <th className="p-3 text-left">명칭</th>
                    <th className="p-3 text-right">청구 건수</th>
                    <th className="p-3 text-right">총 사용량</th>
                  </tr>
                </thead>
                <tbody>
                  {missingItems.map((m) => (
                    <tr key={m.code} className="border-t border-border">
                      <td className="p-3 font-mono text-text">{m.code}</td>
                      <td className="p-3 text-text">{m.name}</td>
                      <td className="p-3 text-amber-500 text-right">{m.claim_count}</td>
                      <td className="p-3 text-subtext text-right">{m.total_qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {(showAddModal || editTarget) && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">
                {editTarget ? '내역 수정' : recordType === 'purchase' ? '구입내역 추가' : '자체 조제(제제)약 내역 추가'}
              </div>
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
                <label className="text-xs text-subtext mb-1 block">품목명 *</label>
                <input
                  value={form.item_name}
                  onChange={(e) => setForm((f) => ({ ...f, item_name: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">치료재료 코드 (해당 시)</label>
                <input
                  value={form.item_code}
                  onChange={(e) => setForm((f) => ({ ...f, item_code: e.target.value }))}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">규격</label>
                <input
                  value={form.spec}
                  onChange={(e) => setForm((f) => ({ ...f, spec: e.target.value }))}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div className="flex gap-3">
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">수량</label>
                  <input
                    type="number"
                    value={form.quantity}
                    onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
                <div className="w-1/2">
                  <label className="text-xs text-subtext mb-1 block">단가(원)</label>
                  <input
                    type="number"
                    value={form.unit_price}
                    onChange={(e) => setForm((f) => ({ ...f, unit_price: e.target.value }))}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">금액(원)</label>
                <input
                  type="number"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              {recordType === 'purchase' && (
                <div>
                  <label className="text-xs text-subtext mb-1 block">거래처</label>
                  <input
                    value={form.supplier_name}
                    onChange={(e) => setForm((f) => ({ ...f, supplier_name: e.target.value }))}
                    className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
              )}
              <div>
                <label className="text-xs text-subtext mb-1 block">
                  {recordType === 'purchase' ? '구입일자 *' : '조제일자 *'}
                </label>
                <input
                  type="date"
                  value={form.transaction_date}
                  onChange={(e) => setForm((f) => ({ ...f, transaction_date: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
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
            <div className="text-sm font-medium text-text mb-2">{deleteTarget.item_name} 내역을 삭제하시겠습니까?</div>
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
