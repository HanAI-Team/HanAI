'use client'
import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import { getStaffList, createStaff, deactivateStaff, activateStaff } from '@/lib/api/staff'
import { Staff } from '@/types'

const STAFF_ROLE_LABEL: Record<string, string> = {
  nurse: '간호사',
  receptionist: '데스크',
}

export default function StaffTab() {
  const [staffList, setStaffList] = useState<Staff[]>([])
  const [staffLoading, setStaffLoading] = useState(false)
  const [staffLimit, setStaffLimit] = useState<number | null>(null)
  const [showAddStaffModal, setShowAddStaffModal] = useState(false)
  const [newStaff, setNewStaff] = useState({ name: '', email: '', password: '', role: 'nurse' })
  const [addStaffLoading, setAddStaffLoading] = useState(false)
  const [staffErrorMessage, setStaffErrorMessage] = useState<string | null>(null)

  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  })

  const loadStaffData = async () => {
    setStaffLoading(true)
    try {
      const [staff, subscription] = await Promise.all([
        getStaffList(),
        fetch(`${BASE_URL}/api/subscription/`, { headers: getHeaders() }).then(res => res.json()),
      ])
      setStaffList(staff)
      setStaffLimit(subscription.staff_limit)
    } catch (e: any) {
      setStaffErrorMessage(e.message || '하위 계정 정보를 불러오지 못했습니다.')
    } finally {
      setStaffLoading(false)
    }
  }

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddStaffLoading(true)
    try {
      await createStaff(newStaff)
      const updated = await getStaffList()
      setStaffList(updated)
      setShowAddStaffModal(false)
      setNewStaff({ name: '', email: '', password: '', role: 'nurse' })
    } catch (e: any) {
      setStaffErrorMessage(e.message || '하위 계정 생성에 실패했습니다.')
    } finally {
      setAddStaffLoading(false)
    }
  }

  const handleToggleActive = async (staff: Staff) => {
    try {
      const updated = staff.is_active 
        ? await deactivateStaff(staff.id) 
        : await activateStaff(staff.id)
      setStaffList(list => list.map(s => s.id === updated.id ? updated : s))
    } catch (e: any) {
      setStaffErrorMessage(e.message || '상태 변경에 실패했습니다.')
    }
  }

  useEffect(() => {
    loadStaffData()
  }, [])

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="text-sm font-medium text-text">하위 계정 관리</div>
        {staffLimit !== null && (
          <div className="text-xs text-subtext">
            {staffList.length} / {staffLimit}명
          </div>
        )}
      </div>

      {staffLoading ? (
        <div className="text-sm text-muted text-center py-12">불러오는 중...</div>
      ) : staffList.length === 0 ? (
        <div className="text-sm text-muted text-center py-12">등록된 하위 계정이 없습니다</div>
      ) : (
        <div className="space-y-3">
          {staffList.map((staff) => (
            <div key={staff.id} className="flex items-center justify-between border border-border rounded-xl px-4 py-4">
              <div>
                <div className="font-medium text-text">{staff.name}</div>
                <div className="text-xs text-subtext mt-0.5">{staff.email}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs px-3 py-1 bg-fill rounded-lg">
                  {STAFF_ROLE_LABEL[staff.role] || staff.role}
                </span>
                <button
                  onClick={() => handleToggleActive(staff)}
                  className={`px-4 py-1.5 text-xs rounded-lg font-medium transition-all ${
                    staff.is_active 
                      ? 'border border-border hover:bg-red-500/10 hover:text-red-400' 
                      : 'bg-[#EF6600] text-white'
                  }`}
                >
                  {staff.is_active ? '비활성화' : '활성화'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowAddStaffModal(true)}
        disabled={staffLimit !== null && staffList.length >= staffLimit}
        className="w-full mt-6 bg-[#EF6600] text-white rounded-xl py-3 flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50"
      >
        <Plus className="w-4 h-4" /> 하위 계정 추가
      </button>

      {/* 추가 모달 */}
      {showAddStaffModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-card w-full max-w-sm rounded-2xl">
            <div className="flex justify-between items-center p-5 border-b border-border">
              <div className="font-medium">하위 계정 추가</div>
              <button onClick={() => setShowAddStaffModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateStaff} className="p-5 space-y-4">
              <input
                placeholder="이름"
                value={newStaff.name}
                onChange={(e) => setNewStaff(s => ({...s, name: e.target.value}))}
                required
                className="w-full bg-bg border border-border rounded-xl px-4 py-3"
              />
              <input
                type="email"
                placeholder="이메일"
                value={newStaff.email}
                onChange={(e) => setNewStaff(s => ({...s, email: e.target.value}))}
                required
                className="w-full bg-bg border border-border rounded-xl px-4 py-3"
              />
              <input
                type="password"
                placeholder="비밀번호"
                value={newStaff.password}
                onChange={(e) => setNewStaff(s => ({...s, password: e.target.value}))}
                required
                className="w-full bg-bg border border-border rounded-xl px-4 py-3"
              />
              <button
                type="submit"
                disabled={addStaffLoading}
                className="w-full bg-[#EF6600] text-white py-3 rounded-xl font-medium"
              >
                {addStaffLoading ? '추가 중...' : '추가하기'}
              </button>
            </form>
          </div>
        </div>
      )}

      {staffErrorMessage && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-2xl p-6 text-center">
            <div className="text-red-400 mb-4">{staffErrorMessage}</div>
            <button onClick={() => setStaffErrorMessage(null)} className="bg-[#EF6600] text-white px-8 py-2 rounded-xl">
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  )
}