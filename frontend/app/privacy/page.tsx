import PublicNav from "@/components/PublicNav";

const ARTICLES = [
  {
    title: "제1조 (수집하는 개인정보 항목)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>
          <span className="text-text font-medium">필수 항목</span>: 이름, 한의사 면허번호,
          생년월일, 연락처, 이메일
        </li>
        <li>
          <span className="text-text font-medium">서비스 이용 중 생성되는 항목</span>: 환자
          진료기록, 음성 녹음 파일, AI 진단 결과, HIRA 청구 데이터
        </li>
        <li>
          <span className="text-text font-medium">자동 수집 항목</span>: 접속 IP, 브라우저 정보,
          이용 로그
        </li>
      </ul>
    ),
  },
  {
    title: "제2조 (개인정보 수집 및 이용 목적)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>한의사 면허 인증 및 서비스 가입</li>
        <li>AI 진단 보조 및 오토차팅 서비스 제공</li>
        <li>HIRA 청구 파일 생성</li>
        <li>고객 지원 및 서비스 개선</li>
      </ul>
    ),
  },
  {
    title: "제3조 (개인정보 보유 및 이용 기간)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>회원 탈퇴 시 즉시 파기합니다. 다만 관련 법령에 따라 보존이 필요한 경우는 예외로 합니다.</li>
        <li>진료기록: 의료법에 따라 10년간 보관합니다.</li>
        <li>전자상거래 기록: 전자상거래법에 따라 5년간 보관합니다.</li>
        <li>접속 로그: 통신비밀보호법에 따라 3개월간 보관합니다.</li>
      </ul>
    ),
  },
  {
    title: "제4조 (개인정보의 제3자 제공)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>회사는 이용자의 개인정보를 원칙적으로 제3자에게 제공하지 않습니다.</li>
        <li>다만 이용자가 사전에 동의한 경우 또는 법령의 규정에 의한 경우에는 예외로 합니다.</li>
      </ul>
    ),
  },
  {
    title: "제5조 (개인정보 처리 위탁)",
    body: (
      <div className="text-subtext leading-relaxed space-y-3">
        <div>
          <p>회사는 서비스 제공을 위해 다음과 같이 개인정보 처리업무를 위탁하고 있습니다.</p>
          <ul className="list-disc list-inside space-y-1 mt-1">
            <li>Clova Speech (네이버클라우드): STT 음성인식 처리</li>
            <li>Anthropic: AI 진단 보조 처리</li>
            <li>Supabase: 데이터베이스 저장</li>
          </ul>
        </div>
        <p>회사는 위탁계약 체결 시 개인정보 보호 관련 법령 준수, 개인정보에 대한 안전성 확보 등을 명시한 계약을 체결합니다.</p>
      </div>
    ),
  },
  {
    title: "제6조 (개인정보 보호 조치)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>주민등록번호 등 민감정보는 AES-256-GCM 방식으로 암호화하여 저장합니다.</li>
        <li>비밀번호는 bcrypt 방식으로 암호화하여 저장합니다.</li>
        <li>JWT 기반 접근 제어를 통해 인가되지 않은 접근을 차단합니다.</li>
        <li>개인정보에 대한 접근 로그를 관리합니다.</li>
      </ul>
    ),
  },
  {
    title: "제7조 (이용자의 권리)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>이용자는 언제든지 자신의 개인정보에 대한 열람, 정정, 삭제, 처리정지를 요청할 수 있습니다.</li>
        <li>문의: sst@zinmac.kr </li>
      </ul>
    ),
  },
  {
    title: "제8조 (개인정보 보호책임자)",
    body: (
      <ul className="list-disc list-inside text-subtext leading-relaxed space-y-1">
        <li>성명: 이승희</li>
        <li>이메일: sst@zinmac.kr </li>
      </ul>
    ),
  },
];

const PrivacyPage = () => {
  return (
    <div className="bg-bg min-h-screen">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-text mb-2">Zinmac 개인정보처리방침</h1>
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

export default PrivacyPage;
