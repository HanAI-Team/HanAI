import PublicNav from "@/components/PublicNav";

const ARTICLES = [
  {
    title: "1. 법적 근거",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>전자상거래 등에서의 소비자보호에 관한 법률 제17조에 따라, 온라인 계약은 원칙적으로 계약 체결일로부터 7일 이내 청약철회가 가능합니다.</li>
        <li>다만 결제 시 &ldquo;결제 즉시 서비스 이용 개시에 동의합니다&rdquo;에 명시적으로 동의한 경우, 관련 법령에 따라 청약철회가 제한될 수 있습니다.</li>
      </ul>
    ),
  },
  {
    title: "2. 월간 플랜 환불 정책",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>결제 당일, 서비스를 이용하지 않은 경우: 전액 환불</li>
        <li>첫 결제 후 7일 이내이며 실제 사용 이력이 없는 경우: 전액 환불</li>
        <li>결제 후 사용 중인 경우(7일 경과 또는 사용 이력이 있는 경우): 환불 불가하며, 자동갱신 취소만 가능합니다.</li>
      </ul>
    ),
  },
  {
    title: "3. 연간 플랜 환불 정책",
    body: (
      <div className="text-subtext leading-relaxed space-y-3">
        <ul className="list-disc list-inside space-y-1">
          <li>결제 후 7일 이내, 미사용 시: 전액 환불</li>
          <li>
            중도 해지 시: 연간 할인 혜택을 취소하고, 실사용 개월 수 × 정상 월요금으로 재계산한
            금액을 연간 결제 금액에서 공제한 후 잔여 금액을 환불합니다.
          </li>
        </ul>
        <p className="text-xs">
          예시: 프리미엄 연간(986,400원) 결제 후 4개월 사용 후 해지하는 경우 — 4개월 × 99,000원 =
          396,000원을 공제하고, 환불액은 986,400원 − 396,000원 = 590,400원입니다.
        </p>
      </div>
    ),
  },
  {
    title: "4. 베타 참여자 특례",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>베타 가격으로 가입한 참여자는 언제든지 중도 해지 시 잔여기간에 해당하는 금액을 전액 환불받을 수 있습니다.</li>
        <li>위약금은 부과되지 않습니다.</li>
      </ul>
    ),
  },
  {
    title: "5. 환불 신청 방법",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>이메일: sst@zinmac.kr</li>
        <li>처리 기간: 영업일 기준 3~5일</li>
        <li>환불은 카드 결제 취소 방식으로 처리됩니다.</li>
      </ul>
    ),
  },
  {
    title: "6. 환불 불가 항목",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>이미 사용된 STT 오토차팅, AI 진단, HIRA 청구 건은 환불 대상에서 제외됩니다.</li>
        <li>자동갱신 취소 후에도 만료일까지는 서비스를 계속 이용할 수 있습니다.</li>
      </ul>
    ),
  },
];

const RefundPage = () => {
  return (
    <div className="bg-bg min-h-screen">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-text mb-2">Zinmac 환불 정책</h1>
        <p className="text-sm text-subtext mb-10">시행일: 2026년 7월 8일</p>

        {ARTICLES.map((article) => (
          <section key={article.title} className="mb-8">
            <h2 className="font-semibold text-text mb-2">{article.title}</h2>
            {article.body}
          </section>
        ))}
      </div>
    </div>
  );
};

export default RefundPage;
