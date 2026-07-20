'use client'
import { useEffect, useState } from 'react'
import { getAuditLogs, AuditLogItem } from '@/lib/api/auditLogs'

const ACTION_CLASS: Record<string, string> = {
  CREATE: 'bg-green-500/15 text-green-600',
  INSERT: 'bg-green-500/15 text-green-600',
  UPDATE: 'bg-[#EF6600]/15 text-[#EF6600]',
  DELETE: 'bg-red-500/15 text-red-500',
  ANONYMIZE: 'bg-red-500/15 text-red-500',
  READ: 'bg-muted/20 text-muted',
}

function formatChangedAt(s: string) {
  if (!s || s.length !== 14) return s
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)} ${s.slice(8, 10)}:${s.slice(10, 12)}:${s.slice(12, 14)}`
}

function toCompactDate(dateInput: string) {
  return dateInput.replaceAll('-', '')
}

export default function AuditLogTab() {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAuditLogs({
        start_date: startDate ? toCompactDate(startDate) : undefined,
        end_date: endDate ? toCompactDate(endDate) : undefined,
      })
      setLogs(data)
    } catch (e: any) {
      setError(e.message || '데이터를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="space-y-4">
      <div className="bg-card border border-border rounded-2xl p-4 flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-subtext mb-1">시작일</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-subtext mb-1">종료일</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={load}
          className="bg-[#EF6600] text-white rounded-lg px-4 py-2 text-sm hover:opacity-90"
        >
          조회
        </button>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6">
        {loading ? (
          <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
        ) : error ? (
          <div className="text-red-500 text-center py-12">{error}</div>
        ) : logs.length === 0 ? (
          <div className="text-sm text-muted text-center py-12">조회된 로그가 없습니다</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-3 pr-4">테이블명</th>
                  <th className="text-left pb-3 pr-4">레코드ID</th>
                  <th className="text-left pb-3 pr-4">액션</th>
                  <th className="text-left pb-3">변경일시</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-border last:border-0">
                    <td className="py-3 pr-4 font-mono">{log.table_name}</td>
                    <td className="py-3 pr-4 font-mono text-subtext truncate max-w-[180px]">{log.record_id}</td>
                    <td className="py-3 pr-4">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-medium ${ACTION_CLASS[log.action] ?? 'bg-muted/20 text-muted'}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 text-subtext whitespace-nowrap">{formatChangedAt(log.changed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
