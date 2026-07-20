import PublicNav from "@/components/PublicNav";

const ARTICLES = [
  {
    title: "제1조 (목적)",
    body: (
      <p className="text-subtext leading-relaxed">
        이 약관은 진맥(이하 &ldquo;회사&rdquo;)이 제공하는 Zinmac 서비스(이하 &ldquo;서비스&rdquo;)의 이용과
        관련하여 회사와 이용자 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로
        합니다.
      </p>
    ),
  },
  {
    title: "제2조 (정의)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>
          <span className="text-text font-medium">서비스</span>: 회사가 제공하는 AI 진료 보조 및
          HIRA 청구 SaaS를 말합니다.
        </li>
        <li>
          <span className="text-text font-medium">이용자</span>: 이 약관에 따라 서비스에 가입한
          한의원 및 한의사를 말합니다.
        </li>
        <li>
          <span className="text-text font-medium">구독</span>: 월간 또는 연간 정기 결제 방식으로
          서비스를 이용할 수 있는 권리를 말합니다.
        </li>
      </ul>
    ),
  },
  {
    title: "제3조 (서비스 이용계약)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>이용계약은 이용자가 회사가 정한 절차에 따라 이용신청을 하고, 회사가 이를 승낙함으로써 성립합니다.</li>
        <li>만 19세 이상의 사업자만 회원으로 가입할 수 있습니다.</li>
        <li>서비스는 한의사 면허를 보유한 자를 대상으로 제공됩니다.</li>
      </ul>
    ),
  },
  {
    title: "제4조 (서비스 제공 및 변경)",
    body: (
      <div className="text-subtext leading-relaxed space-y-3">
        <div>
          <p>회사는 다음 각 호의 서비스를 제공합니다.</p>
          <ul className="list-disc list-inside space-y-1 mt-1">
            <li>STT(음성인식) 기반 오토차팅</li>
            <li>AI 진료 기록 보조</li>
            <li>HIRA(건강보험심사평가원) 청구 파일 생성</li>
          </ul>
        </div>
        <p>
          회사는 운영상, 기술상 필요에 따라 서비스의 내용을 변경하거나 전부 또는 일부를 중단할 수
          있으며, 이 경우 사전에 이용자에게 고지합니다.
        </p>
      </div>
    ),
  },
  {
    title: "제5조 (이용요금)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>베이직 플랜: 베타 기간 중 월 39,000원, 정식 출시 이후 월 79,000원</li>
        <li>프리미엄 플랜: 베타 기간 중 월 99,000원, 정식 출시 이후 월 159,000원</li>
        <li>연간 결제를 선택하는 경우 월간 결제 대비 약 17% 할인된 금액이 적용됩니다.</li>
        <li>베타 기간 중 가입한 이용자(이하 &ldquo;베타 참여자&rdquo;)는 가입일로부터 2년간 베타 기간의 이용요금이 고정 적용됩니다.</li>
      </ul>
    ),
  },
  {
    title: "제6조 (환불 정책)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>월간 구독: 결제 당일 서비스를 이용하지 않은 경우 전액 환불하며, 서비스 이용을 개시한 이후에는 환불하지 않습니다.</li>
        <li>
          연간 구독: 결제일로부터 7일 이내에 서비스를 이용하지 않은 경우 전액 환불합니다. 이 기간이
          지나 중도 해지하는 경우, 이용한 기간에 대해 월간 정상요금을 기준으로 재계산한 금액을
          공제한 후 잔여기간에 해당하는 금액을 환불합니다.
        </li>
        <li>베타 참여자는 위 각 호에도 불구하고 언제든지 잔여기간에 해당하는 금액을 전액 환불받을 수 있습니다.</li>
        <li>
          이용자가 결제와 동시에 서비스 이용이 개시됨에 동의한 경우, 전자상거래 등에서의
          소비자보호에 관한 법률 제17조에 따라 청약철회가 제한될 수 있습니다.
        </li>
      </ul>
    ),
  },
  {
    title: "제7조 (개인정보 보호)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>회사는 관련 법령에 따라 이용자의 개인정보를 보호하며, 자세한 사항은 별도로 정하는 개인정보처리방침에 따릅니다.</li>
        <li>환자의 진료기록 등 민감정보는 의료법에 따라 암호화하여 저장합니다.</li>
      </ul>
    ),
  },
  {
    title: "제8조 (면책조항)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>
          서비스가 제공하는 AI 분석 참고자료는 참고용 정보이며, 의료법상 의료행위를 대체하지
          않습니다. 최종 진단 및 처방에 대한 판단과 책임은 이용자인 한의사에게 있습니다.
        </li>
        <li>회사는 천재지변, 시스템 장애 등 회사의 귀책사유 없는 불가항력으로 인하여 서비스를 제공할 수 없는 경우 이에 대한 책임을 지지 않습니다.</li>
      </ul>
    ),
  },
  {
    title: "제9조 (분쟁해결)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>이 약관과 관련하여 회사와 이용자 간에 발생한 분쟁에는 대한민국 법률을 적용합니다.</li>
        <li>회사와 이용자 간 발생한 분쟁에 관한 소송은 서울중앙지방법원을 관할 법원으로 합니다.</li>
      </ul>
    ),
  },
];

const TermsPage = () => {
  return (
    <div className="bg-bg min-h-screen">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-text mb-2">Zinmac 서비스 이용약관</h1>
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

export default TermsPage;
