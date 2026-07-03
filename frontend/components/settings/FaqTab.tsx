'use client'
import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

const FAQ_LIST = [
  {
    question: "Basic과 Premium의 차이점은 무엇인가요?",
    answer: "Basic은 월 50건 청구 제한, 직원 계정 1개가 포함됩니다. Premium은 청구 건수 무제한, 직원 계정 무제한, 데이터 내보내기(CSV) 기능이 추가로 제공됩니다."
  },
  {
    question: "STT 오토차팅은 어떤 플랜에서 사용할 수 있나요?",
    answer: "Basic, Premium 모두 STT 오토차팅과 AI 진단 보조 기능을 사용할 수 있습니다."
  },
  {
    question: "HIRA 청구 파일 생성은 어떤 플랜에서 가능한가요?",
    answer: "모든 플랜에서 청구 파일(C2 전산매체) 생성이 가능합니다. Basic은 월 50건까지 청구할 수 있습니다."
  },
  {
    question: "환자 데이터는 안전하게 보호되나요?",
    answer: "주민등록번호 등 민감 개인정보는 AES-256-GCM으로 암호화 저장됩니다. 국내 서버(AWS 서울 리전)에 보관하며 의료법 및 개인정보보호법을 준수합니다."
  },
  {
    question: "직원 계정은 몇 명까지 등록할 수 있나요?",
    answer: "Basic은 직원 계정 1개, Premium은 무제한으로 등록 가능합니다."
  },
  {
    question: "멤버십은 언제든지 변경할 수 있나요?",
    answer: "네, 언제든지 Basic ↔ Premium 변경이 가능합니다."
  },
  {
    question: "베타 기간 중 요금은 어떻게 되나요?",
    answer: "베타 기간 중에는 무료로 이용 가능합니다. 정식 출시 시 요금제가 적용됩니다."
  },
  {
    question: "결제는 어떻게 진행되나요?",
    answer: "토스페이먼츠를 통해 신용카드, 계좌이체 등 다양한 결제 수단을 지원하며 월 단위 자동 결제됩니다."
  },
]

export default function FaqTab() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const toggleFaq = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <div className="flex justify-center items-start min-h-[calc(100vh-180px)] pt-6">
      <div className="w-full max-w-[720px]">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-medium text-text">자주 묻는 질문</h2>
        </div>

        <div className="space-y-3">
          {FAQ_LIST.map((faq, index) => {
            const isOpen = openIndex === index
            return (
              <div 
                key={index} 
                className="bg-card border border-border rounded-2xl overflow-hidden "
              >
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full px-6 py-5 flex cursor-pointer justify-between items-center hover:bg-[#EF6600] transition-colors text-left group"
                >
                  <span className="font-medium text-text pr-6 text-[15px]">
                    {faq.question}
                  </span>
                  <div className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}>
                    {isOpen ? 
                      <ChevronUp className="w-5 h-5 text-[#EF6600]" /> : 
                      <ChevronDown className="w-5 h-5 text-subtext group-hover:text-text" />
                    }
                  </div>
                </button>
                
                {isOpen && (
                  <div className="px-6 py-6 text-subtext leading-relaxed border-t border-border">
                    {faq.answer}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}