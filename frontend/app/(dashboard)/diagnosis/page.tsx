'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { getPatients, createPatient, getPatientRecords, importPatientsFromCsv } from '@/lib/api/patients'
import { uploadAndAnalyze, askDiagnosis, diagnoseText } from '@/lib/api/diagnosis'
import { Patient, DiagnosisResult } from '@/types'

export default function DiagnosisPage() {
  const router = useRouter()
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [activeTab, setActiveTab] = useState<'record'|'result'|'history'|'ask'>('record')
  const [isRecording, setIsRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [memo, setMemo] = useState('')
  const [result, setResult] = useState<DiagnosisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [search, setSearch] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newPatient, setNewPatient] = useState({ name: '', birth_date: '', gender: '', phone: '' })
  const [addLoading, setAddLoading] = useState(false)
  const [askQuestion, setAskQuestion] = useState('')
  const [askHistory, setAskHistory] = useState<{ question: string; answer: string }[]>([])
  const [askLoading, setAskLoading] = useState(false)
  const [askMode, setAskMode] = useState<'ask' | 'diagnose'>('ask')
  const [symptomText, setSymptomText] = useState('')
  const [records, setRecords] = useState<{ id: string; recorded_at: string | null; chart_structured: string | null }[]>([])
  const [recordsLoading, setRecordsLoading] = useState(false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const csvInputRef = useRef<HTMLInputElement | null>(null)

  async function handleCsvImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await importPatientsFromCsv(file)
      alert(`가져오기 완료: ${result.inserted}명 등록, ${result.skipped}건 스킵`)
      getPatients().then(setPatients).catch(console.error)
    } catch {
      alert('CSV 가져오기에 실패했습니다.')
    } finally {
      e.target.value = ''
    }
  }

  useEffect(() => {
    getPatients().then(setPatients).catch(console.error)
  }, [])

  useEffect(() => {
    if (activeTab !== 'history' || !selectedPatient) return
    setRecordsLoading(true)
    getPatientRecords(selectedPatient.id)
      .then(data => setRecords(data.records))
      .catch(console.error)
      .finally(() => setRecordsLoading(false))
  }, [activeTab, selectedPatient])

  async function toggleRecording() {
    if (!isRecording) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = e => chunksRef.current.push(e.data)
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setAudioFile(new File([blob], 'recording.webm', { type: 'audio/webm' }))
      }
      recorder.start()
      mediaRef.current = recorder
      setIsRecording(true)
      setSeconds(0)
      timerRef.current = setInterval(() => setSeconds(s => s + 1), 1000)
    } else {
      mediaRef.current?.stop()
      setIsRecording(false)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }

  function mapDiagnosisResult(raw: Record<string, unknown>): DiagnosisResult {
    const r = raw as Record<string, Record<string, unknown>>
    const herb = r.herbal_prescription as Record<string, unknown> ?? {}
    const composition = (herb.composition as {herb:string;dosage:string}[] ?? [])
    return {
      id: '',
      patient_id: selectedPatient?.id ?? '',
      created_at: new Date().toISOString(),
      constitution: String(r.sasang_constitution?.type ?? '-'),
      diagnosis: String(r.tkm_diagnosis?.diagnosis_name ?? '-'),
      western_diagnosis: String((r.western_diagnosis as Record<string, unknown>)?.name ?? '-'),
      prescription: String(herb.name_kr ?? '-'),
      herbs: composition.map(c => `${c.herb} ${c.dosage}`),
      acupuncture: ((r.acupuncture_prescription as unknown) as {point_kr:string;point_code:string}[] ?? [])
        .map(p => `${p.point_kr}(${p.point_code})`),
    }
  }

  async function startAnalysis() {
    if (!selectedPatient) return alert('환자를 선택해주세요')
    if (!audioFile && !symptomText.trim()) return alert('녹음, 파일 업로드 또는 증상 입력 중 하나가 필요합니다')
    setLoading(true)
    try {
      if (audioFile) {
        const data = await uploadAndAnalyze(selectedPatient.id, audioFile)
        setResult(data)
      } else {
        const { result: raw } = await diagnoseText(symptomText.trim())
        setResult(mapDiagnosisResult(raw))
      }
      setActiveTab('result')
    } catch (e: any) {
      alert(e.message || '분석 실패')
    } finally {
      setLoading(false)
    }
  }

  async function handleAddPatient(e: React.FormEvent) {
    e.preventDefault()
    setAddLoading(true)
    try {
      await createPatient(newPatient)
      const updated = await getPatients()
      setPatients(updated)
      setShowAddModal(false)
      setNewPatient({ name: '', birth_date: '', gender: '', phone: '' })
    } catch (e: any) {
      alert(e.message)
    } finally {
      setAddLoading(false)
    }
  }

  async function handleAsk(e: { preventDefault: () => void }) {
    e.preventDefault()
    if (!askQuestion.trim() || askLoading) return
    const q = askQuestion.trim()
    setAskQuestion('')
    setAskLoading(true)
    try {
      let answer: string
      if (askMode === 'diagnose') {
        const { result } = await diagnoseText(q)
        const r = result as Record<string, Record<string, unknown>>
        const constitution = r.sasang_constitution?.type ?? '-'
        const diagnosis = r.tkm_diagnosis?.diagnosis_name ?? '-'
        const western = (r.western_diagnosis?.name ?? '-') as string
        const herb = r.herbal_prescription as Record<string, unknown>
        const herbName = herb?.name_kr ?? '-'
        const composition = (herb?.composition as {herb:string;dosage:string}[] ?? []).map(c=>`${c.herb} ${c.dosage}`).join(', ')
        const acu = ((r.acupuncture_prescription as unknown) as {point_kr:string;point_code:string}[] ?? []).map(p=>`${p.point_kr}(${p.point_code})`).join(', ')
        answer = `▶ 사상체질: ${constitution}\n▶ 한의학 진단: ${diagnosis}\n▶ 양방 진단: ${western}\n▶ 한약 처방: ${herbName}\n  ${composition}\n▶ 침 처방: ${acu}`
      } else {
        const res = await askDiagnosis(q)
        answer = res.answer
      }
      setAskHistory(prev => [...prev, { question: q, answer }])
    } catch {
      setAskHistory(prev => [...prev, { question: q, answer: '답변을 가져오지 못했습니다. 다시 시도해주세요.' }])
    } finally {
      setAskLoading(false)
    }
  }

  function copyAll() {
    if (!result || !selectedPatient) return
    const text = `[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient.name} / ${new Date().toLocaleDateString('ko-KR')}

▶ 사상체질
${result.constitution}

▶ 한의학적 진단
${result.diagnosis}
양방 대응: ${result.western_diagnosis}

▶ 한약 처방
${result.prescription}
${result.herbs?.join(', ')}

▶ 침 처방
${result.acupuncture?.join(', ')}

※ AI 참고용 / 최종 판단은 담당 한의사`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const timer = `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`
  const filtered = patients.filter(p => p.name.includes(search))

  return (
    <div className="flex h-[calc(100vh-52px)] overflow-hidden">

      {/* 왼쪽 환자 패널 */}
      <div className="hidden md:flex w-[260px] flex-shrink-0 bg-white border-r border-[#D4CCC4] flex-col">
        <div className="p-3 border-b border-[#D4CCC4]">
          <div className="text-xs font-medium text-[#232323] uppercase tracking-wide mb-2">환자 목록</div>
          <div className="flex items-center gap-2 bg-[#EDE8E2] border border-[#D4CCC4] rounded-md px-3 py-2">
            <span className="text-[#B0AAA4] text-sm">🔍</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="이름 검색..."
              className="flex-1 bg-transparent text-xs text-[#232323] outline-none"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <div className="text-xs text-[#B0AAA4] text-center py-8">등록된 환자가 없습니다</div>
          ) : (
            filtered.map(patient => (
              <div
                key={patient.id}
                onClick={() => { setSelectedPatient(patient); setActiveTab('record') }}
                className={`flex items-center gap-2.5 px-3.5 py-2.5 cursor-pointer transition-all border-l-[2.5px] ${
                  selectedPatient?.id === patient.id
                    ? 'bg-[#F5F2EE] border-l-[#EF6600]'
                    : 'border-l-transparent hover:bg-[#F5F2EE]'
                }`}
              >
                <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
                  {patient.name[0]}
                </div>
                <div>
                  <div className="text-sm font-medium text-[#232323]">{patient.name}</div>
                  <div className="text-xs text-[#8A8480]">{patient.gender || '-'}</div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="p-3 border-t border-[#D4CCC4] flex flex-col gap-2">
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleCsvImport}
          />
          <button
            onClick={() => csvInputRef.current?.click()}
            className="w-full border border-[#C8BFB6] rounded-md py-2 text-xs text-[#8A8480] hover:border-[#EF6600] hover:text-[#EF6600] transition-all flex items-center justify-center gap-1.5"
          >
            📥 환자 정보 가져오기
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="w-full bg-[#EF6600] text-white rounded-md py-2 text-xs flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            + 신규 환자 등록
          </button>
        </div>
      </div>

      {/* 오른쪽 메인 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex border-b border-[#D4CCC4] bg-white flex-shrink-0">
          {(['record','result','history','ask'] as const).map((tab, i) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3.5 text-xs transition-all border-b-2 ${
                activeTab === tab
                  ? 'text-[#EF6600] border-[#EF6600]'
                  : 'text-[#8A8480] border-transparent hover:text-[#232323]'
              }`}
            >
              {['진료 녹음','진단 결과','진료 이력','한의학 검색'][i]}
            </button>
          ))}
        </div>

        <div className={`flex-1 p-5 ${activeTab === 'ask' ? 'overflow-hidden flex flex-col' : 'overflow-y-auto'}`}>
          {selectedPatient && (
            <div className="flex items-center gap-3 p-3 bg-white border border-[#D4CCC4] rounded-lg mb-4">
              <div className="w-10 h-10 rounded-full bg-[#68413E] flex items-center justify-center text-sm font-medium text-white flex-shrink-0">
                {selectedPatient.name[0]}
              </div>
              <div>
                <div className="text-sm font-medium text-[#232323]">{selectedPatient.name}</div>
                <div className="text-xs text-[#8A8480]">{selectedPatient.gender || '-'}</div>
              </div>
              <div className="ml-auto flex gap-2">
                <button onClick={() => setActiveTab('record')} className="bg-[#EF6600] text-white text-xs px-3 py-1.5 rounded-md hover:opacity-90">🎙 녹음</button>
                <button onClick={() => setActiveTab('history')} className="border border-[#C8BFB6] text-xs px-3 py-1.5 rounded-md text-[#8A8480] hover:border-[#232323] hover:text-[#232323] transition-all">이력 보기</button>
              </div>
            </div>
          )}

          {!selectedPatient && activeTab !== 'ask' && (
            <div className="text-sm text-[#B0AAA4] text-center py-16">
              왼쪽에서 환자를 선택해주세요
            </div>
          )}

          {/* 진료 녹음 탭 */}
          {activeTab === 'record' && selectedPatient && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">음성 녹음</div>
                <div className="text-center p-6 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg mb-3">
                  <button
                    onClick={toggleRecording}
                    className={`w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3 transition-all ${
                      isRecording ? 'bg-[#68413E] animate-pulse' : 'bg-[#EF6600] hover:scale-105'
                    }`}
                  >
                    <span className="text-white text-xl">{isRecording ? '⏹' : '🎙'}</span>
                  </button>
                  <div className="text-sm font-medium text-[#232323] mb-1">
                    {isRecording ? '녹음 중...' : audioFile ? '녹음 완료' : '녹음 시작'}
                  </div>
                  {isRecording && (
                    <div className="flex items-center justify-center gap-1 h-6 my-2">
                      {[10,18,24,16,22,14,20].map((h,i) => (
                        <div key={i} className="w-[3px] rounded-sm bg-[#989689] animate-bounce" style={{ height: h, animationDelay: `${i*0.1}s` }} />
                      ))}
                    </div>
                  )}
                  <div className="text-lg font-light text-[#232323] tabular-nums">{timer}</div>
                  <div className="text-xs text-[#8A8480] mt-1">
                    {isRecording ? '버튼을 눌러 중지하세요' : '버튼을 눌러 녹음을 시작하세요'}
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">파일 업로드</div>
                  <label className="border-[1.5px] border-dashed border-[#C8BFB6] rounded-lg p-5 text-center cursor-pointer hover:border-[#EF6600] transition-all bg-[#EDE8E2] block">
                    <div className="text-2xl mb-2">📂</div>
                    <div className="text-xs text-[#8A8480]">{audioFile ? audioFile.name : '파일을 드래그하거나 클릭'}</div>
                    <div className="text-xs text-[#B0AAA4] mt-1">mp3, wav, m4a · 최대 100MB</div>
                    <input type="file" accept=".mp3,.wav,.m4a,.webm" className="hidden" onChange={e => e.target.files && setAudioFile(e.target.files[0])} />
                  </label>
                </div>
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">추가 메모</div>
                  <textarea
                    value={memo}
                    onChange={e => setMemo(e.target.value)}
                    placeholder="주요 증상, 특이사항...&#10;예) 소화불량 3개월, 스트레스"
                    className="w-full bg-[#EDE8E2] border border-[#D4CCC4] rounded-md p-3 text-xs text-[#232323] outline-none focus:border-[#EF6600] resize-none min-h-[80px] transition-colors"
                  />
                </div>
              </div>
              <div className="md:col-span-2">
                <div className="bg-white border border-[#D4CCC4] rounded-lg p-5">
                  <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-3">증상 직접 입력 <span className="normal-case text-[#B0AAA4]">(음성 없이 텍스트로 분석)</span></div>
                  <textarea
                    value={symptomText}
                    onChange={e => setSymptomText(e.target.value)}
                    placeholder="증상을 자세히 입력하세요&#10;예) 손발이 차고 식은땀이 나며 소화가 잘 안 됨. 평소 피로감이 많고 추위를 탐."
                    className="w-full bg-[#EDE8E2] border border-[#D4CCC4] rounded-md p-3 text-xs text-[#232323] outline-none focus:border-[#EF6600] resize-none min-h-[90px] transition-colors"
                    disabled={!!audioFile}
                  />
                  {audioFile && (
                    <div className="text-xs text-[#B0AAA4] mt-1">음성 파일이 있으면 텍스트 입력은 무시됩니다.</div>
                  )}
                </div>
              </div>
              <div className="md:col-span-2">
                <button
                  onClick={startAnalysis}
                  disabled={loading || (!audioFile && !symptomText.trim())}
                  className="w-full bg-[#EF6600] text-white rounded-md py-3.5 text-sm font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {loading ? '분석 중...' : '✨ AI 진단 분석 시작'}
                </button>
              </div>
            </div>
          )}

          {/* 진단 결과 탭 */}
          {activeTab === 'result' && (
            <div>
              {!result ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">아직 진단 결과가 없습니다.</div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {[
                      { label: '사상체질', icon: '👤', value: result.constitution },
                      { label: '한의학적 진단', icon: '🩺', value: result.diagnosis, sub: `양방: ${result.western_diagnosis}` },
                      { label: '한약 처방', icon: '🌿', value: result.prescription, tags: result.herbs },
                      { label: '침 처방', icon: '📍', value: result.acupuncture?.join(' · ') },
                    ].map((card, i) => (
                      <div key={i} className="bg-white border border-[#D4CCC4] rounded-lg p-4 relative">
                        <button
                          onClick={() => navigator.clipboard.writeText(`${card.label}: ${card.value}`)}
                          className="absolute top-3 right-3 bg-[#EDE8E2] border border-[#D4CCC4] rounded-md px-2 py-1 text-xs text-[#8A8480] hover:border-[#EF6600] hover:text-[#EF6600] transition-all"
                        >
                          📋 복사
                        </button>
                        <div className="text-xs text-[#8A8480] uppercase tracking-wide mb-2">{card.icon} {card.label}</div>
                        <div className="text-sm font-medium text-[#232323]">{card.value}</div>
                        {card.sub && <div className="text-xs text-[#8A8480] mt-1">{card.sub}</div>}
                        {card.tags && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {card.tags.map((t,i) => (
                              <span key={i} className="px-2 py-0.5 bg-[#EDE8E2] border border-[#D4CCC4] rounded text-xs text-[#585753]">{t}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="bg-[#232323] rounded-lg p-5 mt-4 relative">
                    <div className="text-xs text-[#A09892] uppercase tracking-wide mb-3">📋 동의보감 차팅용 전체 복사</div>
                    <button
                      onClick={copyAll}
                      className={`absolute top-4 right-4 text-xs px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all ${
                        copied ? 'bg-green-600 text-white' : 'bg-[#EF6600] text-white hover:opacity-90'
                      }`}
                    >
                      {copied ? '✓ 복사 완료!' : '📋 전체 복사'}
                    </button>
                    <pre className="text-xs text-white/70 leading-relaxed whitespace-pre-wrap font-sans mt-6">
{`[AI 한의 진단 보조 — Zinmac]
환자: ${selectedPatient?.name} / ${new Date().toLocaleDateString('ko-KR')}

▶ 사상체질
${result.constitution}

▶ 한의학적 진단
${result.diagnosis}
양방: ${result.western_diagnosis}

▶ 한약 처방
${result.prescription}
${result.herbs?.join(', ')}

▶ 침 처방
${result.acupuncture?.join(', ')}

※ AI 참고용 / 최종 판단은 담당 한의사`}
                    </pre>
                  </div>
                  <div className="text-xs text-[#B0AAA4] mt-3 p-3 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg">
                    ⚠️ 본 결과는 AI 참고용이며 최종 진단 및 처방은 반드시 한의사가 직접 판단해야 합니다.
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button className="flex-1 bg-[#EF6600] text-white rounded-md py-2.5 text-xs flex items-center justify-center gap-1.5 hover:opacity-90">💾 저장</button>
                    <button className="flex-1 border border-[#C8BFB6] rounded-md py-2.5 text-xs text-[#8A8480] hover:border-[#232323] transition-all flex items-center justify-center">🖨 인쇄</button>
                    <button onClick={() => setActiveTab('record')} className="flex-1 border border-[#C8BFB6] rounded-md py-2.5 text-xs text-[#8A8480] hover:border-[#232323] transition-all flex items-center justify-center">+ 새 진료</button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* 진료 이력 탭 */}
          {activeTab === 'history' && (
            <div className="overflow-y-auto">
              {!selectedPatient ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">환자를 선택해주세요</div>
              ) : recordsLoading ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">불러오는 중...</div>
              ) : records.length === 0 ? (
                <div className="text-sm text-[#B0AAA4] text-center py-12">진료 이력이 없습니다</div>
              ) : (
                <div className="flex flex-col gap-3">
                  {records.map(r => (
                    <div key={r.id} className="bg-white border border-[#D4CCC4] rounded-lg p-4">
                      <div className="text-xs text-[#8A8480] mb-2">
                        {r.recorded_at ? new Date(r.recorded_at).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) : '날짜 미상'}
                      </div>
                      <div className="text-sm text-[#232323] whitespace-pre-wrap line-clamp-4">
                        {r.chart_structured || '차트 내용 없음'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 한의학 검색 탭 */}
          {activeTab === 'ask' && (
            <div className="flex flex-col flex-1 min-h-0 gap-4">
              <div className="flex-1 flex flex-col gap-3 overflow-y-auto min-h-0">
                {askHistory.length === 0 && (
                  <div className="text-center py-16 text-[#B0AAA4]">
                    <div className="text-2xl mb-3">💬</div>
                    <div className="text-sm">한의학 관련 궁금한 점을 질문해보세요</div>
                    <div className="text-xs mt-2 text-[#C8BFB6]">예) 소음인 소화불량에 어떤 처방이 좋나요?</div>
                  </div>
                )}
                {askHistory.map((item, i) => (
                  <div key={i} className="flex flex-col gap-2">
                    <div className="self-end max-w-[75%] bg-[#EF6600] text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5">
                      {item.question}
                    </div>
                    <div className="self-start max-w-[75%] bg-white border border-[#D4CCC4] text-sm text-[#232323] rounded-2xl rounded-tl-sm px-4 py-2.5 leading-relaxed whitespace-pre-wrap">
                      {item.answer}
                    </div>
                  </div>
                ))}
                {askLoading && (
                  <div className="self-start bg-white border border-[#D4CCC4] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                    {[0,1,2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 bg-[#B0AAA4] rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                )}
              </div>
              <div className="pt-2 border-t border-[#D4CCC4] flex flex-col gap-2">
                <div className="flex gap-1 p-1 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg w-fit">
                  <button
                    type="button"
                    onClick={() => setAskMode('ask')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === 'ask'
                        ? 'bg-white text-[#232323] shadow-sm'
                        : 'text-[#8A8480] hover:text-[#232323]'
                    }`}
                  >
                    💬 질문하기
                  </button>
                  <button
                    type="button"
                    onClick={() => setAskMode('diagnose')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      askMode === 'diagnose'
                        ? 'bg-white text-[#232323] shadow-sm'
                        : 'text-[#8A8480] hover:text-[#232323]'
                    }`}
                  >
                    🩺 증상 분석
                  </button>
                </div>
                <form onSubmit={handleAsk} className="flex gap-2">
                  <input
                    value={askQuestion}
                    onChange={e => setAskQuestion(e.target.value)}
                    placeholder={askMode === 'diagnose' ? '증상을 입력하면 진단·처방을 분석합니다...' : '한의학 관련 질문을 입력하세요...'}
                    className="flex-1 bg-[#EDE8E2] border border-[#D4CCC4] rounded-lg px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                    disabled={askLoading}
                  />
                  <button
                    type="submit"
                    disabled={askLoading || !askQuestion.trim()}
                    className="bg-[#EF6600] text-white px-4 py-2.5 rounded-lg text-sm disabled:opacity-40 hover:opacity-90 transition-opacity"
                  >
                    전송
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 신규 환자 등록 모달 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-[#232323]/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-[400px] overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#D4CCC4]">
              <div className="text-sm font-medium text-[#232323]">신규 환자 등록</div>
              <button onClick={() => setShowAddModal(false)} className="text-[#8A8480] text-xl">✕</button>
            </div>
            <form onSubmit={handleAddPatient} className="p-5 flex flex-col gap-3">
              {[
                { label: '이름 *', key: 'name', type: 'text', placeholder: '환자 이름' },
                { label: '생년월일', key: 'birth_date', type: 'date', placeholder: '' },
                { label: '전화번호', key: 'phone', type: 'tel', placeholder: '010-0000-0000' },
              ].map(field => (
                <div key={field.key}>
                  <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">{field.label}</label>
                  <input
                    type={field.type}
                    placeholder={field.placeholder}
                    value={newPatient[field.key as keyof typeof newPatient]}
                    onChange={e => setNewPatient({ ...newPatient, [field.key]: e.target.value })}
                    className="w-full bg-[#F5F2EE] border border-[#D4CCC4] rounded-md px-4 py-2.5 text-sm text-[#232323] outline-none focus:border-[#EF6600] transition-colors"
                    required={field.key === 'name'}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs text-[#8A8480] uppercase tracking-wide mb-1.5">성별</label>
                <div className="flex gap-2">
                  {['남성', '여성'].map(g => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setNewPatient({ ...newPatient, gender: g })}
                      className={`flex-1 py-2.5 text-sm rounded-md border transition-all ${
                        newPatient.gender === g
                          ? 'bg-[#EF6600] text-white border-[#EF6600]'
                          : 'bg-white text-[#8A8480] border-[#D4CCC4] hover:border-[#EF6600]'
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <button
                type="submit"
                disabled={addLoading}
                className="w-full bg-[#EF6600] text-white rounded-md py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 mt-2"
              >
                {addLoading ? '등록 중...' : '등록 완료'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 로딩 오버레이 */}
      {loading && (
        <div className="fixed inset-0 bg-[#232323]/60 z-50 flex flex-col items-center justify-center gap-4">
          <div className="w-9 h-9 border-2 border-white/20 border-t-[#EF6600] rounded-full animate-spin" />
          <div className="text-sm text-white/80">AI가 진료 내용을 분석하고 있습니다...</div>
        </div>
      )}
    </div>
  )
}