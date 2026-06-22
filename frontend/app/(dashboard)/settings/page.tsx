'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { jwtDecode } from 'jwt-decode'
import { getStaffList, createStaff, deactivateStaff, activateStaff } from '@/lib/api/staff'
import { Staff } from '@/types'
import { Plus, X, MessageSquare } from 'lucide-react'

const BETA_FEEDBACK_FORM_URL = 'https://forms.gle/6HANKvSxdvfwKXFP9'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

const STAFF_ROLE_LABEL: Record<string, string> = {
  nurse: '간호사',
  receptionist: '데스크',
}

export default function SettingsPage() {
  const router = useRouter()
  const [tab, setTab] = useState<'general' | 'staff'>('general')
  const [isOwner] = useState(() => {
    if (typeof window === 'undefined') return false
    const token = localStorage.getItem('token')
    if (!token) return false
    try {
      return jwtDecode<{ role: string }>(token).role === 'owner'
    } catch {
      return false
    }
  })

  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)

  const [staffList, setStaffList] = useState<Staff[]>([])
  const [staffLoading, setStaffLoading] = useState(false)
  const [staffLimit, setStaffLimit] = useState<number | null>(null)
  const [showAddStaffModal, setShowAddStaffModal] = useState(false)
  const [newStaff, setNewStaff] = useState({ name: '', email: '', password: '', role: 'nurse' })
  const [addStaffLoading, setAddStaffLoading] = useState(false)
  const [staffErrorMessage, setStaffErrorMessage] = useState<string | null>(null)

  async function loadStaffData() {
    setStaffLoading(true)
    try {
      const [staff, subscription] = await Promise.all([
        getStaffList(),
        fetch(`${BASE_URL}/api/subscription/`, { headers: getHeaders() }).then((res) => {
          if (!res.ok) throw new Error('구독 정보 조회 실패')
          return res.json()
        }),
      ])
      setStaffList(staff)
      setStaffLimit(subscription.staff_limit)
    } catch (e: any) {
      setStaffErrorMessage(e.message || '하위 계정 정보를 불러오지 못했습니다.')
    } finally {
      setStaffLoading(false)
    }
  }

  useEffect(() => {
    if (tab !== 'staff' || !isOwner) return
    Promise.resolve().then(loadStaffData)
  }, [tab, isOwner])

  function handleLogout() {
    localStorage.removeItem('token')
    router.push('/login')
  }

  async function handleChangePassword() {
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('새 비밀번호가 일치하지 않습니다.')
      return
    }
    if (pwForm.new_password.length < 8) {
      setPwError('비밀번호는 8자 이상이어야 합니다.')
      return
    }
    setPwLoading(true)
    setPwError(null)
    try {
      const res = await fetch(`${BASE_URL}/api/auth/password`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({
          current_password: pwForm.current_password,
          new_password: pwForm.new_password,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '비밀번호 변경 실패')
      }
      setPwSuccess(true)
      setPwForm({ current_password: '', new_password: '', confirm: '' })
      setTimeout(() => setPwSuccess(false), 3000)
    } catch (e: any) {
      setPwError(e.message)
    } finally {
      setPwLoading(false)
    }
  }

  async function handleCreateStaff(e: React.FormEvent) {
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

  async function handleToggleActive(staff: Staff) {
    try {
      const updated = staff.is_active
        ? await deactivateStaff(staff.id)
        : await activateStaff(staff.id)
      setStaffList((list) => list.map((s) => (s.id === updated.id ? updated : s)))
    } catch (e: any) {
      setStaffErrorMessage(e.message || '상태 변경에 실패했습니다.')
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-[480px]">
      <div className="mb-6">
        <h1 className="font-serif text-2xl text-text">설정</h1>
        <p className="text-xs text-subtext mt-1">계정 및 환경 설정</p>
      </div>

      {isOwner && (
        <div className="flex bg-fill border border-border rounded-md p-1 mb-6">
          {[
            { value: 'general', label: '일반' },
            { value: 'staff', label: '하위 계정 관리' },
          ].map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value as 'general' | 'staff')}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                tab === t.value ? 'bg-card text-text shadow-sm' : 'text-subtext'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {tab === 'general' && (
        <div className="flex flex-col gap-4">
          <div className="bg-card border border-border rounded-lg p-5">
            <div className="text-xs font-medium text-text uppercase tracking-wide mb-4">비밀번호 변경</div>
            <form onSubmit={(e) => { e.preventDefault(); handleChangePassword() }} className="flex flex-col gap-3">
              {[
                { label: '현재 비밀번호', key: 'current_password' },
                { label: '새 비밀번호', key: 'new_password' },
                { label: '새 비밀번호 확인', key: 'confirm' },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs text-subtext uppercase tracking-wide mb-1.5">{field.label}</label>
                  <input
                    type="password"
                    value={pwForm[field.key as keyof typeof pwForm]}
                    onChange={(e) => setPwForm((f) => ({ ...f, [field.key]: e.target.value }))}
                    required
                    className="w-full bg-bg border border-border rounded-md px-4 py-2.5 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                  />
                </div>
              ))}
              {pwError && (
                <div className="text-xs text-red-500">{pwError}</div>
              )}
              <button
                type="submit"
                disabled={pwLoading}
                className={`w-full rounded-md py-2.5 text-sm font-medium transition-all mt-1 ${
                  pwSuccess
                    ? 'bg-green-600 text-white'
                    : 'bg-[#EF6600] text-white hover:opacity-90 disabled:opacity-50'
                }`}
              >
                {pwSuccess ? '✓ 변경되었습니다' : pwLoading ? '변경 중...' : '비밀번호 변경'}
              </button>
            </form>
          </div>
          <div className="bg-card border border-border rounded-lg p-5">
            <div className="text-xs font-medium text-text uppercase tracking-wide mb-4">계정</div>
            <button
              onClick={handleLogout}
              className="w-full border border-border-strong rounded-md py-2.5 text-sm text-subtext hover:border-text hover:text-text transition-all"
            >
              로그아웃
            </button>
          </div>
          <a
            href={BETA_FEEDBACK_FORM_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-card border border-border rounded-lg p-5 flex items-center justify-between hover:border-[#EF6600] transition-all"
          >
            <span className="text-sm text-text">베타 피드백 남기기</span>
            <MessageSquare className="w-4 h-4 text-subtext" />
          </a>
        </div>
      )}

      {tab === 'staff' && isOwner && (
        <div className="flex flex-col gap-4">
          <div className="bg-card border border-border rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-medium text-text uppercase tracking-wide">하위 계정</div>
              {staffLimit !== null && (
                <div className="text-xs text-subtext">
                  {staffList.length} / {staffLimit}명
                </div>
              )}
            </div>

            {staffLoading ? (
              <div className="text-sm text-muted text-center py-8">불러오는 중...</div>
            ) : staffList.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">등록된 하위 계정이 없습니다</div>
            ) : (
              <div className="flex flex-col gap-2">
                {staffList.map((staff) => (
                  <div
                    key={staff.id}
                    className="flex items-center justify-between border border-border rounded-md px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-text flex items-center gap-2">
                        {staff.name}
                        <span className="text-[10px] text-subtext border border-border rounded px-1.5 py-0.5">
                          {STAFF_ROLE_LABEL[staff.role] || staff.role}
                        </span>
                        {!staff.is_active && (
                          <span className="text-[10px] text-red-500 border border-red-200 rounded px-1.5 py-0.5">
                            비활성
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-subtext mt-0.5 truncate">{staff.email}</div>
                    </div>
                    <button
                      onClick={() => handleToggleActive(staff)}
                      className={`flex-shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                        staff.is_active
                          ? 'border border-border-strong text-subtext hover:border-text hover:text-text'
                          : 'bg-[#EF6600] text-white hover:opacity-90'
                      }`}
                    >
                      {staff.is_active ? '비활성화' : '활성화'}
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => setShowAddStaffModal(true)}
              disabled={staffLimit !== null && staffList.length >= staffLimit}
              className="w-full mt-4 bg-[#EF6600] text-white rounded-md py-2.5 text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Plus className="w-4 h-4" /> 하위 계정 추가
            </button>
          </div>
        </div>
      )}

      {/* 하위 계정 추가 모달 */}
      {showAddStaffModal && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="text-sm font-medium text-text">하위 계정 추가</div>
              <button
                onClick={() => setShowAddStaffModal(false)}
                className="text-subtext hover:text-text transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateStaff} className="p-5 flex flex-col gap-3">
              <div>
                <label className="text-xs text-subtext mb-1 block">이름 *</label>
                <input
                  value={newStaff.name}
                  onChange={(e) => setNewStaff((s) => ({ ...s, name: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">이메일 *</label>
                <input
                  type="email"
                  value={newStaff.email}
                  onChange={(e) => setNewStaff((s) => ({ ...s, email: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">비밀번호 *</label>
                <input
                  type="password"
                  value={newStaff.password}
                  onChange={(e) => setNewStaff((s) => ({ ...s, password: e.target.value }))}
                  required
                  className="w-full bg-fill border border-border rounded-md px-3 py-2 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-subtext mb-1 block">역할</label>
                <div className="flex gap-4">
                  {[
                    { value: 'nurse', label: '간호사' },
                    { value: 'receptionist', label: '데스크' },
                  ].map((opt) => (
                    <label key={opt.value} className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="staff-role"
                        value={opt.value}
                        checked={newStaff.role === opt.value}
                        onChange={() => setNewStaff((s) => ({ ...s, role: opt.value }))}
                        className="accent-[#EF6600]"
                      />
                      <span className="text-sm text-text">{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button
                type="submit"
                disabled={addStaffLoading}
                className="w-full bg-[#EF6600] text-white rounded-md py-2.5 text-sm mt-1 disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                {addStaffLoading ? '추가 중...' : '추가'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 에러 모달 */}
      {staffErrorMessage && (
        <div className="fixed inset-0 bg-[#232323]/50 z-50 flex items-center justify-center p-4">
          <div className="bg-card rounded-xl p-6 w-full max-w-xs shadow-xl text-center">
            <div className="text-sm text-text mb-4">{staffErrorMessage}</div>
            <button
              onClick={() => setStaffErrorMessage(null)}
              className="bg-[#EF6600] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition-opacity"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
