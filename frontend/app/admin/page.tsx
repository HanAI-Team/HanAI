'use client'
import { useState } from 'react'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type PendingDoctor = {
  doctor_id: string
  name: string
  license_number: string
  clinic_name: string
  created_at: string
}

export default function AdminPage() {
  const [key, setKey] = useState('')
  const [authed, setAuthed] = useState(false)
  const [doctors, setDoctors] = useState<PendingDoctor[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [approving, setApproving] = useState<string | null>(null)

  async function fetchPending(adminKey: string) {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${BASE_URL}/api/auth/admin/pending`, {
        headers: { 'X-Admin-Key': adminKey },
      })
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      if (!res.ok) throw new Error()
      setDoctors(await res.json())
      setAuthed(true)
    } catch {
      setError('목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function approve(doctorId: string) {
    setApproving(doctorId)
    try {
      const res = await fetch(`${BASE_URL}/api/auth/admin/approve/${doctorId}`, {
        method: 'POST',
        headers: { 'X-Admin-Key': key },
      })
      if (!res.ok) throw new Error()
      setDoctors((prev) => prev.filter((d) => d.doctor_id !== doctorId))
    } catch {
      alert('승인에 실패했습니다.')
    } finally {
      setApproving(null)
    }
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#F5F2EE] flex items-center justify-center">
        <div className="bg-white rounded-xl border border-[#D4CCC4] p-8 w-full max-w-sm">
          <h1 className="text-lg font-medium text-[#232323] mb-1">관리자 페이지</h1>
          <p className="text-sm text-[#8A8480] mb-6">관리자 키를 입력하세요</p>
          {error && <p className="text-sm text-red-500 mb-3">{error}</p>}
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchPending(key)}
            placeholder="Admin Key"
            className="w-full border border-[#C8BFB6] rounded-md px-4 py-2.5 text-sm outline-none focus:border-[#EF6600] mb-3"
          />
          <button
            onClick={() => fetchPending(key)}
            disabled={loading || !key}
            className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {loading ? '확인 중...' : '접속'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F2EE] p-8">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-medium text-[#232323]">승인 대기 한의사</h1>
            <p className="text-sm text-[#8A8480] mt-0.5">{doctors.length}명 대기 중</p>
          </div>
          <button
            onClick={() => fetchPending(key)}
            className="text-sm text-[#8A8480] border border-[#C8BFB6] rounded-md px-3 py-1.5 hover:border-[#232323] hover:text-[#232323]"
          >
            새로고침
          </button>
        </div>

        {doctors.length === 0 ? (
          <div className="bg-white border border-[#D4CCC4] rounded-xl p-12 text-center text-sm text-[#8A8480]">
            승인 대기 중인 한의사가 없습니다
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {doctors.map((d) => (
              <div
                key={d.doctor_id}
                className="bg-white border border-[#D4CCC4] rounded-xl px-5 py-4 flex items-center justify-between gap-4"
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-sm font-medium text-[#232323]">
                    {d.name}
                  </span>
                  <span className="text-xs text-[#8A8480]">
                    {d.clinic_name} · 면허 {d.license_number}
                  </span>
                  <span className="text-xs text-[#B0AAA4]">
                    가입일 {new Date(d.created_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <button
                  onClick={() => approve(d.doctor_id)}
                  disabled={approving === d.doctor_id}
                  className="flex-shrink-0 bg-[#EF6600] text-white rounded-md px-4 py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {approving === d.doctor_id ? '처리 중...' : '승인'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
