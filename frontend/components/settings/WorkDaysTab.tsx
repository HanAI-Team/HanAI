'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, X } from 'lucide-react'
import { listDoctorWorkDays, createDoctorWorkDays } from '@/lib/api/doctor-work-days'
import { DoctorWorkDays } from '@/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const now = new Date()

export default function WorkDaysTab() {
  const router = useRouter()
  const [hospitalId, setHospitalId] = useState<string | null>(null)
  const [doctorId, setDoctorId] = useState<string | null>(null)
  const [rows, setRows] = useState<DoctorWorkDays[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [form, setForm] = useState({
    claim_period_year: now.getFullYear(),
    claim_period_month: now.getMonth() + 1,
    work_days: '',
  })
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [needsBirthDate, setNeedsBirthDate] = useState(false)

  useEffect(() => {
    fetch(`${BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then((res) => res.json())
      .then((me) => {
        setHospitalId(me.hospital_id)
        setDoctorId(me.id)
      })
      .catch(() => {})
  }, [])

  const loadRows = async (id: string) => {
    setLoading(true)
    try {
      setRows(await listDoctorWorkDays(id))
    } catch {
      // 목록 조회 실패는 조용히 무시 (빈 목록으로 표시)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (hospitalId) loadRows(hospitalId)
  }, [hospitalId])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!hospitalId || !doctorId) return
    setAddLoading(true)
    setAddError(null)
    setNeedsBirthDate(false)
    try {
      await createDoctorWorkDays(hospitalId, {
        doctor_id: doctorId,
        claim_period_year: Number(form.claim_period_year),
        claim_period_month: Number(form.claim_period_month),
        work_days: Number(form.work_days),
      })
      await loadRows(hospitalId)
      setShowAddModal(false)
      setForm({ claim_period_year: now.getFullYear(), claim_period_month: now.getMonth() + 1, work_days: '' })
    } catch (e: any) {
      const message = e.message || '진료일수 등록에 실패했습니다.'
      setAddError(message)
      if (message.includes('생년월일 미등록')) setNeedsBirthDate(true)
    } finally {
      setAddLoading(false)
    }
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="text-sm font-medium text-text mb-6">월별 의사별 진료일수</div>

      {loading ? (
        <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
      ) : rows.length === 0 ? (
        <div className="text-sm text-muted text-center py-12">등록된 진료일수가 없습니다</div>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="flex items-center justify-between border border-border rounded-xl px-4 py-4">
              <div className="font-medium text-text">{row.claim_period_year}년 {row.claim_period_month}월</div>
              <div className="text-xs text-subtext">생년월일 {row.doctor_birth_date} · 진료일수 {row.work_days}일</div>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowAddModal(true)}
        className="w-full mt-6 bg-[#EF6600] text-white rounded-xl py-3 flex items-center justify-center gap-2 hover:opacity-90"
      >
        <Plus className="w-4 h-4" /> 진료일수 추가
      </button>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-card w-full max-w-sm rounded-2xl">
            <div className="flex justify-between items-center p-5 border-b border-border">
              <div className="font-medium">진료일수 추가</div>
              <button onClick={() => setShowAddModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div className="flex gap-3">
                <input
                  type="number"
                  placeholder="청구년도"
                  value={form.claim_period_year}
                  onChange={(e) => setForm((f) => ({ ...f, claim_period_year: Number(e.target.value) }))}
                  required
                  className="w-1/2 bg-bg border border-border rounded-xl px-4 py-3"
                />
                <input
                  type="number"
                  placeholder="청구월"
                  min={1}
                  max={12}
                  value={form.claim_period_month}
                  onChange={(e) => setForm((f) => ({ ...f, claim_period_month: Number(e.target.value) }))}
                  required
                  className="w-1/2 bg-bg border border-border rounded-xl px-4 py-3"
                />
              </div>
              <input
                type="number"
                placeholder="진료일수"
                min={1}
                value={form.work_days}
                onChange={(e) => setForm((f) => ({ ...f, work_days: e.target.value }))}
                required
                className="w-full bg-bg border border-border rounded-xl px-4 py-3"
              />

              {addError && (
                <div className="text-red-500 text-sm">
                  {addError}
                  {needsBirthDate && (
                    <button
                      type="button"
                      onClick={() => router.push('/settings')}
                      className="block mt-2 text-[#EF6600] underline"
                    >
                      설정 &gt; 일반 탭에서 생년월일 등록하기
                    </button>
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={addLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium disabled:opacity-50"
              >
                {addLoading ? '등록 중...' : '등록하기'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
