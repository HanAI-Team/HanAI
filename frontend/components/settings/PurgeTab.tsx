'use client'
import { useEffect, useRef, useState } from 'react'
import { Download, X } from 'lucide-react'
import { getPurgeLogs, downloadPurgeLogsCsv, DataPurgeLog } from '@/lib/api/patients'
import { formatDateTime } from '@/lib/formatDateTime'

const PURGE_TYPE_LABEL: Record<string, string> = {
  anonymize: '익명화',
  delete: '삭제',
}

export default function PurgeTab() {
  const [logs, setLogs] = useState<DataPurgeLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fetchedRef = useRef(false)

  const [showReasonModal, setShowReasonModal] = useState(false)
  const [reason, setReason] = useState('')
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

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

  async function handleDownload(e: React.FormEvent) {
    e.preventDefault()
    if (!reason.trim()) return
    setDownloadLoading(true)
    setDownloadError(null)
    try {
      await downloadPurgeLogsCsv(reason.trim())
      setShowReasonModal(false)
      setReason('')
    } catch (e: any) {
      setDownloadError(e.message || 'CSV 다운로드에 실패했습니다.')
    } finally {
      setDownloadLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => setShowReasonModal(true)}
          className="bg-[#EF6600] text-white rounded-lg px-4 py-2 text-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
        >
          <Download className="w-3.5 h-3.5" /> CSV 다운로드
        </button>
      </div>

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
                    <td className="py-3 text-subtext whitespace-nowrap">{formatDateTime(log.purged_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showReasonModal && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">다운로드 사유 입력</div>
              <button
                onClick={() => {
                  setShowReasonModal(false)
                  setReason('')
                  setDownloadError(null)
                }}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleDownload} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">사유 *</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required
                  minLength={1}
                  rows={3}
                  placeholder="다운로드 사유를 입력하세요"
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors resize-none"
                />
              </div>
              {downloadError && <div className="text-red-500 text-xs">{downloadError}</div>}
              <div className="flex gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setShowReasonModal(false)
                    setReason('')
                    setDownloadError(null)
                  }}
                  className="flex-1 border border-border text-text rounded-md py-2.5 text-sm hover:bg-bg transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={downloadLoading || !reason.trim()}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
                >
                  {downloadLoading ? '다운로드 중...' : '확인'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
