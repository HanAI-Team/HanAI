'use client'
import { useState } from 'react'
import { Download, X } from 'lucide-react'
import { downloadDbExport, DB_EXPORT_TABLES, DbExportFormat } from '@/lib/api/dbExport'

export default function DbExportTab() {
  const [table, setTable] = useState<string>(DB_EXPORT_TABLES[0].value)
  const [format, setFormat] = useState<DbExportFormat>('csv')
  const [showReasonModal, setShowReasonModal] = useState(false)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDownload(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await downloadDbExport(table, format, reason.trim())
      setShowReasonModal(false)
      setReason('')
    } catch (e: any) {
      setError(e.message || 'DB 내역 추출에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="text-sm font-medium text-text mb-1">DB 내역 추출</div>
        <p className="text-xs text-subtext mb-6">
          HIRA 청구SW 기능검사용 — 테이블 전체 내역을 TEXT(CSV) 또는 Excel 파일로 추출합니다.
        </p>

        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label className="block text-xs text-subtext mb-1">테이블</label>
            <select
              value={table}
              onChange={(e) => setTable(e.target.value)}
              className="bg-fill border border-border rounded-lg px-3 py-2 text-sm text-text outline-none min-w-[240px]"
            >
              {DB_EXPORT_TABLES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-subtext mb-1">포맷</label>
            <div className="flex bg-fill border border-border rounded-lg p-1">
              {(['csv', 'xlsx'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFormat(f)}
                  className={`px-4 py-1.5 text-sm rounded-md transition-all ${
                    format === f ? 'bg-card text-text shadow-sm' : 'text-subtext hover:text-text'
                  }`}
                >
                  {f.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => setShowReasonModal(true)}
            className="bg-[#EF6600] text-white rounded-lg px-4 py-2 text-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Download className="w-3.5 h-3.5" /> 다운로드
          </button>
        </div>

        {error && !showReasonModal && <div className="text-red-500 text-xs mt-3">{error}</div>}
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
              {error && <div className="text-red-500 text-xs">{error}</div>}
              <div className="flex gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setShowReasonModal(false)
                    setReason('')
                  }}
                  className="flex-1 border border-border text-text rounded-md py-2.5 text-sm hover:bg-bg transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={loading || !reason.trim()}
                  className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-sm disabled:opacity-50 hover:opacity-90 transition-opacity"
                >
                  {loading ? '다운로드 중...' : '확인'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
