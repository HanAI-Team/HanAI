"use client";
import { publicAskStream } from "@/lib/api/diagnosis";
import { MessageCircle } from "lucide-react";
import { useState } from "react";

interface AskItem {
  question: string;
  answer: string;
}

export default function PublicSearchPage() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AskItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  function appendToLast(chunk: string) {
    setHistory((prev) =>
      prev.map((item, i) =>
        i === prev.length - 1 ? { ...item, answer: item.answer + chunk } : item,
      ),
    );
  }

  async function handleSubmit(e: { preventDefault: () => void }) {
    e.preventDefault();
    if (!question.trim() || isStreaming) return;
    const q = question.trim();
    setQuestion("");
    setHistory((prev) => [...prev, { question: q, answer: "" }]);
    setIsStreaming(true);

    try {
      await publicAskStream(q, appendToLast);
    } catch {
      appendToLast("답변을 가져오지 못했습니다. 다시 시도해주세요.");
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <div className="h-[52px] bg-[#232323] flex items-center px-6 flex-shrink-0">
        <div className="text-[19px] text-white">Zinmac 한의학 검색</div>
      </div>

      <div className="bg-[#FFF3CD] text-[#856404] text-xs text-center py-2 px-4 flex-shrink-0">
        ⚠️ 이 페이지는 Chrome 또는 Edge 브라우저에서 이용해주세요. (Internet Explorer 미지원)
      </div>

      <div className="flex-1 flex flex-col max-w-2xl w-full mx-auto p-5 gap-4 min-h-0">
        <div className="flex-1 flex flex-col gap-3 overflow-y-auto min-h-0">
          {history.length === 0 && (
            <div className="text-center py-16 text-muted">
              <MessageCircle className="w-8 h-8 mx-auto mb-3 text-muted" />
              <div className="text-sm">한의학 관련 궁금한 점을 질문해보세요</div>
              <div className="text-xs mt-2 text-[#C8BFB6]">
                예) 소음인 소화불량에 어떤 처방이 좋나요?
              </div>
            </div>
          )}
          {history.map((item, i) => (
            <div key={i} className="flex flex-col gap-2">
              <div className="self-end max-w-[75%] bg-[#EF6600] text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5">
                {item.question}
              </div>
              {item.answer === "" ? (
                <div className="self-start bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                  {[0, 1, 2].map((j) => (
                    <div
                      key={j}
                      className="w-1.5 h-1.5 bg-[#B0AAA4] rounded-full animate-bounce"
                      style={{ animationDelay: `${j * 0.15}s` }}
                    />
                  ))}
                </div>
              ) : (
                <div className="self-start max-w-[75%] bg-card border border-border text-sm text-text rounded-2xl rounded-tl-sm px-4 py-2.5 leading-relaxed whitespace-pre-wrap">
                  {item.answer}
                </div>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="pt-2 border-t border-border flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="한의학 관련 질문을 입력하세요..."
            className="flex-1 bg-card border border-border rounded-lg px-4 py-2.5 text-sm text-text outline-none focus:border-[#EF6600] transition-colors"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={isStreaming || !question.trim()}
            className="bg-[#EF6600] text-white px-4 py-2.5 rounded-lg text-sm disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            전송
          </button>
        </form>
      </div>
    </div>
  );
}
