"use client";
import { useState, FormEvent } from "react";
import PublicNav from "@/components/PublicNav";

const INQUIRY_TYPES = ["도입 문의", "가격 문의", "기술 지원", "기타"];

const INITIAL_FORM = {
  hospitalName: "",
  contactName: "",
  phone: "",
  email: "",
  inquiryType: "",
  message: "",
};

const inputClass =
  "w-full bg-bg border border-border rounded-xl px-4 py-3 text-text outline-none focus:border-[#EF6600] transition-colors";
const labelClass = "text-sm font-medium text-text mb-1 block";

const ContactPage = () => {
  const [form, setForm] = useState(INITIAL_FORM);
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (field: keyof typeof INITIAL_FORM) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setForm(INITIAL_FORM);
  };

  return (
    <div className="bg-bg min-h-screen">
      <PublicNav />
      <div className="max-w-2xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-text mb-2">도입 문의</h1>
        <p className="text-subtext mb-10">
          Zinmac 도입이 궁금하신가요? 아래 양식으로 문의해 주세요.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>
              병원명 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={form.hospitalName}
              onChange={handleChange("hospitalName")}
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>
              담당자 이름 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={form.contactName}
              onChange={handleChange("contactName")}
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>
              연락처 <span className="text-red-400">*</span>
            </label>
            <input
              type="tel"
              required
              value={form.phone}
              onChange={handleChange("phone")}
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>
              이메일 <span className="text-red-400">*</span>
            </label>
            <input
              type="email"
              required
              value={form.email}
              onChange={handleChange("email")}
              className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>문의 유형</label>
            <select value={form.inquiryType} onChange={handleChange("inquiryType")} className={inputClass}>
              <option value="">선택해 주세요</option>
              {INQUIRY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass}>
              문의 내용 <span className="text-red-400">*</span>
            </label>
            <textarea
              required
              rows={4}
              value={form.message}
              onChange={handleChange("message")}
              className={inputClass}
            />
          </div>

          <button
            type="submit"
            className="w-full bg-[#EF6600] hover:opacity-90 text-white py-3 rounded-xl font-medium transition-all"
          >
            문의 보내기
          </button>

          {submitted && (
            <div className="bg-fill border border-border rounded-xl px-4 py-3 text-sm text-text text-center">
              문의가 접수되었습니다. 영업일 기준 1~2일 내 답변드리겠습니다.
            </div>
          )}
        </form>

        <hr className="border-border my-10" />

        <section>
          <h2 className="font-semibold text-text mb-2">직접 연락하기</h2>
          <p className="text-subtext leading-relaxed">이메일: sst@zinmac.kr</p>
          <p className="text-subtext leading-relaxed">운영시간: 평일 09:00 ~ 18:00 (주말·공휴일 제외)</p>
        </section>
      </div>
    </div>
  );
};

export default ContactPage;
