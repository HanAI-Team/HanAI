'use client'
import { useEffect, useRef, useState } from 'react'
import { getPurgeLogs, DataPurgeLog } from '@/lib/api/patients'

const PURGE_TYPE_LABEL: Record<string, string> = {
  anonymize: '익명화',
  delete: '삭제',
}

function formatPurgedAt(s: string) {
  if (!s || s.length !== 14) return s
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)} ${s.slice(8, 10)}:${s.slice(10, 12)}:${s.slice(12, 14)}`
}

export default function PurgeTab() {
  const [logs, setLogs] = useState<DataPurgeLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    setLoading(true)
    setError(null)
    getPurgeLogs()
      .then(setLogs)
      .catch((e: any) => setError(e.message || '데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-2xl p-6">
        {loading ? (
          <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
        ) : error ? (
          <div className="text-red-500 text-center py-12">{error}</div>
        ) : logs.length === 0 ? (
          <div className="text-sm text-muted text-center py-12">파기 이력이 없습니다</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-3 pr-4">이름</th>
                  <th className="text-left pb-3 pr-4">파기유형</th>
                  <th className="text-left pb-3 pr-4">사유</th>
                  <th className="text-left pb-3">파기일시</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-border last:border-0">
                    <td className="py-3 pr-4">{log.patient_name_before ?? '-'}</td>
                    <td className="py-3 pr-4">{PURGE_TYPE_LABEL[log.purge_type] ?? log.purge_type}</td>
                    <td className="py-3 pr-4 text-subtext">{log.reason}</td>
                    <td className="py-3 text-subtext whitespace-nowrap">{formatPurgedAt(log.purged_at)}</td>
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
