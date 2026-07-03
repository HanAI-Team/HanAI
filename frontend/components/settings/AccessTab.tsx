'use client'
import { useState, useEffect } from 'react'
import { getLoginLogs, getAccountHistories, LoginLog, AccountHistory } from '@/lib/api/auth'

const ACCOUNT_TYPE_LABEL: Record<string, string> = {
  doctor: '의사',
  staff: '직원',
}

const ACTION_LABEL: Record<string, string> = {
  created: '생성',
  deactivated: '비활성화',
  role_changed: '권한 변경',
}

function formatDate(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function AccessTab() {
  const [accessSubTab, setAccessSubTab] = useState<'login-logs' | 'account-histories'>('login-logs')
  const [loginLogs, setLoginLogs] = useState<LoginLog[]>([])
  const [accountHistories, setAccountHistories] = useState<AccountHistory[]>([])
  const [accessLoading, setAccessLoading] = useState(false)
  const [accessError, setAccessError] = useState<string | null>(null)

  const loadAccessData = async () => {
    setAccessLoading(true)
    setAccessError(null)
    try {
      const [logs, histories] = await Promise.all([
        getLoginLogs(),
        getAccountHistories()
      ])
      setLoginLogs(logs)
      setAccountHistories(histories)
    } catch (e: any) {
      setAccessError(e.message || '데이터를 불러오지 못했습니다.')
    } finally {
      setAccessLoading(false)
    }
  }

  useEffect(() => {
    loadAccessData()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex bg-fill border border-border rounded-2xl p-1">
        {[
          { value: 'login-logs', label: '로그인 기록' },
          { value: 'account-histories', label: '계정 이력' },
        ].map((t) => (
          <button
            key={t.value}
            onClick={() => setAccessSubTab(t.value as 'login-logs' | 'account-histories')}
            className={`flex-1 rounded-xl py-3 text-sm font-medium transition-all ${
              accessSubTab === t.value ? 'bg-card text-text shadow-sm' : 'text-subtext hover:text-text'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-card border border-border rounded-2xl p-6">
        {accessLoading ? (
          <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
        ) : accessError ? (
          <div className="text-red-500 text-center py-12">{accessError}</div>
        ) : accessSubTab === 'login-logs' ? (
          loginLogs.length === 0 ? (
            <div className="text-sm text-muted text-center py-12">로그인 기록이 없습니다</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left pb-3 pr-4">계정유형</th>
                    <th className="text-left pb-3 pr-4">성공여부</th>
                    <th className="text-left pb-3 pr-4">IP 주소</th>
                    <th className="text-left pb-3">시간</th>
                  </tr>
                </thead>
                <tbody>
                  {loginLogs.map((log) => (
                    <tr key={log.id} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4">{ACCOUNT_TYPE_LABEL[log.account_type] ?? log.account_type}</td>
                      <td className="py-3 pr-4">
                        <span className={`px-3 py-1 rounded-full text-[10px] font-medium ${
                          log.success 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {log.success ? '성공' : '실패'}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-mono text-subtext">{log.ip_address ?? '-'}</td>
                      <td className="py-3 text-subtext whitespace-nowrap">{formatDate(log.attempted_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          accountHistories.length === 0 ? (
            <div className="text-sm text-muted text-center py-12">계정 이력이 없습니다</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left pb-3 pr-4">계정유형</th>
                    <th className="text-left pb-3 pr-4">작업</th>
                    <th className="text-left pb-3">시간</th>
                  </tr>
                </thead>
                <tbody>
                  {accountHistories.map((h) => (
                    <tr key={h.id} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4">{ACCOUNT_TYPE_LABEL[h.account_type] ?? h.account_type}</td>
                      <td className="py-3 pr-4">{ACTION_LABEL[h.action] ?? h.action}</td>
                      <td className="py-3 text-subtext">{formatDate(h.started_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  )
}