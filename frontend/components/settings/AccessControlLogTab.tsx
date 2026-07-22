'use client'
import { useEffect, useState } from 'react'
import { getAccessControlLogs, AccessControlLog } from '@/lib/api/auth'
import { formatDateTime } from '@/lib/formatDateTime'

const ACTION_CLASS: Record<string, string> = {
  부여: 'bg-green-500/15 text-green-600',
  변경: 'bg-[#EF6600]/15 text-[#EF6600]',
  말소: 'bg-red-500/15 text-red-500',
}

export default function AccessControlLogTab() {
  const [logs, setLogs] = useState<AccessControlLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getAccessControlLogs()
      .then(setLogs)
      .catch((e: any) => setError(e.message || '데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      {loading ? (
        <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
      ) : error ? (
        <div className="text-red-500 text-center py-12">{error}</div>
      ) : logs.length === 0 ? (
        <div className="text-sm text-muted text-center py-12">권한 변경 이력이 없습니다</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left pb-3 pr-4">대상 계정</th>
                <th className="text-left pb-3 pr-4">변경내용</th>
                <th className="text-left pb-3 pr-4">변경자</th>
                <th className="text-left pb-3">변경일시</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-border last:border-0">
                  <td className="py-3 pr-4">
                    {log.target_account_name ?? log.target_account_id.slice(0, 8)}
                    <span className="text-muted ml-1">({log.role})</span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-medium ${ACTION_CLASS[log.action_type] ?? 'bg-muted/20 text-muted'}`}>
                      {log.action_type}
                    </span>
                    {log.reason && <span className="text-subtext ml-2">{log.reason}</span>}
                  </td>
                  <td className="py-3 pr-4 text-subtext">{log.acted_by_name ?? (log.acted_by ? log.acted_by.slice(0, 8) : '-')}</td>
                  <td className="py-3 text-subtext whitespace-nowrap">{formatDateTime(log.acted_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
