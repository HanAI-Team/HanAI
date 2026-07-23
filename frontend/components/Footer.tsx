import Image from "next/image";
import Link from "next/link";

const LINE_1 = [
  "상호명: (주)비와이진 | © 2026 BYzin",
  "대표자: 이승희",
  "사업자등록번호: 2818703849",
  "사업장 주소: 서울특별시 관악구 남부순환로198길7,101동 111호",
];



const LINE_2 = [
  "전화번호: 01068187518",
  "통신판매업 신고번호: 2026-서울관악-1380",
  "이메일: sst@zinmac.kr",
  "개인정보관리책임자: 이승희",
];

const FooterLine = ({ items }: { items: string[] }) => (
  <div className="text-center sm:text-left text-xs text-muted leading-relaxed sm:leading-normal">
    {items.map((item, i) => (
      <span key={item} className="block sm:inline sm:whitespace-nowrap">
        {item}
        <span className="hidden sm:inline">{i < items.length - 1 && " · "}</span>
      </span>
    ))}
  </div>
);

const Footer = () => {
  return (
    <footer className="border-t border-border bg-fill px-6 pt-6 pb-16 sm:py-6 md:px-12 flex-shrink-0">
      <div className="max-w-5xl mx-auto space-y-1">
        <div className="flex justify-center sm:justify-start mb-3">
          <Link href="/" className="inline-flex items-center gap-2 w-fit">
            <Image
              src="/images/logo-light.png"
              alt="Zinmac"
              width={24}
              height={24}
              className="w-6 h-6 dark:hidden"
            />
            <Image
              src="/images/logo-dark.png"
              alt="Zinmac"
              width={24}
              height={24}
              className="w-6 h-6 hidden dark:block"
            />
            <span className="font-serif text-sm text-text">Zinmac</span>
          </Link>
        </div>
        <FooterLine items={LINE_1} />
        <FooterLine items={LINE_2} />
        <div className="text-center sm:text-left flex flex-wrap justify-center sm:justify-start gap-x-3">
          <Link href="/terms" className="text-xs text-muted underline hover:text-text">
            이용약관
          </Link>
          <Link href="/privacy" className="text-xs text-muted underline hover:text-text">
            개인정보처리방침
          </Link>
          <Link href="/refund" className="text-xs text-muted underline hover:text-text">
            환불 정책
          </Link>
          <Link href="/faq" className="text-xs text-muted underline hover:text-text">
            FAQ
          </Link>
          <Link href="/contact" className="text-xs text-muted underline hover:text-text">
            문의하기
          </Link>
        </div>
        <p className="text-xs text-muted text-center sm:text-left">
          © 2026 진맥. All rights reserved.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
