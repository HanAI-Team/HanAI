'use client'
import { useEffect, useRef, useState } from 'react'
import { getChangeLog, ChangeLogItem } from '@/lib/api/changeLog'
import Pagination from './Pagination'

const PAGE_SIZE = 20

function formatDateTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export default function ChangeLogTab() {
  const [items, setItems] = useState<ChangeLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  async function load(pg: number, from: string, to: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await getChangeLog(pg, PAGE_SIZE, from || undefined, to || undefined)
      setItems(res.items)
      setTotal(res.total)
    } catch (e: any) {
      setError(e.message || '변경일 이력을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(page, dateFrom, dateTo), 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, dateFrom, dateTo])

  return (
    <div className="space-y-4">
      <div className="bg-card border border-border rounded-2xl p-4 flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-subtext mb-1">시작일 (최초입력일 기준)</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-subtext mb-1">종료일</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value)
              setPage(1)
            }}
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="text-sm text-muted text-center py-16">불러오는 중...</div>
        ) : error ? (
          <div className="text-red-500 text-center py-16">{error}</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-muted text-center py-16">조회된 진료기록이 없습니다</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border">
                <tr className="text-xs text-subtext">
                  <th className="p-3 text-left">환자명</th>
                  <th className="p-3 text-left">진료기록ID</th>
                  <th className="p-3 text-left">최초입력일시</th>
                  <th className="p-3 text-left">최종수정일시</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-t border-border hover:bg-fill transition-colors">
                    <td className="p-3 text-text font-medium">{item.patient_name}</td>
                    <td className="p-3 font-mono text-subtext">{item.id.slice(0, 8)}</td>
                    <td className="p-3 text-subtext whitespace-nowrap">{formatDateTime(item.created_at)}</td>
                    <td className="p-3 text-subtext whitespace-nowrap">{formatDateTime(item.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} totalPages={totalPages} totalCount={total} onPageChange={setPage} itemLabel="건" />
          </div>
        )}
      </div>
    </div>
  )
}
